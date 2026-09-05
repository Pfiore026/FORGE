"""
FORGE Document Ingestion Pipeline (Phase 2 -- narrow first slice)
Supported types only: PDF, DOCX, JPG, PNG.
"""
from __future__ import annotations
import hashlib
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

SUPPORTED_MIME_TYPES = {
    "application/pdf": "pdf",
    "image/jpeg": "jpg",
    "image/png": "png",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
}
MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024

DATE_PATTERN = re.compile(
    r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|"
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4})\b",
    re.IGNORECASE
)
CASE_NUMBER_PATTERN = re.compile(r"\b\d{1,2}:\d{2}-cv-\d{3,6}(?:-[A-Z]{2,5})?\b")
AMOUNT_PATTERN = re.compile(r"\$\s?[\d,]+(?:\.\d{2})?")


@dataclass
class ValidationResult:
    is_valid: bool
    reason: Optional[str] = None
    normalized_type: Optional[str] = None


def validate_upload(filename: str, mime_type: str, size_bytes: int) -> ValidationResult:
    if size_bytes <= 0:
        return ValidationResult(False, "The file appears to be empty.")
    if size_bytes > MAX_FILE_SIZE_BYTES:
        return ValidationResult(False, f"File exceeds the {MAX_FILE_SIZE_BYTES // (1024*1024)} MB limit for this release.")
    if mime_type not in SUPPORTED_MIME_TYPES:
        return ValidationResult(False, "This file type is not yet supported. Supported types: PDF, DOCX, JPG, PNG.")
    return ValidationResult(True, normalized_type=SUPPORTED_MIME_TYPES[mime_type])


def compute_sha256(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


def extract_text_stub(file_bytes: bytes, normalized_type: str) -> Tuple[str, float, int]:
    if normalized_type == "docx":
        return "[DOCX text extraction not wired in this reference build.]", 0.5, 1
    if normalized_type == "pdf":
        return "[PDF text extraction not wired in this reference build.]", 0.5, 1
    return "[Image OCR not wired in this reference build.]", 0.4, 1


def propose_candidate_facts(extracted_text: str, page_number: int = 1) -> List[dict]:
    candidates = []
    for match in DATE_PATTERN.finditer(extracted_text):
        start, end = max(0, match.start() - 40), min(len(extracted_text), match.end() + 40)
        candidates.append({
            "normalized_statement": f"Document references date: {match.group(0)}",
            "fact_type": "date", "confidence": 0.6, "source_page": page_number,
            "source_quote": extracted_text[start:end].strip(),
        })
    for match in CASE_NUMBER_PATTERN.finditer(extracted_text):
        candidates.append({
            "normalized_statement": f"Document references case number: {match.group(0)}",
            "fact_type": "case_number", "confidence": 0.7, "source_page": page_number,
            "source_quote": match.group(0),
        })
    for match in AMOUNT_PATTERN.finditer(extracted_text):
        candidates.append({
            "normalized_statement": f"Document references amount: {match.group(0)}",
            "fact_type": "amount", "confidence": 0.55, "source_page": page_number,
            "source_quote": match.group(0),
        })
    return candidates


def run_pipeline(filename: str, mime_type: str, file_bytes: bytes) -> dict:
    validation = validate_upload(filename, mime_type, len(file_bytes))
    if not validation.is_valid:
        return {"status": "rejected", "reason": validation.reason}
    sha256 = compute_sha256(file_bytes)
    extracted_text, ocr_confidence, page_count = extract_text_stub(file_bytes, validation.normalized_type)
    candidate_facts = propose_candidate_facts(extracted_text, page_number=1)
    return {
        "status": "processed", "normalized_type": validation.normalized_type, "sha256": sha256,
        "extracted_text": extracted_text, "ocr_confidence": ocr_confidence,
        "page_count": page_count, "candidate_facts": candidate_facts,
    }
