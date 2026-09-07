"""
FORGE Phase 2A -- Document Completeness & Review Safeguard
Every uploaded document is treated as a starting point for verification,
never as a finished, trustworthy record on its own.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
import re
import uuid

EXTRACTION_UNAVAILABLE_MARKER = "[FORGE_EXTRACTION_UNAVAILABLE]"

COMPLETENESS_CHECKS = [
    {"check": "Text extraction", "looks_for": "Whether FORGE was actually able to read machine-readable "
     "text from this file at all",
     "if_flagged": "Red flag if extraction failed or was unavailable (e.g., an image with no OCR engine, "
     "or a scanned PDF with no text layer) -- every other check below is skipped for that document, "
     "since there is no real text to check"},
    {"check": "Page continuity", "looks_for": "No pages detected, or embedded 'Page X of Y' markers "
     "that skip, repeat, or disagree on the total page count",
     "if_flagged": "Red flag if no pages detected; amber flag if page markers are out of sequence"},
    {"check": "Legibility", "looks_for": "Blurred or low-contrast text OCR cannot confidently read",
     "if_flagged": "Amber flag on affected page; text excluded from proposed facts"},
    {"check": "Referenced exhibits", "looks_for": "Text referencing 'Exhibit A' etc. not present in the upload",
     "if_flagged": "Red flag; document incomplete until exhibit is uploaded or confirmed absent"},
    {"check": "Signature / certification page", "looks_for": "Missing signature on a document type that requires one",
     "if_flagged": "Amber flag; user asked to confirm whether a signed version exists"},
    {"check": "Multiple dates detected", "looks_for": "More than one distinct calendar date appearing in the "
     "document text",
     "if_flagged": "Informational flag listing the dates found; FORGE does not determine whether they conflict, "
     "since that can require reading context FORGE cannot verify -- the user is asked to confirm consistency"},
    {"check": "Duplicate detection", "looks_for": "A file matching an already-uploaded document",
     "if_flagged": "Informational flag; user chooses to keep both, replace, or discard"},
    {"check": "Redaction markers", "looks_for": "Bracketed or blacked-out redaction markers in the extracted text",
     "if_flagged": "Amber flag; user asked to confirm no relied-upon field is hidden by the redaction"},
]

_DATE_PATTERNS = [
    re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b"),
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),
    re.compile(
        r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)"
        r"\s+\d{1,2},?\s+\d{4}\b", re.IGNORECASE
    ),
]

_PAGE_MARKER_PATTERN = re.compile(r"\bpage\s+(\d+)\s+of\s+(\d+)\b", re.IGNORECASE)

_REDACTION_PATTERNS = [
    re.compile(r"\[\s*redacted\s*\]", re.IGNORECASE),
    re.compile(r"\bredacted\b", re.IGNORECASE),
    re.compile(r"[\u2588\u25A0]{3,}"),
    re.compile(r"X{6,}"),
]


@dataclass
class CompletenessFlag:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str = ""
    check_name: str = ""
    severity: str = "amber"
    detail: str = ""
    page_reference: Optional[int] = None
    resolution_status: str = "unresolved"
    resolution_note: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    resolved_at: Optional[str] = None


def _extract_distinct_dates(text: str) -> List[str]:
    found = []
    for pattern in _DATE_PATTERNS:
        found.extend(pattern.findall(text))
    seen = []
    for d in found:
        if d not in seen:
            seen.append(d)
    return seen


def _check_page_sequence(text: str) -> Optional[str]:
    """Purely mechanical: looks for embedded 'Page X of Y' markers (common in
    PDF-extracted text) and checks whether X values are a clean 1..Y run
    with a single agreed-upon Y. Returns a detail string if inconsistent,
    else None. This does NOT catch every out-of-sequence scenario -- FORGE
    only has a single extracted_text blob per document, not per-page text,
    so this is a best-effort mechanical scan, not a guarantee."""
    matches = _PAGE_MARKER_PATTERN.findall(text)
    if not matches:
        return None
    page_nums = [int(a) for a, b in matches]
    totals = {int(b) for a, b in matches}
    if len(totals) > 1:
        return f"The document states more than one total page count ({sorted(totals)}); this is inconsistent."
    total = totals.pop()
    expected = list(range(1, total + 1))
    if sorted(set(page_nums)) != expected or len(page_nums) != len(set(page_nums)):
        return (f"Page markers found ({sorted(page_nums)}) do not form a complete, "
                f"non-repeating sequence from 1 to {total}.")
    return None


def run_completeness_check(document_category: str, page_count, extracted_text: str,
                            ocr_confidence, existing_document_hashes: Optional[List[str]] = None,
                            this_hash: Optional[str] = None) -> List[CompletenessFlag]:
    text = extracted_text or ""

    if text.startswith(EXTRACTION_UNAVAILABLE_MARKER):
        return [CompletenessFlag(
            check_name="Text extraction", severity="red",
            detail=text.replace(EXTRACTION_UNAVAILABLE_MARKER, "").strip(),
        )]

    flags: List[CompletenessFlag] = []
    text_lower = text.lower()

    exhibit_markers = ["exhibit a", "exhibit b", "exhibit 1", "exhibit 2", "attachment 1", "see exhibit"]
    if any(marker in text_lower for marker in exhibit_markers):
        flags.append(CompletenessFlag(
            check_name="Referenced exhibits", severity="red",
            detail="The document text references an exhibit or attachment that may not be included in this upload.",
        ))

    requires_signature = document_category in (
        "Complaint, petition, answer, or other court filing", "Summons or service document",
        "Court order, notice, or scheduling order", "Criminal docket, judgment, or disposition",
    )
    if requires_signature and "signature" not in text_lower and "/s/" not in text_lower:
        flags.append(CompletenessFlag(
            check_name="Signature / certification page", severity="amber",
            detail="This document type typically includes a signature or certificate of service. "
                    "None was detected in the extracted text.",
        ))

    if ocr_confidence is not None and ocr_confidence < 0.55:
        flags.append(CompletenessFlag(
            check_name="Legibility", severity="amber",
            detail=f"Extraction confidence is low ({ocr_confidence:.0%}). Some text may not be reliably captured.",
        ))

    if existing_document_hashes and this_hash in existing_document_hashes:
        flags.append(CompletenessFlag(
            check_name="Duplicate detection", severity="info",
            detail="This file appears identical to a document already uploaded to this case.",
        ))

    if page_count is not None and page_count <= 0:
        flags.append(CompletenessFlag(
            check_name="Page continuity", severity="red",
            detail="No pages could be detected in this document.",
        ))
    else:
        page_issue = _check_page_sequence(text)
        if page_issue:
            flags.append(CompletenessFlag(
                check_name="Page continuity", severity="amber",
                detail=page_issue,
            ))

    distinct_dates = _extract_distinct_dates(text)
    if len(distinct_dates) > 1:
        flags.append(CompletenessFlag(
            check_name="Multiple dates detected", severity="info",
            detail=(
                f"This document contains {len(distinct_dates)} distinct dates: "
                f"{', '.join(distinct_dates)}. FORGE does not determine whether these are "
                f"consistent with each other -- please confirm they match what you expect "
                f"(e.g., an incident date vs. a filing date) rather than a conflict."
            ),
        ))

    if any(p.search(text) for p in _REDACTION_PATTERNS):
        flags.append(CompletenessFlag(
            check_name="Redaction markers", severity="amber",
            detail="This document appears to contain redacted or blacked-out sections. If a redaction "
                    "covers information FORGE would otherwise treat as a fact, upload an unredacted "
                    "version or confirm the redaction is expected.",
        ))

    return flags


def all_flags_resolved(flags: List[CompletenessFlag]) -> bool:
    return all(f.resolution_status in ("resolved", "acknowledged") for f in flags)


SECOND_LOOK_WARNING = (
    "**Before you continue:** This document is about to be marked ready for your records. "
    "Please confirm you have reviewed the full document, not just the extracted summary, and "
    "that every flag above has been addressed. FORGE organizes information -- it does not verify "
    "that your filing is legally sufficient, and it will never submit anything on your behalf."
)
