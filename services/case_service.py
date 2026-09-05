"""
FORGE Case Service -- in-memory reference implementation.
Wires in all four safeguard engines:
  - Document Completeness Check (Phase 2A)      -> services/completeness.py
  - Multi-Source Corroboration (24.1)           -> services/corroboration.py
  - Confidence Decay & Re-Verification (24.2)   -> services/corroboration.py
  - Contradiction Detection                     -> services/contradiction.py
"""
from __future__ import annotations
from typing import Optional, Dict, List
from .models import (
    CaseProfile, CaseVault, CaseDocument, FactCard, FactSource,
    TimelineEvent, AuditEntry, AdditionalEvent, ContradictionFlag
)
from .completeness import CompletenessFlag, run_completeness_check, all_flags_resolved
from .corroboration import add_source_and_recompute, scan_case_for_decay, reverify
from .contradiction import scan_case_for_contradictions, resolve_flag as resolve_contradiction_flag


class AuditService:
    def __init__(self):
        self._log: List[AuditEntry] = []

    def record(self, case_id, user_id, action, target_type="", target_id=None, detail=None):
        entry = AuditEntry(case_id=case_id, user_id=user_id, action=action,
                            target_type=target_type, target_id=target_id, detail=detail or {})
        self._log.append(entry)
        return entry

    def for_case(self, case_id: str) -> List[AuditEntry]:
        return [e for e in self._log if e.case_id == case_id]


class CaseService:
    def __init__(self, audit: AuditService):
        self.audit = audit
        self.cases: Dict[str, CaseProfile] = {}
        self.vaults: Dict[str, CaseVault] = {}

    def create_case(self, user_id: str, case_name: str = "My Case") -> CaseProfile:
        profile = CaseProfile(user_id=user_id, case_name=case_name)
        self.cases[profile.id] = profile
        vault = CaseVault(case_id=profile.id, storage_prefix=f"cases/{profile.id}/originals/")
        self.vaults[profile.id] = vault
        self.audit.record(profile.id, user_id, "case_created", "case_profile", profile.id, {"case_name": case_name})
        self.audit.record(profile.id, user_id, "vault_created", "case_vault", vault.id,
                           {"storage_prefix": vault.storage_prefix})
        return profile

    def get(self, case_id: str) -> Optional[CaseProfile]:
        return self.cases.get(case_id)

    def get_vault(self, case_id: str) -> Optional[CaseVault]:
        return self.vaults.get(case_id)

    def update_fields(self, case_id: str, user_id: str, **fields):
        profile = self.cases.get(case_id)
        if not profile:
            raise ValueError("Unknown case_id")
        changed = {}
        for key, value in fields.items():
            if hasattr(profile, key):
                old = getattr(profile, key)
                if old != value:
                    setattr(profile, key, value)
                    changed[key] = {"old": old, "new": value}
        if changed:
            self.audit.record(case_id, user_id, "case_profile_updated", "case_profile", case_id, changed)
        return profile

    def add_additional_event(self, case_id: str, user_id: str, event: AdditionalEvent):
        profile = self.cases.get(case_id)
        if not profile:
            raise ValueError("Unknown case_id")
        profile.additional_events.append(event)
        self.audit.record(case_id, user_id, "additional_event_added", "additional_event", event.id,
                           {"event_type": event.event_type, "precision": event.event_date_precision})
        return event

    def mark_intake_complete(self, case_id: str, user_id: str, confirmed: bool):
        profile = self.update_fields(case_id, user_id, intake_completed=True, intake_reviewed_confirmed=confirmed)
        self.audit.record(case_id, user_id, "intake_completed", "case_profile", case_id,
                           {"user_confirmed_summary": confirmed})
        return profile


class DocumentService:
    def __init__(self, audit: AuditService):
        self.audit = audit
        self.documents: Dict[str, CaseDocument] = {}
        self.completeness_flags: Dict[str, List[CompletenessFlag]] = {}

    def register_upload(self, case_id, vault_id, user_id, filename, mime_type, sha256, size_bytes,
                         document_category="other") -> CaseDocument:
        doc = CaseDocument(case_id=case_id, vault_id=vault_id, original_filename=filename, mime_type=mime_type,
                            storage_key=f"{case_id}/{filename}", sha256=sha256, size_bytes=size_bytes,
                            document_category=document_category)
        self.documents[doc.id] = doc
        self.completeness_flags[doc.id] = []
        self.audit.record(case_id, user_id, "document_uploaded", "case_document", doc.id,
                           {"filename": filename, "category": document_category, "size_bytes": size_bytes})
        return doc

    def set_processing_status(self, doc_id: str, user_id: str, status: str, **extra):
        doc = self.documents.get(doc_id)
        if not doc:
            raise ValueError("Unknown document id")
        doc.processing_status = status
        for k, v in extra.items():
            if hasattr(doc, k):
                setattr(doc, k, v)
        self.audit.record(doc.case_id, user_id, "document_processing_status_changed",
                           "case_document", doc_id, {"status": status})
        return doc

    def run_completeness_check(self, doc_id: str, user_id: str) -> List[CompletenessFlag]:
        doc = self.documents.get(doc_id)
        if not doc:
            raise ValueError("Unknown document id")
        existing_hashes = [d.sha256 for d in self.documents.values() if d.id != doc_id and d.case_id == doc.case_id]
        flags = run_completeness_check(
            document_category=doc.document_category, page_count=doc.page_count,
            extracted_text=doc.extracted_text, ocr_confidence=doc.ocr_confidence,
            existing_document_hashes=existing_hashes, this_hash=doc.sha256,
        )
        for f in flags:
            f.document_id = doc_id
        self.completeness_flags[doc_id] = flags
        doc.completeness_status = "flagged_incomplete" if flags else "unreviewed"
        self.audit.record(doc.case_id, user_id, "completeness_check_run", "case_document", doc_id,
                           {"flags_found": len(flags)})
        return flags

    def get_flags(self, doc_id: str) -> List[CompletenessFlag]:
        return self.completeness_flags.get(doc_id, [])

    def resolve_flag(self, doc_id: str, flag_id: str, user_id: str, action: str, note: Optional[str] = None):
        from datetime import datetime
        flags = self.completeness_flags.get(doc_id, [])
        for f in flags:
            if f.id == flag_id:
                f.resolution_status = action
                f.resolution_note = note
                f.resolved_at = datetime.utcnow().isoformat()
                self.audit.record(self.documents[doc_id].case_id, user_id, "completeness_flag_resolved",
                                   "completeness_flag", flag_id, {"action": action})
        return flags

    def confirm_completeness(self, doc_id: str, user_id: str, confirmed: bool):
        doc = self.documents.get(doc_id)
        if not doc:
            raise ValueError("Unknown document id")
        flags = self.completeness_flags.get(doc_id, [])
        if confirmed and not all_flags_resolved(flags):
            raise ValueError("All completeness flags must be resolved or acknowledged first.")
        doc.completeness_status = "user_confirmed_complete" if confirmed else "flagged_incomplete"
        self.audit.record(doc.case_id, user_id, "document_completeness_reviewed",
                           "case_document", doc_id, {"confirmed": confirmed})
        return doc

    def for_case(self, case_id: str) -> List[CaseDocument]:
        return [d for d in self.documents.values() if d.case_id == case_id]


class FactCardService:
    def __init__(self, audit: AuditService):
        self.audit = audit
        self.facts: Dict[str, FactCard] = {}

    def propose(self, case_id, normalized_statement, fact_type, confidence,
                source_document_id=None, source_page=None, source_quote=None) -> FactCard:
        fc = FactCard(case_id=case_id, normalized_statement=normalized_statement, fact_type=fact_type)
        source = FactSource(source_document_id=source_document_id, source_page=source_page,
                             source_quote=source_quote, confidence=confidence)
        add_source_and_recompute(fc, source)
        self.facts[fc.id] = fc
        self.audit.record(case_id, None, "fact_card_proposed", "fact_card", fc.id,
                           {"fact_type": fact_type, "confidence": confidence, "strength_tier": fc.strength_tier})
        return fc

    def add_corroborating_source(self, fact_id, user_id, source_document_id, source_page, source_quote, confidence):
        fc = self.facts.get(fact_id)
        if not fc:
            raise ValueError("Unknown fact id")
        source = FactSource(source_document_id=source_document_id, source_page=source_page,
                             source_quote=source_quote, confidence=confidence)
        add_source_and_recompute(fc, source)
        self.audit.record(fc.case_id, user_id, "fact_card_corroborated", "fact_card", fact_id,
                           {"new_strength_tier": fc.strength_tier, "source_count": fc.source_count})
        return fc

    def review(self, fact_id, user_id, action, correction=None):
        fc = self.facts.get(fact_id)
        if not fc:
            raise ValueError("Unknown fact id")
        fc.status = action
        if action == "corrected":
            fc.user_correction = correction
        from datetime import datetime
        fc.reviewed_at = datetime.utcnow().isoformat()
        self.audit.record(fc.case_id, user_id, "fact_card_reviewed", "fact_card", fact_id,
                           {"action": action, "correction": correction})
        return fc

    def reverify(self, fact_id, user_id):
        fc = self.facts.get(fact_id)
        if not fc:
            raise ValueError("Unknown fact id")
        reverify(fc)
        self.audit.record(fc.case_id, user_id, "fact_card_reverified", "fact_card", fact_id, {})
        return fc

    def scan_decay(self, case_id: str) -> List[FactCard]:
        return scan_case_for_decay(self.for_case(case_id))

    def scan_contradictions(self, case_id: str) -> List[ContradictionFlag]:
        return scan_case_for_contradictions(self.for_case(case_id))

    def for_case(self, case_id: str) -> List[FactCard]:
        return [f for f in self.facts.values() if f.case_id == case_id]

    def confirmed_for_case(self, case_id: str) -> List[FactCard]:
        return [f for f in self.facts.values() if f.case_id == case_id and f.status == "confirmed"]


class ContradictionService:
    def __init__(self, audit: AuditService):
        self.audit = audit
        self.flags: Dict[str, ContradictionFlag] = {}

    def store(self, flags: List[ContradictionFlag], user_id: Optional[str] = None):
        for flag in flags:
            if flag.id not in self.flags:
                self.flags[flag.id] = flag
                self.audit.record(flag.case_id, user_id, "contradiction_flagged", "contradiction_flag",
                                   flag.id, {"type": flag.contradiction_type, "severity": flag.severity})
        return flags

    def resolve(self, flag_id, user_id, action, note=None):
        flag = self.flags.get(flag_id)
        if not flag:
            raise ValueError("Unknown flag id")
        resolve_contradiction_flag(flag, action, note)
        self.audit.record(flag.case_id, user_id, "contradiction_resolved", "contradiction_flag",
                           flag_id, {"action": action})
        return flag

    def for_case(self, case_id: str) -> List[ContradictionFlag]:
        return [f for f in self.flags.values() if f.case_id == case_id]

    def unresolved_for_case(self, case_id: str) -> List[ContradictionFlag]:
        return [f for f in self.flags.values() if f.case_id == case_id and f.resolution_status == "unresolved"]


class TimelineService:
    def __init__(self, audit: AuditService):
        self.audit = audit
        self.events: Dict[str, TimelineEvent] = {}

    def add_event(self, case_id, user_id, title, event_type, event_date, date_precision, source_type,
                   description="", source_fact_card_id=None, source_document_id=None) -> TimelineEvent:
        ev = TimelineEvent(case_id=case_id, title=title, event_type=event_type, event_date=event_date,
                            date_precision=date_precision, source_type=source_type, description=description,
                            source_fact_card_id=source_fact_card_id, source_document_id=source_document_id)
        self.events[ev.id] = ev
        self.audit.record(case_id, user_id, "timeline_event_added", "timeline_event", ev.id,
                           {"title": title, "precision": date_precision, "source_type": source_type})
        return ev

    def for_case(self, case_id: str) -> List[TimelineEvent]:
        items = [e for e in self.events.values() if e.case_id == case_id]
        return sorted(items, key=lambda e: (e.event_date is None, e.event_date or ""))
