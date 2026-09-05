"""
FORGE -- Contradiction Detection across sources with severity ratings.
Only proposes flags -- never merges, deletes, or silently prefers one fact.
Resolution is always a human action (resolved / acknowledged).
"""
from __future__ import annotations
import re
from datetime import datetime
from typing import List, Optional
from .models import FactCard, ContradictionFlag

DATE_TOKEN = re.compile(r"\b(\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b")
AMOUNT_TOKEN = re.compile(r"\$\s?[\d,]+(?:\.\d{2})?")


def _extract_dates(text: str) -> List[str]:
    return DATE_TOKEN.findall(text or "")


def _extract_amounts(text: str) -> List[str]:
    return AMOUNT_TOKEN.findall(text or "")


def _normalize_amount(raw: str) -> Optional[float]:
    try:
        return float(raw.replace("$", "").replace(",", "").strip())
    except ValueError:
        return None


def detect_date_contradiction(fact_a: FactCard, fact_b: FactCard) -> Optional[ContradictionFlag]:
    dates_a = set(_extract_dates(fact_a.normalized_statement))
    dates_b = set(_extract_dates(fact_b.normalized_statement))
    if dates_a and dates_b and dates_a.isdisjoint(dates_b):
        if fact_a.fact_type == fact_b.fact_type == "date":
            return ContradictionFlag(
                case_id=fact_a.case_id, fact_card_id_a=fact_a.id, fact_card_id_b=fact_b.id,
                contradiction_type="date_mismatch", severity="high",
                detail=(f"'{fact_a.normalized_statement}' cites {', '.join(dates_a)} while "
                        f"'{fact_b.normalized_statement}' cites {', '.join(dates_b)}."),
            )
    return None


def detect_amount_contradiction(fact_a: FactCard, fact_b: FactCard) -> Optional[ContradictionFlag]:
    if fact_a.fact_type != "amount" or fact_b.fact_type != "amount":
        return None
    amounts_a = [a for a in (_normalize_amount(x) for x in _extract_amounts(fact_a.normalized_statement)) if a is not None]
    amounts_b = [a for a in (_normalize_amount(x) for x in _extract_amounts(fact_b.normalized_statement)) if a is not None]
    if amounts_a and amounts_b and set(amounts_a).isdisjoint(set(amounts_b)):
        return ContradictionFlag(
            case_id=fact_a.case_id, fact_card_id_a=fact_a.id, fact_card_id_b=fact_b.id,
            contradiction_type="amount_mismatch", severity="medium",
            detail=(f"'{fact_a.normalized_statement}' states {amounts_a} while "
                    f"'{fact_b.normalized_statement}' states {amounts_b}."),
        )
    return None


def scan_case_for_contradictions(facts: List[FactCard]) -> List[ContradictionFlag]:
    flags: List[ContradictionFlag] = []
    for i in range(len(facts)):
        for j in range(i + 1, len(facts)):
            fact_a, fact_b = facts[i], facts[j]
            for detector in (detect_date_contradiction, detect_amount_contradiction):
                flag = detector(fact_a, fact_b)
                if flag:
                    flags.append(flag)
    return flags


def resolve_flag(flag: ContradictionFlag, action: str, note: Optional[str] = None) -> ContradictionFlag:
    flag.resolution_status = action
    flag.resolution_note = note
    flag.resolved_at = datetime.utcnow().isoformat()
    return flag
