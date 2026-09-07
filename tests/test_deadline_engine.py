"""
tests/test_deadline_engine.py

Validates services/deadline_engine.py against known FRCP Rule 6 outcomes.
Run with: pytest tests/test_deadline_engine.py -v
"""
import json
import pytest
from datetime import date
from services.deadline_engine import FRCPDeadlineEngine, MissingVariableError
from services.citation_guard import RuleCitationStore, REFUSAL_TEXT


@pytest.fixture
def engine():
    with open("data/frcp_rules_corpus.json") as f:
        corpus = json.load(f)
    return FRCPDeadlineEngine(corpus)


def test_21_day_answer_no_collision(engine):
    r = engine.compute_forward_deadline(
        rule_cited="FRCP 12(a)(1)(A)(i)",
        trigger_event="Service of summons and complaint",
        trigger_date=date(2026, 6, 1),  # Monday
        period_days=21,
        service_method="personal",
    )
    assert r.resulting_deadline == date(2026, 6, 22)
    assert r.added_days_rule_6d == 0


def test_mail_service_adds_3_days_and_rolls_weekend(engine):
    r = engine.compute_forward_deadline(
        rule_cited="FRCP 33",
        trigger_event="Service of interrogatories by mail",
        trigger_date=date(2026, 6, 5),  # Friday
        period_days=30,
        service_method="mail",
    )
    assert r.added_days_rule_6d == 3
    assert r.resulting_deadline == date(2026, 7, 9)


def test_missing_trigger_date_halts(engine):
    with pytest.raises(MissingVariableError):
        engine.compute_forward_deadline(
            rule_cited="FRCP 26(a)(1)(C)",
            trigger_event="Rule 26(f) conference",
            trigger_date=None,
            period_days=14,
        )


def test_unknown_rule_refused(engine):
    with pytest.raises(MissingVariableError):
        engine._get_rule_text("999")


def test_observed_holiday_shift(engine):
    from services.deadline_engine import is_federal_legal_holiday
    # July 4, 2026 falls on a Saturday -> observed Friday July 3
    assert is_federal_legal_holiday(date(2026, 7, 3)) == "Independence Day (observed)"
    assert is_federal_legal_holiday(date(2026, 7, 4)) == "Independence Day"


def test_citation_guard_refuses_unknown_rule():
    store = RuleCitationStore({"6": {"title": "x", "source": "y", "subsections": {}}})
    assert store.safe_cite_or_refusal("999(a)") == REFUSAL_TEXT


def test_citation_guard_returns_verbatim_text():
    corpus = {
        "6": {
            "title": "Rule 6",
            "source": "Cornell LII",
            "subsections": {"6(d)": "3 days are added after service by mail."}
        }
    }
    store = RuleCitationStore(corpus)
    result = store.safe_cite_or_refusal("6(d)")
    assert "3 days are added after service by mail." in result
    assert "Cornell LII" in result
