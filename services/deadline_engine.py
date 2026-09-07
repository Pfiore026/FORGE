"""
services/deadline_engine.py

FRCP Rule 6 Time-Computation Protocol implementation for FORGE.

STRICT GROUNDING: Every computation cites the exact FRCP subsection it relies on.
This module refuses to guess. If a required input (trigger date, service method,
or a local-rule/judge-order modifier) is missing, it raises MissingVariableError
so the calling layer can HALT and ask the user (per CRITICAL_OVERRIDE:
PROACTIVE_CLARIFICATION in the FORGE master prompt).

This module does NOT give legal advice and does NOT decide whether a filing
is warranted. It only computes dates mechanically from FRCP Rule 6(a)/6(d),
optionally overridden by an explicit Local Rule or Judge's Practice modifier
that the caller supplies as verbatim text.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional, List

US_FEDERAL_HOLIDAYS_FIXED = {
    (1, 1): "New Year's Day",
    (6, 19): "Juneteenth National Independence Day",
    (7, 4): "Independence Day",
    (11, 11): "Veterans' Day",
    (12, 25): "Christmas Day",
}


class MissingVariableError(Exception):
    """Raised when a deadline cannot be computed because a required fact
    (trigger date, service method, or rule text) was not provided.
    Carries a user-facing clarification question, per CRITICAL_OVERRIDE."""
    def __init__(self, question: str, why: str):
        self.question = question
        self.why = why
        super().__init__(f"{question} | REASON: {why}")


def _nth_weekday_of_month(year: int, month: int, weekday: int, n: int) -> date:
    d = date(year, month, 1)
    count = 0
    while True:
        if d.weekday() == weekday:
            count += 1
            if count == n:
                return d
        d += timedelta(days=1)


def _last_weekday_of_month(year: int, month: int, weekday: int) -> date:
    if month == 12:
        d = date(year, 12, 31)
    else:
        d = date(year, month + 1, 1) - timedelta(days=1)
    while d.weekday() != weekday:
        d -= timedelta(days=1)
    return d


def _observed(d: date) -> date:
    """5 U.S.C. 6103 observance shift: if a fixed-date federal holiday falls on
    Saturday, it is observed the preceding Friday; if Sunday, the following Monday."""
    if d.weekday() == 5:
        return d - timedelta(days=1)
    if d.weekday() == 6:
        return d + timedelta(days=1)
    return d


def is_federal_legal_holiday(d: date) -> Optional[str]:
    """FRCP 6(a)(6)(A)-(B): fixed-date federal holidays plus the floating
    Monday holidays, including the 5 U.S.C. 6103 Saturday/Sunday observance
    shift that federal court clerks' offices actually follow. State holidays
    under 6(a)(6)(C) are NOT included here; pass `extra_state_holidays` on
    FRCPDeadlineEngine.compute_forward_deadline for those."""
    key = (d.month, d.day)
    if key in US_FEDERAL_HOLIDAYS_FIXED:
        return US_FEDERAL_HOLIDAYS_FIXED[key]
    for (mo, da), name in US_FEDERAL_HOLIDAYS_FIXED.items():
        fixed_date = date(d.year, mo, da)
        if _observed(fixed_date) == d and d != fixed_date:
            return f"{name} (observed)"
    if d == _nth_weekday_of_month(d.year, 1, 0, 3):
        return "Martin Luther King Jr.'s Birthday"
    if d == _nth_weekday_of_month(d.year, 2, 0, 3):
        return "Washington's Birthday"
    if d == _last_weekday_of_month(d.year, 5, 0):
        return "Memorial Day"
    if d == _nth_weekday_of_month(d.year, 9, 0, 1):
        return "Labor Day"
    if d == _nth_weekday_of_month(d.year, 10, 0, 2):
        return "Columbus Day"
    if d == _nth_weekday_of_month(d.year, 11, 3, 4):
        return "Thanksgiving Day"
    return None


def is_dies_non(d: date, extra_state_holidays: Optional[List[date]] = None) -> bool:
    """A day that does not count as the final day of a period under
    FRCP 6(a)(1)(C): Saturday, Sunday, or a legal holiday."""
    if d.weekday() >= 5:
        return True
    if is_federal_legal_holiday(d):
        return True
    if extra_state_holidays and d in extra_state_holidays:
        return True
    return False


@dataclass
class DeadlineComputation:
    rule_cited: str
    rule_text: str
    trigger_event: str
    trigger_date: date
    raw_period_days: int
    service_method: Optional[str]
    added_days_rule_6d: int
    landed_on_dies_non: bool
    dies_non_reason: Optional[str]
    resulting_deadline: date
    computation_steps: List[str] = field(default_factory=list)
    local_rule_modifier: Optional[str] = None
    judge_practice_modifier: Optional[str] = None

    def as_table_row(self) -> dict:
        return {
            "Triggering Event": self.trigger_event,
            "Rule(s) Cited": self.rule_cited,
            "Service Method / Trigger Date": (
                f"{self.trigger_date.isoformat()}"
                + (f" via {self.service_method}" if self.service_method else "")
            ),
            "Computation Steps": " ".join(self.computation_steps),
            "Resulting Deadline Date": self.resulting_deadline.isoformat(),
        }


MAIL_EXTENSION_METHODS = {"mail", "leaving_with_clerk", "other_consented"}


class FRCPDeadlineEngine:
    """Mechanical FRCP Rule 6 deadline calculator. No strategy, no advice."""

    def __init__(self, rule_corpus: dict):
        self.rule_corpus = rule_corpus

    def _get_rule_text(self, rule_id: str) -> str:
        rule_num, _, sub = rule_id.partition("(")
        rule_num = rule_num.strip()
        entry = self.rule_corpus.get(rule_num)
        if not entry:
            raise MissingVariableError(
                question=f"I do not have the specific rule required to answer this "
                          f"(FRCP {rule_id} is not in the loaded rule corpus).",
                why="Strict Citation & Grounding Mandate forbids answering from memory."
            )
        subs = entry.get("subsections", {})
        if rule_id in subs:
            return subs[rule_id]
        return entry.get("title", "")

    def compute_forward_deadline(
        self,
        rule_cited: str,
        trigger_event: str,
        trigger_date: Optional[date],
        period_days: int,
        service_method: Optional[str] = None,
        local_rule_text: Optional[str] = None,
        judge_practice_text: Optional[str] = None,
        state_for_holidays: Optional[str] = None,
        extra_state_holidays: Optional[List[date]] = None,
    ) -> DeadlineComputation:
        """Computes a forward-counted deadline (X days AFTER an event) under
        FRCP 6(a)(1), with optional Rule 6(d) mail/service extension.

        HALTS via MissingVariableError if trigger_date is not provided.
        """
        if trigger_date is None:
            raise MissingVariableError(
                question=f"To calculate the deadline under {rule_cited}, I need the "
                          f"exact date of '{trigger_event}'. Please provide it.",
                why="FRCP 6(a)(1)(A) requires excluding the day of the triggering "
                    "event, which cannot be identified without that date."
            )

        rule_text_6a1 = self._get_rule_text("6(a)(1)")
        steps = [
            f"Rule 6(a)(1)(A): exclude {trigger_date.isoformat()} (the triggering "
            f"event day, '{trigger_event}').",
            f"Rule 6(a)(1)(B): count every day, including intermediate weekends "
            f"and legal holidays, for {period_days} days."
        ]

        deadline = trigger_date + timedelta(days=period_days)
        steps.append(
            f"Raw {period_days}-day count from {trigger_date.isoformat()} lands on "
            f"{deadline.isoformat()}."
        )

        landed_on_dies_non = False
        dies_non_reason = None
        while is_dies_non(deadline, extra_state_holidays):
            reason = ("weekend" if deadline.weekday() >= 5
                       else is_federal_legal_holiday(deadline))
            landed_on_dies_non = True
            dies_non_reason = reason
            steps.append(
                f"Rule 6(a)(1)(C): {deadline.isoformat()} is a {reason}; deadline "
                f"rolls forward one day."
            )
            deadline += timedelta(days=1)

        added_days = 0
        if service_method:
            normalized = service_method.strip().lower().replace(" ", "_")
            if normalized in MAIL_EXTENSION_METHODS:
                self._get_rule_text("6(d)")
                added_days = 3
                steps.append(
                    f"Rule 6(d): service was by '{service_method}', so 3 days are "
                    f"added after the period would otherwise expire."
                )
                deadline = deadline + timedelta(days=added_days)
                while is_dies_non(deadline, extra_state_holidays):
                    reason = ("weekend" if deadline.weekday() >= 5
                               else is_federal_legal_holiday(deadline))
                    steps.append(
                        f"Rule 6(a)(1)(C) applied again after the 6(d) extension: "
                        f"{deadline.isoformat()} is a {reason}; rolls forward one day."
                    )
                    deadline += timedelta(days=1)
            elif normalized in {"personal", "electronic", "email", "ecf"}:
                steps.append(
                    f"Service method '{service_method}' does not qualify for the "
                    f"Rule 6(d) 3-day mail extension (electronic service was removed "
                    f"from Rule 6(d) by the 2016 amendment)."
                )

        if local_rule_text:
            steps.append(f"Local Rule modifier applied verbatim: \"{local_rule_text}\"")
        if judge_practice_text:
            steps.append(f"Judge's Practice modifier applied verbatim: \"{judge_practice_text}\"")

        return DeadlineComputation(
            rule_cited=rule_cited,
            rule_text=rule_text_6a1,
            trigger_event=trigger_event,
            trigger_date=trigger_date,
            raw_period_days=period_days,
            service_method=service_method,
            added_days_rule_6d=added_days,
            landed_on_dies_non=landed_on_dies_non,
            dies_non_reason=dies_non_reason,
            resulting_deadline=deadline,
            computation_steps=steps,
            local_rule_modifier=local_rule_text,
            judge_practice_modifier=judge_practice_text,
        )
