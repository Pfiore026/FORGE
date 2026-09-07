"""
services/deadline_service.py

Wires FRCPDeadlineEngine + RuleCitationStore into the same audit-logged
service pattern used by CaseService, DocumentService, FactCardService,
ContradictionService, and TimelineService (see services/case_service.py).

This is the missing link between the timeline events FORGE already collects
(TimelineService) and the Deadline Table required by the master prompt's
OUTPUT_FORMATS. It never guesses: MissingVariableError propagates up to
the UI layer, which must surface the .question to the user per
CRITICAL_OVERRIDE: PROACTIVE_CLARIFICATION.
"""
from __future__ import annotations
from typing import Optional, Dict, List
import json

from .deadline_engine import FRCPDeadlineEngine, DeadlineComputation, MissingVariableError
from .citation_guard import RuleCitationStore

DEFAULT_CORPUS_PATH = "data/frcp_rules_corpus.json"

# Convenience presets so the UI can offer a dropdown of common triggering
# events instead of requiring free-text rule numbers. This layer never
# overrides the Strict Citation Mandate -- every rule listed here has
# verbatim text loaded in data/frcp_rules_corpus.json, and citation lookups
# still go through RuleCitationStore, which refuses on any miss.
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


class DeadlineService:
    """Same shape as the other FORGE services: takes an AuditService,
    exposes case-scoped compute/read methods, and logs every write."""

    def __init__(self, audit, corpus_path: str = DEFAULT_CORPUS_PATH):
        self.audit = audit
        with open(corpus_path) as f:
            corpus = json.load(f)
        self.engine = FRCPDeadlineEngine(corpus)
        self.citations = RuleCitationStore(corpus)
        self.deadlines: Dict[str, DeadlineComputation] = {}
        self._case_index: Dict[str, List[str]] = {}

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
        key = f"{case_id}:{trigger_event}:{rule_cited}"
        self.deadlines[key] = computation
        self._case_index.setdefault(case_id, [])
        if key not in self._case_index[case_id]:
            self._case_index[case_id].append(key)
        self.audit.record(case_id, user_id, "deadline_computed", "deadline", key, {
            "rule_cited": rule_cited,
            "trigger_event": trigger_event,
            "resulting_deadline": computation.resulting_deadline.isoformat(),
            "added_days_rule_6d": computation.added_days_rule_6d,
        })
        return computation

    def for_case(self, case_id: str) -> List[DeadlineComputation]:
        keys = self._case_index.get(case_id, [])
        items = [self.deadlines[k] for k in keys]
        return sorted(items, key=lambda c: c.resulting_deadline)

    def cite(self, rule_id: str) -> str:
        """Never throws -- returns verbatim text or the mandated refusal
        string. Safe to call directly from the UI layer."""
        return self.citations.safe_cite_or_refusal(rule_id)
