"""
FORGE -- Contradiction Detection across sources with severity ratings.
Only proposes flags -- never merges, deletes, or silently prefers one fact.
Resolution is always a human action (resolved / acknowledged).

IMPORTANT LIMITATION, READ BEFORE MODIFYING: FactCard.normalized_statement
for date/amount facts is generic ("Document references date: X") with no
semantic tag for WHAT that date or amount represents (an incident date, a
filing date, a service date, a filing fee, damages sought, etc. all look
identical to this module). Comparing every date-type fact in a case against
every other date-type fact -- which the original version of this file did --
means a single ordinary document with three unrelated dates (incident date,
filing date, service date) produces 3 separate "high severity" contradiction
flags, none of which are real contradictions. At real-world scale (a case
with 5+ dates across several documents) this explodes combinatorially and
would bury any genuine contradiction under a pile of false ones.

Until fact_type carries real semantic subtypes (e.g. "incident_date" vs.
"filing_date" vs. "service_date"), this module:
  1. Only compares facts extracted from the SAME source document -- a date
     mismatch between a docket entry and an unrelated complaint is not
     meaningful to flag at all, since nothing links them as describing the
     same underlying event.
  2. Downgrades severity to "low" and reframes the language honestly as a
     discrepancy to confirm, not an asserted contradiction -- matching the
     same honest framing already used by the "Multiple dates detected"
     completeness check in services/completeness.py.
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


def _shared_source_document(fact_a: FactCard, fact_b: FactCard) -> Optional[str]:
    """Returns the shared source_document_id if both facts have at least one
    source pointing to the same document, else None. Facts with no sources,
    or sources from different documents, are never compared -- there is no
    basis to treat two dates from unrelated documents as describing the
    same underlying event."""
    docs_a = {s.source_document_id for s in fact_a.sources if s.source_document_id}
    docs_b = {s.source_document_id for s in fact_b.sources if s.source_document_id}
    shared = docs_a & docs_b
    return next(iter(shared), None) if shared else None


def detect_date_contradiction(fact_a: FactCard, fact_b: FactCard) -> Optional[ContradictionFlag]:
    if fact_a.fact_type != "date" or fact_b.fact_type != "date":
        return None
    shared_doc = _shared_source_document(fact_a, fact_b)
    if not shared_doc:
        return None
    dates_a = set(_extract_dates(fact_a.normalized_statement))
    dates_b = set(_extract_dates(fact_b.normalized_statement))
    if dates_a and dates_b and dates_a.isdisjoint(dates_b):
        return ContradictionFlag(
            case_id=fact_a.case_id, fact_card_id_a=fact_a.id, fact_card_id_b=fact_b.id,
            contradiction_type="date_discrepancy", severity="low",
            detail=(f"'{fact_a.normalized_statement}' and '{fact_b.normalized_statement}' were both "
                    f"extracted from the same document but cite different dates. This does not "
                    f"necessarily mean they conflict -- confirm they represent different events "
                    f"(e.g., an incident date vs. a filing date) rather than inconsistent values "
                    f"for the same fact."),
        )
    return None


def detect_amount_contradiction(fact_a: FactCard, fact_b: FactCard) -> Optional[ContradictionFlag]:
    if fact_a.fact_type != "amount" or fact_b.fact_type != "amount":
        return None
    shared_doc = _shared_source_document(fact_a, fact_b)
    if not shared_doc:
        return None
    amounts_a = [a for a in (_normalize_amount(x) for x in _extract_amounts(fact_a.normalized_statement)) if a is not None]
    amounts_b = [a for a in (_normalize_amount(x) for x in _extract_amounts(fact_b.normalized_statement)) if a is not None]
    if amounts_a and amounts_b and set(amounts_a).isdisjoint(set(amounts_b)):
        return ContradictionFlag(
            case_id=fact_a.case_id, fact_card_id_a=fact_a.id, fact_card_id_b=fact_b.id,
            contradiction_type="amount_discrepancy", severity="low",
            detail=(f"'{fact_a.normalized_statement}' and '{fact_b.normalized_statement}' were both "
                    f"extracted from the same document but cite different dollar amounts. This does "
                    f"not necessarily mean they conflict -- confirm they represent different figures "
                    f"(e.g., a filing fee vs. damages sought) rather than inconsistent values for the "
                    f"same amount."),
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
