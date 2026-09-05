"""
FORGE Phase 2A -- Document Completeness & Review Safeguard
Every uploaded document is treated as a starting point for verification,
never as a finished, trustworthy record on its own.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
import uuid

COMPLETENESS_CHECKS = [
    {"check": "Page continuity", "looks_for": "Missing or out-of-sequence page numbers",
     "if_flagged": "Amber flag; user must confirm pages are absent or upload missing pages"},
    {"check": "Legibility", "looks_for": "Blurred or low-contrast text OCR cannot confidently read",
     "if_flagged": "Amber flag on affected page; text excluded from proposed facts"},
    {"check": "Referenced exhibits", "looks_for": "Text referencing 'Exhibit A' etc. not present in the upload",
     "if_flagged": "Red flag; document incomplete until exhibit is uploaded or confirmed absent"},
    {"check": "Signature / certification page", "looks_for": "Missing signature on a document type that requires one",
     "if_flagged": "Amber flag; user asked to confirm whether a signed version exists"},
    {"check": "Date consistency within document", "looks_for": "Internal dates that conflict",
     "if_flagged": "Red flag; treated as a contradiction requiring resolution"},
    {"check": "Duplicate detection", "looks_for": "A file matching an already-uploaded document",
     "if_flagged": "Informational flag; user chooses to keep both, replace, or discard"},
    {"check": "Redaction consistency", "looks_for": "Redacted blocks obscuring a relied-upon field",
     "if_flagged": "Amber flag; redacted fields excluded from proposed facts"},
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


def run_completeness_check(document_category: str, page_count, extracted_text: str,
                            ocr_confidence, existing_document_hashes: Optional[List[str]] = None,
                            this_hash: Optional[str] = None) -> List[CompletenessFlag]:
    flags: List[CompletenessFlag] = []
    text_lower = (extracted_text or "").lower()

    exhibit_markers = ["exhibit a", "exhibit b", "exhibit 1", "exhibit 2", "attachment 1", "see exhibit"]
    if any(marker in text_lower for marker in exhibit_markers):
        flags.append(CompletenessFlag(
            check_name="Referenced exhibits", severity="red",
            detail="The document text references an exhibit or attachment that may not be included in this upload.",
        ))

    requires_signature = document_category in (
        "Complaint, petition, answer, or other court filing", "Summons or service document",
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

    return flags


def all_flags_resolved(flags: List[CompletenessFlag]) -> bool:
    return all(f.resolution_status in ("resolved", "acknowledged") for f in flags)


SECOND_LOOK_WARNING = (
    "**Before you continue:** This document is about to be marked ready for your records. "
    "Please confirm you have reviewed the full document, not just the extracted summary, and "
    "that every flag above has been addressed. FORGE organizes information -- it does not verify "
    "that your filing is legally sufficient, and it will never submit anything on your behalf."
)
