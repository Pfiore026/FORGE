"""Inspection, validation, review, and source-cited relationship services.

Provider-specific OCR calls remain intentionally outside this module. A worker
may use Azure, Mistral, Google, AWS, or a local engine, but must return source
citations and never replace the immutable original record.
"""
from __future__ import annotations
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from .models import (DocumentRecord, ExtractedField, FactAssertion, ProcessingState, ReviewTask, SourceCitation)

HIGH_RISK_FIELDS = {
    "name", "address", "case_number", "docket_number", "incident_date",
    "incident_datetime", "deadline", "monetary_amount", "statute_citation",
}

@dataclass(frozen=True)
class InspectionResult:
    sha256: str
    byte_size: int
    native_text_present: bool | None
    recommended_route: str
    flags: tuple[str, ...] = ()

def inspect_upload(payload: bytes, filename: str, mime_type: str) -> InspectionResult:
    digest = hashlib.sha256(payload).hexdigest()
    if not payload:
        return InspectionResult(digest, 0, None, "reject", ("zero_byte_file",))
    is_pdf = mime_type == "application/pdf" or filename.lower().endswith(".pdf")
    if not is_pdf:
        return InspectionResult(digest, len(payload), None, "manual_or_supported_parser", ("non_pdf",))
    flags = () if payload.startswith(b"%PDF") else ("pdf_signature_not_detected",)
    native = any(marker in payload for marker in (b"/Font", b"/ToUnicode", b"BT"))
    return InspectionResult(digest, len(payload), native, "native_text_then_layout" if native else "render_then_ocr", flags)

def apply_inspection(document: DocumentRecord, result: InspectionResult) -> DocumentRecord:
    document.sha256 = result.sha256
    document.byte_size = result.byte_size
    document.native_text_present = result.native_text_present
    document.state = ProcessingState.REJECTED if result.recommended_route == "reject" else ProcessingState.INSPECTED
    return document

def original_storage_key(case_id: str, document_id: str, filename: str) -> str:
    return f"cases/{case_id}/originals/{document_id}/{Path(filename).name.replace(' ', '_')}"

def validate_citation(citation: SourceCitation) -> list[str]:
    errors: list[str] = []
    if citation.page_number < 1: errors.append("page_number_must_be_positive")
    if not citation.verbatim_source_text.strip(): errors.append("missing_verbatim_source_text")
    if not citation.bounding_box.valid(): errors.append("invalid_bounding_box")
    if citation.ocr_confidence is not None and not 0 <= citation.ocr_confidence <= 1: errors.append("invalid_ocr_confidence")
    return errors

def validate_field(field: ExtractedField) -> tuple[list[str], bool]:
    errors: list[str] = []
    if not field.raw_value.strip(): errors.append("empty_raw_value")
    if not field.citations: errors.append("field_has_no_source_citation")
    for citation in field.citations: errors.extend(validate_citation(citation))
    low_ocr = any(c.ocr_confidence is not None and c.ocr_confidence < .90 for c in field.citations)
    return list(dict.fromkeys(errors)), bool(errors) or low_ocr or field.field_name in HIGH_RISK_FIELDS

def field_review_task(case_id: str, field: ExtractedField) -> ReviewTask | None:
    errors, required = validate_field(field)
    if not required: return None
    reason = "; ".join(errors) if errors else "high_risk_or_low_confidence_field"
    priority = "high" if field.field_name in HIGH_RISK_FIELDS else "normal"
    return ReviewTask(case_id, "field_review", reason, field.id, priority=priority)

def detect_conflicts(assertions: list[FactAssertion]) -> list[tuple[FactAssertion, FactAssertion]]:
    groups: dict[tuple[str, str], list[FactAssertion]] = {}
    for item in assertions: groups.setdefault((item.subject.casefold(), item.predicate.casefold()), []).append(item)
    conflicts: list[tuple[FactAssertion, FactAssertion]] = []
    for candidates in groups.values():
        for index, left in enumerate(candidates):
            for right in candidates[index + 1:]:
                if left.value.strip().casefold() != right.value.strip().casefold(): conflicts.append((left, right))
    return conflicts

@dataclass
class DiscoveryGraph:
    nodes: dict[str, dict] = field(default_factory=dict)
    edges: list[dict] = field(default_factory=list)
    def add_node(self, node_id: str, kind: str, label: str, source_ids: list[str] | None = None) -> None:
        self.nodes[node_id] = {"kind": kind, "label": label, "source_ids": source_ids or []}
    def connect(self, source_id: str, target_id: str, relationship: str) -> None:
        if source_id not in self.nodes or target_id not in self.nodes: raise KeyError("Both nodes must exist")
        self.edges.append({"source_id": source_id, "target_id": target_id, "relationship": relationship})
    def trace_sources(self, node_id: str) -> set[str]:
        sources = set(self.nodes[node_id]["source_ids"])
        for edge in self.edges:
            if node_id in (edge["source_id"], edge["target_id"]):
                other = edge["target_id"] if edge["source_id"] == node_id else edge["source_id"]
                sources.update(self.nodes[other]["source_ids"])
        return sources

def neutral_gap_prompt(reference_label: str, missing_detail: str) -> str:
    return f"{reference_label} references {missing_detail}. You may add this as a source-linked factual topic to your discovery-planning records."
