"""Source-preserving data models for FORGE Discovery Workspace."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

def uid(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"

def utcnow() -> datetime:
    return datetime.now(UTC)

class DocumentKind(str, Enum):
    COURT_FILING = "court_filing"
    COURT_ORDER = "court_order"
    DISCOVERY_REQUEST = "discovery_request"
    DISCOVERY_RESPONSE = "discovery_response"
    CORRESPONDENCE = "correspondence"
    EVIDENCE_RECORD = "evidence_record"
    WITNESS_MATERIAL = "witness_material"
    ADMINISTRATIVE_RECORD = "administrative_record"
    UNKNOWN = "unknown"

class ExtractionMethod(str, Enum):
    NATIVE_TEXT = "native_text"
    OCR = "ocr"
    USER_ENTERED = "user_entered"

class ProcessingState(str, Enum):
    RECEIVED = "received"
    INSPECTED = "inspected"
    EXTRACTING = "extracting"
    REVIEW_REQUIRED = "review_required"
    COMPLETE = "complete"
    REJECTED = "rejected"

class ReviewState(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    CORRECTED = "corrected"
    UNREADABLE = "unreadable"
    DISMISSED = "dismissed"

@dataclass(frozen=True)
class BoundingBox:
    x: float
    y: float
    width: float
    height: float
    def valid(self) -> bool:
        values = (self.x, self.y, self.width, self.height)
        return all(0.0 <= value <= 1.0 for value in values) and self.x + self.width <= 1.0 and self.y + self.height <= 1.0

@dataclass
class DocumentRecord:
    case_id: str
    original_filename: str
    sha256: str
    mime_type: str
    byte_size: int
    storage_object_id: str
    source_classification: str
    id: str = field(default_factory=lambda: uid("doc"))
    version_id: str = field(default_factory=lambda: uid("ver"))
    kind: DocumentKind = DocumentKind.UNKNOWN
    state: ProcessingState = ProcessingState.RECEIVED
    uploaded_at: datetime = field(default_factory=utcnow)
    page_count: int | None = None
    native_text_present: bool | None = None
    parent_document_id: str | None = None
    relationship: str | None = None

@dataclass
class SourceCitation:
    document_id: str
    document_version_id: str
    page_number: int
    bounding_box: BoundingBox
    verbatim_source_text: str
    extraction_method: ExtractionMethod
    id: str = field(default_factory=lambda: uid("cite"))
    ocr_confidence: float | None = None
    extraction_confidence: float | None = None
    review_state: ReviewState = ReviewState.PENDING

@dataclass
class ExtractedField:
    document_id: str
    field_name: str
    raw_value: str
    citations: list[SourceCitation]
    id: str = field(default_factory=lambda: uid("field"))
    normalized_value: str | None = None
    normalization_status: str = "unprocessed"
    validation_messages: list[str] = field(default_factory=list)
    review_state: ReviewState = ReviewState.PENDING

@dataclass
class FactAssertion:
    case_id: str
    subject: str
    predicate: str
    value: str
    source_field_ids: list[str]
    id: str = field(default_factory=lambda: uid("fact"))
    status: str = "unresolved"
    user_verified: bool = False
    conflict_ids: list[str] = field(default_factory=list)

@dataclass
class RuleSource:
    court: str
    authority_level: int
    title: str
    version_label: str
    source_url: str
    id: str = field(default_factory=lambda: uid("rule"))
    effective_date: str | None = None
    verified_at: datetime | None = None
    content_hash: str | None = None

@dataclass
class ReviewTask:
    case_id: str
    task_type: str
    reason: str
    target_id: str
    id: str = field(default_factory=lambda: uid("review"))
    priority: str = "normal"
    state: ReviewState = ReviewState.PENDING
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class InterrogatoryTopic:
    case_id: str
    target_party: str
    factual_topic: str
    source_field_ids: list[str]
    source_document_ids: list[str]
    category: str
    id: str = field(default_factory=lambda: uid("inttopic"))
    discrete_subpart_count: int = 1
    related_deposition_topic_ids: list[str] = field(default_factory=list)
    status: str = "idea"
    user_notes: str = ""

@dataclass
class DepositionTopic:
    case_id: str
    label: str
    source_field_ids: list[str]
    source_document_ids: list[str]
    id: str = field(default_factory=lambda: uid("deptopic"))
    related_interrogatory_topic_ids: list[str] = field(default_factory=list)
    status: str = "identified"
    user_notes: str = ""

@dataclass
class ProceduralPreflight:
    court_verified: bool = False
    federal_rule_source_id: str | None = None
    local_rule_source_id: str | None = None
    scheduling_order_source_id: str | None = None
    judge_practices_source_id: str | None = None
    discovery_status_confirmed: bool = False
    target_is_party_confirmed: bool = False
    interrogatory_count_reviewed: bool = False
    user_acknowledged_not_legal_advice: bool = False
    def missing(self) -> list[str]:
        checks = {
            "court_verified": self.court_verified,
            "federal_rule_source": bool(self.federal_rule_source_id),
            "local_rule_source": bool(self.local_rule_source_id),
            "scheduling_order_source": bool(self.scheduling_order_source_id),
            "discovery_status_confirmed": self.discovery_status_confirmed,
            "target_is_party_confirmed": self.target_is_party_confirmed,
            "interrogatory_count_reviewed": self.interrogatory_count_reviewed,
            "not_legal_advice_acknowledgment": self.user_acknowledged_not_legal_advice,
        }
        return [key for key, ready in checks.items() if not ready]
