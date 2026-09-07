"""
services/deadline_service.py

Wires FRCPDeadlineEngine + RuleCitationStore into real Postgres persistence
(public.computed_deadlines), via the authenticated session's Supabase
client. The deadline math itself (services/deadline_engine.py) is pure
logic and unchanged -- this module only adds the read/write layer that was
previously an in-memory dict with no real database table backing it at all.

RLS on computed_deadlines (case_id must belong to a case owned by
auth.uid()) means the database itself enforces per-user isolation here too.
"""
from __future__ import annotations
from datetime import date
from typing import Optional, Dict, List

from .deadline_engine import FRCPDeadlineEngine, DeadlineComputation, MissingVariableError
from .citation_guard import RuleCitationStore

DEFAULT_CORPUS_PATH = "data/frcp_rules_corpus.json"

KNOWN_TRIGGERS = {
    "Complaint filed with the court (Rule 4(m) service deadline)": {
        "rule_cited": "FRCP 4(m)", "period_days": 90,
        "citation_keys": ["6(a)(1)", "4(m)"],
    },
    "Service of summons and complaint (personal or waiver)": {
        "rule_cited": "FRCP 12(a)(1)(A)(i)", "period_days": 21,
        "citation_keys": ["6(a)(1)"],
    },
    "Rule 26(f) conference held": {
        "rule_cited": "FRCP 26(a)(1)(C)", "period_days": 14,
        "citation_keys": ["6(a)(1)", "26(a)(1)(C)"],
    },
    "Interrogatories served on you": {
        "rule_cited": "FRCP 33(b)(2)", "period_days": 30,
        "citation_keys": ["6(a)(1)", "33(b)(2)"],
    },
    "Requests for production served on you": {
        "rule_cited": "FRCP 34(b)(2)(A)", "period_days": 30,
        "citation_keys": ["6(a)(1)", "34(b)(2)(A)"],
    },
    "Requests for admission served on you": {
        "rule_cited": "FRCP 36(a)(3)", "period_days": 30,
        "citation_keys": ["6(a)(1)", "36(a)(3)"],
    },
}


def _row_to_computation(row: dict) -> DeadlineComputation:
    return DeadlineComputation(
        rule_cited=row.get("rule_cited") or "", rule_text="",
        trigger_event=row.get("trigger_event") or "",
        trigger_date=date.fromisoformat(row["trigger_date"]),
        raw_period_days=row.get("period_days") or 0, service_method=row.get("service_method"),
        added_days_rule_6d=row.get("added_days_rule_6d") or 0,
        landed_on_dies_non=row.get("landed_on_dies_non") or False, dies_non_reason=row.get("dies_non_reason"),
        resulting_deadline=date.fromisoformat(row["resulting_deadline"]),
        computation_steps=row.get("computation_steps") or [],
        local_rule_modifier=row.get("local_rule_modifier"), judge_practice_modifier=row.get("judge_practice_modifier"),
    )


class DeadlineService:
    """Same shape as the other FORGE services: takes an AuditService and a
    Supabase client, exposes case-scoped compute/read methods, and logs
    every write."""

    def __init__(self, audit, client, corpus_path: str = DEFAULT_CORPUS_PATH):
        self.audit = audit
        self.client = client
        import json
        with open(corpus_path) as f:
            corpus = json.load(f)
        self.engine = FRCPDeadlineEngine(corpus)
        self.citations = RuleCitationStore(corpus)

    def compute(self, case_id, user_id, trigger_event, trigger_date, rule_cited,
                period_days, service_method=None, local_rule_text=None,
                judge_practice_text=None, state_for_holidays=None) -> DeadlineComputation:
        """May raise MissingVariableError -- the caller (app.py) must catch
        it and display e.question rather than silently failing or guessing."""
        computation = self.engine.compute_forward_deadline(
            rule_cited=rule_cited, trigger_event=trigger_event, trigger_date=trigger_date,
            period_days=period_days, service_method=service_method,
            local_rule_text=local_rule_text, judge_practice_text=judge_practice_text,
            state_for_holidays=state_for_holidays,
        )

        payload = {
            "case_id": case_id, "rule_cited": rule_cited, "trigger_event": trigger_event,
            "trigger_date": computation.trigger_date.isoformat(), "period_days": period_days,
            "service_method": service_method, "added_days_rule_6d": computation.added_days_rule_6d,
            "landed_on_dies_non": computation.landed_on_dies_non, "dies_non_reason": computation.dies_non_reason,
            "resulting_deadline": computation.resulting_deadline.isoformat(),
            "computation_steps": computation.computation_steps,
            "local_rule_modifier": local_rule_text, "judge_practice_modifier": judge_practice_text,
        }

        existing = (
            self.client.table("computed_deadlines").select("id")
            .eq("case_id", case_id).eq("trigger_event", trigger_event).eq("rule_cited", rule_cited)
            .execute()
        )
        if existing.data:
            self.client.table("computed_deadlines").update(payload).eq("id", existing.data[0]["id"]).execute()
        else:
            self.client.table("computed_deadlines").insert(payload).execute()

        self.audit.record(case_id, user_id, "deadline_computed", "deadline",
                           f"{case_id}:{trigger_event}:{rule_cited}", {
                               "rule_cited": rule_cited, "trigger_event": trigger_event,
                               "resulting_deadline": computation.resulting_deadline.isoformat(),
                               "added_days_rule_6d": computation.added_days_rule_6d,
                           })
        return computation

    def for_case(self, case_id: str) -> List[DeadlineComputation]:
        resp = (
            self.client.table("computed_deadlines").select("*").eq("case_id", case_id)
            .order("resulting_deadline").execute()
        )
        return [_row_to_computation(r) for r in (resp.data or [])]

    def cite(self, rule_id: str) -> str:
        """Never throws -- returns verbatim text or the mandated refusal
        string. Safe to call directly from the UI layer."""
        return self.citations.safe_cite_or_refusal(rule_id)
