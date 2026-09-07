"""
FORGE Data Models
Protects three core commitments:
  1. Do not overbuild before the first complete path works.
  2. Keep the user's burden low (unsure/unknown are first-class values).
  3. Make uncertainty visible (precision, confidence, and strength tiers travel with every fact).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
import uuid


def new_id() -> str:
    return str(uuid.uuid4())


@dataclass
class AdditionalEvent:
    id: str = field(default_factory=new_id)
    event_date: Optional[str] = None
    event_date_precision: str = "unknown"
    person_involved: str = "unknown"
    event_type: str = ""
    has_related_document: Optional[bool] = None


@dataclass
class CaseProfile:
    id: str = field(default_factory=new_id)
    user_id: str = ""
    case_name: str = "Untitled Case"

    filing_status: Optional[str] = None
    federal_court: str = "United States District Court for the District of Maine"
    federal_court_confirmed: Optional[bool] = None
    incident_state: Optional[str] = None
    state_source_jurisdiction: Optional[str] = None
    state_source_confirmed: Optional[bool] = None

    event_types: List[str] = field(default_factory=list)
    primary_event_date: Optional[str] = None
    primary_event_date_precision: str = "unknown"
    primary_event_city: Optional[str] = None
    primary_event_county: Optional[str] = None
    primary_event_state: Optional[str] = None
    primary_event_narrative: Optional[str] = None
    additional_events: List[AdditionalEvent] = field(default_factory=list)

    related_proceeding_status: Optional[str] = None
    civil_case_filed: Optional[str] = None
    federal_case_number: Optional[str] = None
    judge_assigned: Optional[bool] = None
    assigned_district_judge: Optional[str] = None
    assigned_magistrate_judge: Optional[str] = None
    judge_practices_status: str = "not_applicable_yet"

    # FRCP 4(l)/4(m): tracked separately from judge/case-number fields because
    # proof of service has its own filing requirement and its own deadline
    # (service must be completed within 90 days of filing under Rule 4(m)),
    # independent of whether a judge has been assigned yet.
    # Values: None (not yet addressed), "filed" (affidavit of service filed
    # with the court), "not_yet_filed", "waived" (defendant returned a Rule
    # 4(d) waiver, so proof of service is not required), "not_applicable"
    # (e.g., user has not filed a civil case), "unsure".
    proof_of_service_status: Optional[str] = None

    first_document_category: Optional[str] = None

    intake_completed: bool = False
    intake_reviewed_confirmed: bool = False
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def completion_percent(self) -> int:
        checkpoints = [
            self.filing_status is not None,
            self.federal_court_confirmed is not None,
            self.incident_state is not None,
            bool(self.event_types),
            bool(self.primary_event_date_precision != "unknown" or self.primary_event_narrative),
            self.related_proceeding_status is not None,
            self.civil_case_filed is not None,
            self.first_document_category is not None,
        ]
        return round(100 * sum(checkpoints) / len(checkpoints))


@dataclass
class CaseVault:
    id: str = field(default_factory=new_id)
    case_id: str = ""
    storage_prefix: str = ""
    encryption_status: str = "required"
    access_status: str = "private"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class CaseDocument:
    id: str = field(default_factory=new_id)
    case_id: str = ""
    vault_id: str = ""
    original_filename: str = ""
    mime_type: str = ""
    storage_key: str = ""
    sha256: str = ""
    size_bytes: int = 0
    document_category: str = "other"
    upload_status: str = "uploaded"
    processing_status: str = "queued"
    ocr_confidence: Optional[float] = None
    page_count: Optional[int] = None
    extracted_text: Optional[str] = None
    completeness_status: str = "unreviewed"
    uploaded_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class FactSource:
    id: str = field(default_factory=new_id)
    source_document_id: Optional[str] = None
    source_page: Optional[int] = None
    source_quote: Optional[str] = None
    confidence: float = 0.0
    added_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class FactCard:
    id: str = field(default_factory=new_id)
    case_id: str = ""
    normalized_statement: str = ""
    fact_type: str = "other"
    sources: List[FactSource] = field(default_factory=list)
    strength_tier: str = "weak"
    status: str = "proposed"
    user_correction: Optional[str] = None
    last_verified_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    decay_window_days: int = 60
    needs_reverification: bool = False
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    reviewed_at: Optional[str] = None

    @property
    def source_count(self) -> int:
        return len(self.sources)

    @property
    def max_confidence(self) -> float:
        return max((s.confidence for s in self.sources), default=0.0)


@dataclass
class ContradictionFlag:
    id: str = field(default_factory=new_id)
    case_id: str = ""
    fact_card_id_a: str = ""
    fact_card_id_b: str = ""
    contradiction_type: str = "other"
    severity: str = "medium"
    detail: str = ""
    resolution_status: str = "unresolved"
    resolution_note: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    resolved_at: Optional[str] = None


@dataclass
class TimelineEvent:
    id: str = field(default_factory=new_id)
    case_id: str = ""
    event_date: Optional[str] = None
    date_precision: str = "unknown"
    title: str = ""
    event_type: str = ""
    description: str = ""
    source_type: str = "user_stated"
    source_fact_card_id: Optional[str] = None
    source_document_id: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class AuditEntry:
    id: str = field(default_factory=new_id)
    case_id: Optional[str] = None
    user_id: Optional[str] = None
    action: str = ""
    target_type: str = ""
    target_id: Optional[str] = None
    detail: dict = field(default_factory=dict)
    occurred_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
