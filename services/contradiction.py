"""
FORGE -- Contradiction Detection across sources with severity ratings.
Only proposes flags -- never merges, deletes, or silently prefers one fact.
Resolution is always a human action (resolved / acknowledged).

IMPORTANT LIMITATION, READ BEFORE MODIFYING: FactCard.normalized_statement
for date/amount facts is generic ("Document references date: X") with no
semantic tag for WHAT that date or amount represents. Comparing every
date-type fact in a case against every other date-type fact case-wide means
a single ordinary document with several unrelated dates (incident date,
filing date, service date) would produce a false "contradiction" for every
pair. This module therefore requires facts to share a source document
before comparing them at all, EXCEPT for a narrower, higher-stakes category:
sworn statements, affidavits, depositions, and police/incident reports.

HIGH-SCRUTINY CATEGORIES: inconsistencies across DIFFERENT sworn statements
or police/incident reports are exactly the kind of discrepancy a pro se
litigant needs surfaced prominently -- a prior inconsistent statement is
classic impeachment material, and it is meaningful precisely BECAUSE it
crosses documents (e.g., an officer's incident report says one date/detail,
their later sworn statement says another). For this category only, this
module compares across documents and keeps severity at "high" -- everywhere
else, it stays same-document-only and "low" severity per the honest,
conservative default.
"""
from __future__ import annotations
import re
from datetime import datetime
from typing import Dict, List, Optional
from .models import FactCard, ContradictionFlag

DATE_TOKEN = re.compile(r"\b(\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b")
AMOUNT_TOKEN = re.compile(r"\$\s?[\d,]+(?:\.\d{2})?")

# Document categories treated as sworn/high-reliability-expected statements,
# where a cross-document inconsistency is itself the meaningful signal
# (e.g., a prior inconsistent statement), matching how these documents are
# actually used in litigation -- not merely organizational metadata.
HIGH_SCRUTINY_CATEGORIES = {
    "Police, arrest, or incident report",
    "Affidavit, declaration, or sworn statement (under oath)",
}


def _extract_dates(text: str) -> List[str]:
    return DATE_TOKEN.findall(text or "")


def _extract_amounts(text: str) -> List[str]:
    return AMOUNT_TOKEN.findall(text or "")


def _normalize_amount(raw: str) -> Optional[float]:
    try:
        return float(raw.replace("$", "").replace(",", "").strip())
    except ValueError:
        return None


def _fact_document_ids(fact: FactCard) -> set:
    return {s.source_document_id for s in fact.sources if s.source_document_id}


def _shared_source_document(fact_a: FactCard, fact_b: FactCard) -> Optional[str]:
    shared = _fact_document_ids(fact_a) & _fact_document_ids(fact_b)
    return next(iter(shared), None) if shared else None


def _is_high_scrutiny_pair(fact_a: FactCard, fact_b: FactCard,
                            document_categories: Optional[Dict[str, str]]) -> bool:
    """True if EVERY document backing fact_a and EVERY document backing
    fact_b falls in HIGH_SCRUTINY_CATEGORIES. Requires document_categories
    (a source_document_id -> category lookup) to be supplied by the caller;
    without it, this always returns False and the conservative same-document
    default applies -- this module never assumes a category it wasn't told."""
    if not document_categories:
        return False
    docs_a = _fact_document_ids(fact_a)
    docs_b = _fact_document_ids(fact_b)
    if not docs_a or not docs_b:
        return False
    cats_a = {document_categories.get(d) for d in docs_a}
    cats_b = {document_categories.get(d) for d in docs_b}
    return cats_a <= HIGH_SCRUTINY_CATEGORIES and cats_b <= HIGH_SCRUTINY_CATEGORIES


def detect_date_contradiction(fact_a: FactCard, fact_b: FactCard,
                               document_categories: Optional[Dict[str, str]] = None) -> Optional[ContradictionFlag]:
    if fact_a.fact_type != "date" or fact_b.fact_type != "date":
        return None

    high_scrutiny = _is_high_scrutiny_pair(fact_a, fact_b, document_categories)
    if not high_scrutiny and not _shared_source_document(fact_a, fact_b):
        return None

    dates_a = set(_extract_dates(fact_a.normalized_statement))
    dates_b = set(_extract_dates(fact_b.normalized_statement))
    if not (dates_a and dates_b and dates_a.isdisjoint(dates_b)):
        return None

    if high_scrutiny:
        return ContradictionFlag(
            case_id=fact_a.case_id, fact_card_id_a=fact_a.id, fact_card_id_b=fact_b.id,
            contradiction_type="sworn_statement_date_mismatch", severity="high",
            detail=(f"A sworn statement, affidavit, or police/incident report cites "
                    f"'{fact_a.normalized_statement}', while another such document in this case "
                    f"cites '{fact_b.normalized_statement}'. Because both are sworn or official "
                    f"reports, a date discrepancy between them may be significant -- review both "
                    f"source documents directly before relying on either date."),
        )
    return ContradictionFlag(
        case_id=fact_a.case_id, fact_card_id_a=fact_a.id, fact_card_id_b=fact_b.id,
        contradiction_type="date_discrepancy", severity="low",
        detail=(f"'{fact_a.normalized_statement}' and '{fact_b.normalized_statement}' were both "
                f"extracted from the same document but cite different dates. This does not "
                f"necessarily mean they conflict -- confirm they represent different events "
                f"(e.g., an incident date vs. a filing date) rather than inconsistent values "
                f"for the same fact."),
    )


def detect_amount_contradiction(fact_a: FactCard, fact_b: FactCard,
                                 document_categories: Optional[Dict[str, str]] = None) -> Optional[ContradictionFlag]:
    if fact_a.fact_type != "amount" or fact_b.fact_type != "amount":
        return None

    high_scrutiny = _is_high_scrutiny_pair(fact_a, fact_b, document_categories)
    if not high_scrutiny and not _shared_source_document(fact_a, fact_b):
        return None

    amounts_a = [a for a in (_normalize_amount(x) for x in _extract_amounts(fact_a.normalized_statement)) if a is not None]
    amounts_b = [a for a in (_normalize_amount(x) for x in _extract_amounts(fact_b.normalized_statement)) if a is not None]
    if not (amounts_a and amounts_b and set(amounts_a).isdisjoint(set(amounts_b))):
        return None

    if high_scrutiny:
        return ContradictionFlag(
            case_id=fact_a.case_id, fact_card_id_a=fact_a.id, fact_card_id_b=fact_b.id,
            contradiction_type="sworn_statement_amount_mismatch", severity="high",
            detail=(f"A sworn statement, affidavit, or police/incident report cites "
                    f"'{fact_a.normalized_statement}', while another such document in this case "
                    f"cites '{fact_b.normalized_statement}'. Review both source documents directly "
                    f"before relying on either figure."),
        )
    return ContradictionFlag(
        case_id=fact_a.case_id, fact_card_id_a=fact_a.id, fact_card_id_b=fact_b.id,
        contradiction_type="amount_discrepancy", severity="low",
        detail=(f"'{fact_a.normalized_statement}' and '{fact_b.normalized_statement}' were both "
                f"extracted from the same document but cite different dollar amounts. This does "
                f"not necessarily mean they conflict -- confirm they represent different figures "
                f"(e.g., a filing fee vs. damages sought) rather than inconsistent values for the "
                f"same amount."),
    )


def scan_case_for_contradictions(facts: List[FactCard],
                                  document_categories: Optional[Dict[str, str]] = None) -> List[ContradictionFlag]:
    """`document_categories` is an optional {source_document_id: category}
    lookup. When supplied, sworn-statement / police-report pairs are
    compared across documents at high severity; everything else remains
    same-document-only at low severity. When omitted, every comparison
    falls back to the conservative same-document-only behavior."""
    flags: List[ContradictionFlag] = []
    for i in range(len(facts)):
        for j in range(i + 1, len(facts)):
            fact_a, fact_b = facts[i], facts[j]
            for detector in (detect_date_contradiction, detect_amount_contradiction):
                flag = detector(fact_a, fact_b, document_categories)
                if flag:
                    flags.append(flag)
    return flags


def resolve_flag(flag: ContradictionFlag, action: str, note: Optional[str] = None) -> ContradictionFlag:
    flag.resolution_status = action
    flag.resolution_note = note
    flag.resolved_at = datetime.utcnow().isoformat()
    return flag
