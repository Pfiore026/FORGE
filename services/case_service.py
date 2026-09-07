"""
FORGE Case Service -- Supabase-backed implementation (Phase 2).

This replaces the earlier in-memory-dict reference implementation with real
Postgres persistence via the authenticated session's Supabase client
(services.db.get_session_client()). Every public method signature is
UNCHANGED from the in-memory version -- app.py requires no modification
beyond how the services are constructed.

Row Level Security on every table (case_profiles.user_id = auth.uid(), and
every other table cascading ownership through case_id) means the database
itself enforces per-user isolation. This module does not add its own
"WHERE user_id = ..." filtering on top of that -- RLS already guarantees no
query here can ever return or modify another user's rows, regardless of
what this code does or forgets to do.

Wires in all four safeguard engines (pure-logic modules, unchanged):
  - Document Completeness Check (Phase 2A)      -> services/completeness.py
  - Multi-Source Corroboration (24.1)           -> services/corroboration.py
  - Confidence Decay & Re-Verification (24.2)   -> services/corroboration.py
  - Contradiction Detection                     -> services/contradiction.py
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional, Dict, List

from .models import (
    CaseProfile, CaseVault, CaseDocument, FactCard, FactSource,
    TimelineEvent, AuditEntry, AdditionalEvent, ContradictionFlag
)
from .completeness import CompletenessFlag, run_completeness_check, all_flags_resolved
from .corroboration import compute_strength_tier, check_decay
from .contradiction import scan_case_for_contradictions, resolve_flag as resolve_contradiction_flag_logic

_CASE_PROFILE_FIELDS = {
    "filing_status", "federal_court", "federal_court_confirmed", "incident_state",
    "state_source_jurisdiction", "state_source_confirmed", "event_types",
    "primary_event_date", "primary_event_date_precision", "primary_event_city",
    "primary_event_county", "primary_event_state", "primary_event_narrative",
    "related_proceeding_status", "civil_case_filed", "federal_case_number",
    "judge_assigned", "assigned_district_judge", "assigned_magistrate_judge",
    "judge_practices_status", "proof_of_service_status", "first_document_category",
    "intake_completed", "intake_reviewed_confirmed",
}


def _row_to_case_profile(row: dict) -> CaseProfile:
    return CaseProfile(
        id=row["id"], user_id=row["user_id"], case_name=row.get("case_name") or "Untitled Case",
        filing_status=row.get("filing_status"), federal_court=row.get("federal_court") or CaseProfile.federal_court,
        federal_court_confirmed=row.get("federal_court_confirmed"), incident_state=row.get("incident_state"),
        state_source_jurisdiction=row.get("state_source_jurisdiction"),
        state_source_confirmed=row.get("state_source_confirmed"),
        event_types=row.get("event_types") or [], primary_event_date=row.get("primary_event_date"),
        primary_event_date_precision=row.get("primary_event_date_precision") or "unknown",
        primary_event_city=row.get("primary_event_city"), primary_event_county=row.get("primary_event_county"),
        primary_event_state=row.get("primary_event_state"), primary_event_narrative=row.get("primary_event_narrative"),
        related_proceeding_status=row.get("related_proceeding_status"),
        civil_case_filed=row.get("civil_case_filed"), federal_case_number=row.get("federal_case_number"),
        judge_assigned=row.get("judge_assigned"), assigned_district_judge=row.get("assigned_district_judge"),
        assigned_magistrate_judge=row.get("assigned_magistrate_judge"),
        judge_practices_status=row.get("judge_practices_status") or "not_applicable_yet",
        proof_of_service_status=row.get("proof_of_service_status"),
        first_document_category=row.get("first_document_category"),
        intake_completed=row.get("intake_completed") or False,
        intake_reviewed_confirmed=row.get("intake_reviewed_confirmed") or False,
        created_at=row.get("created_at") or "", updated_at=row.get("updated_at") or "",
    )


def _row_to_case_vault(row: dict) -> CaseVault:
    return CaseVault(
        id=row["id"], case_id=row["case_id"], storage_prefix=row.get("storage_prefix") or "",
        encryption_status=row.get("encryption_status") or "required",
        access_status=row.get("access_status") or "private", created_at=row.get("created_at") or "",
    )


def _row_to_case_document(row: dict) -> CaseDocument:
    return CaseDocument(
        id=row["id"], case_id=row["case_id"], vault_id=row["vault_id"],
        original_filename=row.get("original_filename") or "", mime_type=row.get("mime_type") or "",
        storage_key=row.get("storage_key") or "", sha256=row.get("sha256") or "",
        size_bytes=row.get("size_bytes") or 0, document_category=row.get("document_category") or "other",
        upload_status=row.get("upload_status") or "uploaded", processing_status=row.get("processing_status") or "queued",
        ocr_confidence=row.get("ocr_confidence"), page_count=row.get("page_count"),
        extracted_text=row.get("extracted_text"), completeness_status=row.get("completeness_status") or "unreviewed",
        uploaded_at=row.get("uploaded_at") or "",
    )


def _row_to_completeness_flag(row: dict) -> CompletenessFlag:
    return CompletenessFlag(
        id=row["id"], document_id=row.get("document_id") or "", check_name=row.get("check_name") or "",
        severity=row.get("severity") or "amber", detail=row.get("detail") or "",
        page_reference=row.get("page_reference"), resolution_status=row.get("resolution_status") or "unresolved",
        resolution_note=row.get("resolution_note"), created_at=row.get("created_at") or "",
        resolved_at=row.get("resolved_at"),
    )


def _row_to_fact_source(row: dict) -> FactSource:
    return FactSource(
        id=row["id"], source_document_id=row.get("source_document_id"), source_page=row.get("source_page"),
        source_quote=row.get("source_quote"), confidence=float(row.get("confidence") or 0.0),
        added_at=row.get("created_at") or "",
    )


def _row_to_fact_card(row: dict, sources: List[FactSource]) -> FactCard:
    return FactCard(
        id=row["id"], case_id=row["case_id"], normalized_statement=row.get("normalized_statement") or "",
        fact_type=row.get("fact_type") or "other", sources=sources, strength_tier=row.get("strength_tier") or "weak",
        status=row.get("status") or "proposed", user_correction=row.get("user_correction"),
        last_verified_at=row.get("last_verified_at") or "", decay_window_days=row.get("decay_window_days") or 60,
        needs_reverification=row.get("needs_reverification") or False, created_at=row.get("created_at") or "",
        reviewed_at=row.get("reviewed_at"),
    )


def _row_to_contradiction_flag(row: dict) -> ContradictionFlag:
    return ContradictionFlag(
        id=row["id"], case_id=row["case_id"], fact_card_id_a=row.get("fact_card_id_a") or "",
        fact_card_id_b=row.get("fact_card_id_b") or "", contradiction_type=row.get("contradiction_type") or "other",
        severity=row.get("severity") or "medium", detail=row.get("detail") or "",
        resolution_status=row.get("resolution_status") or "unresolved", resolution_note=row.get("resolution_note"),
        created_at=row.get("created_at") or "", resolved_at=row.get("resolved_at"),
    )


def _row_to_timeline_event(row: dict) -> TimelineEvent:
    return TimelineEvent(
        id=row["id"], case_id=row["case_id"], event_date=row.get("event_date"),
        date_precision=row.get("date_precision") or "unknown", title=row.get("title") or "",
        event_type=row.get("event_type") or "", description=row.get("description") or "",
        source_type=row.get("source_type") or "user_stated", source_fact_card_id=row.get("source_fact_card_id"),
        source_document_id=row.get("source_document_id"), created_at=row.get("created_at") or "",
    )


class AuditService:
    """Writes directly to public.audit_log. No RLS-bypassing filtering is
    performed here -- RLS on audit_log already scopes every query to rows
    whose case_id belongs to the authenticated user."""

    def __init__(self, client):
        self.client = client

    def record(self, case_id, user_id, action, target_type="", target_id=None, detail=None) -> AuditEntry:
        payload = {
            "case_id": case_id, "user_id": user_id, "action": action,
            "target_type": target_type, "target_id": target_id, "detail": detail or {},
        }
        resp = self.client.table("audit_log").insert(payload).execute()
        row = resp.data[0]
        return AuditEntry(
            id=row["id"], case_id=row.get("case_id"), user_id=row.get("user_id"), action=row.get("action") or "",
            target_type=row.get("target_type") or "", target_id=row.get("target_id"), detail=row.get("detail") or {},
            occurred_at=row.get("occurred_at") or "",
        )

    def for_case(self, case_id: str) -> List[AuditEntry]:
        resp = self.client.table("audit_log").select("*").eq("case_id", case_id).order("occurred_at").execute()
        return [
            AuditEntry(
                id=r["id"], case_id=r.get("case_id"), user_id=r.get("user_id"), action=r.get("action") or "",
                target_type=r.get("target_type") or "", target_id=r.get("target_id"), detail=r.get("detail") or {},
                occurred_at=r.get("occurred_at") or "",
            )
            for r in (resp.data or [])
        ]


class CaseService:
    def __init__(self, audit: AuditService, client):
        self.audit = audit
        self.client = client

    def create_case(self, user_id: str, case_name: str = "My Case") -> CaseProfile:
        resp = self.client.table("case_profiles").insert(
            {"user_id": user_id, "case_name": case_name}
        ).execute()
        row = resp.data[0]
        profile = _row_to_case_profile(row)
        vault_resp = self.client.table("case_vaults").insert(
            {"case_id": profile.id, "storage_prefix": f"cases/{profile.id}/originals/"}
        ).execute()
        vault_row = vault_resp.data[0]
        self.audit.record(profile.id, user_id, "case_created", "case_profile", profile.id, {"case_name": case_name})
        self.audit.record(profile.id, user_id, "vault_created", "case_vault", vault_row["id"],
                           {"storage_prefix": vault_row.get("storage_prefix")})
        return profile

    def get(self, case_id: str) -> Optional[CaseProfile]:
        resp = self.client.table("case_profiles").select("*").eq("id", case_id).maybe_single().execute()
        if not resp or not resp.data:
            return None
        return _row_to_case_profile(resp.data)

    def get_vault(self, case_id: str) -> Optional[CaseVault]:
        resp = self.client.table("case_vaults").select("*").eq("case_id", case_id).maybe_single().execute()
        if not resp or not resp.data:
            return None
        return _row_to_case_vault(resp.data)

    def update_fields(self, case_id: str, user_id: str, **fields):
        payload = {k: v for k, v in fields.items() if k in _CASE_PROFILE_FIELDS}
        if not payload:
            return self.get(case_id)
        before = self.get(case_id)
        resp = self.client.table("case_profiles").update(payload).eq("id", case_id).execute()
        row = resp.data[0]
        profile = _row_to_case_profile(row)
        changed = {}
        if before:
            for k, v in payload.items():
                old = getattr(before, k, None)
                if old != v:
                    changed[k] = {"old": old, "new": v}
        if changed:
            self.audit.record(case_id, user_id, "case_profile_updated", "case_profile", case_id, changed)
        return profile

    def add_additional_event(self, case_id: str, user_id: str, event: AdditionalEvent):
        payload = {
            "case_id": case_id, "event_date": event.event_date,
            "event_date_precision": event.event_date_precision, "person_involved": event.person_involved,
            "event_type": event.event_type, "has_related_document": event.has_related_document,
        }
        resp = self.client.table("additional_events").insert(payload).execute()
        row = resp.data[0]
        new_event = AdditionalEvent(
            id=row["id"], event_date=row.get("event_date"), event_date_precision=row.get("event_date_precision") or "unknown",
            person_involved=row.get("person_involved") or "unknown", event_type=row.get("event_type") or "",
            has_related_document=row.get("has_related_document"),
        )
        self.audit.record(case_id, user_id, "additional_event_added", "additional_event", new_event.id,
                           {"event_type": new_event.event_type, "precision": new_event.event_date_precision})
        return new_event

    def mark_intake_complete(self, case_id: str, user_id: str, confirmed: bool):
        profile = self.update_fields(case_id, user_id, intake_completed=True, intake_reviewed_confirmed=confirmed)
        self.audit.record(case_id, user_id, "intake_completed", "case_profile", case_id,
                           {"user_confirmed_summary": confirmed})
        return profile

    def for_user(self, user_id: str) -> List[CaseProfile]:
        """All cases belonging to this user, most recently updated first.
        Used on session start so a returning user resumes their existing
        case instead of silently getting a brand-new empty one -- without
        this, persistence would be pointless: the case_id itself was being
        regenerated fresh every new browser session even after Phase 2."""
        resp = (
            self.client.table("case_profiles").select("*").eq("user_id", user_id)
            .order("updated_at", desc=True).execute()
        )
        return [_row_to_case_profile(r) for r in (resp.data or [])]


class DocumentService:
    def __init__(self, audit: AuditService, client):
        self.audit = audit
        self.client = client

    def register_upload(self, case_id, vault_id, user_id, filename, mime_type, sha256, size_bytes,
                         document_category="other") -> CaseDocument:
        payload = {
            "case_id": case_id, "vault_id": vault_id, "original_filename": filename, "mime_type": mime_type,
            "storage_key": f"{case_id}/{filename}", "sha256": sha256, "size_bytes": size_bytes,
            "document_category": document_category,
        }
        resp = self.client.table("case_documents").insert(payload).execute()
        doc = _row_to_case_document(resp.data[0])
        self.audit.record(case_id, user_id, "document_uploaded", "case_document", doc.id,
                           {"filename": filename, "category": document_category, "size_bytes": size_bytes})
        return doc

    def set_processing_status(self, doc_id: str, user_id: str, status: str, **extra):
        allowed = {"ocr_confidence", "page_count", "extracted_text", "completeness_status", "upload_status"}
        payload = {"processing_status": status}
        payload.update({k: v for k, v in extra.items() if k in allowed})
        resp = self.client.table("case_documents").update(payload).eq("id", doc_id).execute()
        doc = _row_to_case_document(resp.data[0])
        self.audit.record(doc.case_id, user_id, "document_processing_status_changed",
                           "case_document", doc_id, {"status": status})
        return doc

    def run_completeness_check(self, doc_id: str, user_id: str) -> List[CompletenessFlag]:
        doc_resp = self.client.table("case_documents").select("*").eq("id", doc_id).single().execute()
        doc = _row_to_case_document(doc_resp.data)
        existing_resp = (
            self.client.table("case_documents").select("id, sha256")
            .eq("case_id", doc.case_id).neq("id", doc_id).execute()
        )
        existing_hashes = [r["sha256"] for r in (existing_resp.data or []) if r.get("sha256")]

        flags = run_completeness_check(
            document_category=doc.document_category, page_count=doc.page_count,
            extracted_text=doc.extracted_text, ocr_confidence=doc.ocr_confidence,
            existing_document_hashes=existing_hashes, this_hash=doc.sha256,
        )
        stored_flags = []
        for f in flags:
            payload = {
                "document_id": doc_id, "check_name": f.check_name, "severity": f.severity,
                "detail": f.detail, "page_reference": f.page_reference,
            }
            resp = self.client.table("completeness_flags").insert(payload).execute()
            stored_flags.append(_row_to_completeness_flag(resp.data[0]))

        new_status = "flagged_incomplete" if stored_flags else "unreviewed"
        self.client.table("case_documents").update({"completeness_status": new_status}).eq("id", doc_id).execute()
        self.audit.record(doc.case_id, user_id, "completeness_check_run", "case_document", doc_id,
                           {"flags_found": len(stored_flags)})
        return stored_flags

    def get_flags(self, doc_id: str) -> List[CompletenessFlag]:
        resp = self.client.table("completeness_flags").select("*").eq("document_id", doc_id).execute()
        return [_row_to_completeness_flag(r) for r in (resp.data or [])]

    def resolve_flag(self, doc_id: str, flag_id: str, user_id: str, action: str, note: Optional[str] = None):
        payload = {"resolution_status": action, "resolution_note": note, "resolved_at": datetime.utcnow().isoformat()}
        self.client.table("completeness_flags").update(payload).eq("id", flag_id).execute()
        doc_resp = self.client.table("case_documents").select("case_id").eq("id", doc_id).single().execute()
        self.audit.record(doc_resp.data["case_id"], user_id, "completeness_flag_resolved",
                           "completeness_flag", flag_id, {"action": action})
        return self.get_flags(doc_id)

    def confirm_completeness(self, doc_id: str, user_id: str, confirmed: bool):
        flags = self.get_flags(doc_id)
        if confirmed and not all_flags_resolved(flags):
            raise ValueError("All completeness flags must be resolved or acknowledged first.")
        new_status = "user_confirmed_complete" if confirmed else "flagged_incomplete"
        resp = self.client.table("case_documents").update(
            {"completeness_status": new_status}
        ).eq("id", doc_id).execute()
        doc = _row_to_case_document(resp.data[0])
        self.audit.record(doc.case_id, user_id, "document_completeness_reviewed",
                           "case_document", doc_id, {"confirmed": confirmed})
        return doc

    def for_case(self, case_id: str) -> List[CaseDocument]:
        resp = self.client.table("case_documents").select("*").eq("case_id", case_id).execute()
        return [_row_to_case_document(r) for r in (resp.data or [])]

    def category_lookup(self, case_id: str) -> Dict[str, str]:
        resp = self.client.table("case_documents").select("id, document_category").eq("case_id", case_id).execute()
        return {r["id"]: r.get("document_category") for r in (resp.data or [])}


class FactCardService:
    def __init__(self, audit: AuditService, client):
        self.audit = audit
        self.client = client

    def _sources_for(self, fact_card_id: str) -> List[FactSource]:
        resp = self.client.table("fact_card_sources").select("*").eq("fact_card_id", fact_card_id).execute()
        return [_row_to_fact_source(r) for r in (resp.data or [])]

    def propose(self, case_id, normalized_statement, fact_type, confidence,
                source_document_id=None, source_page=None, source_quote=None) -> FactCard:
        fc_resp = self.client.table("fact_cards").insert(
            {"case_id": case_id, "normalized_statement": normalized_statement, "fact_type": fact_type}
        ).execute()
        fc_row = fc_resp.data[0]
        fact_id = fc_row["id"]

        self.client.table("fact_card_sources").insert({
            "fact_card_id": fact_id, "source_document_id": source_document_id,
            "source_page": source_page, "source_quote": source_quote, "confidence": confidence,
        }).execute()

        sources = self._sources_for(fact_id)
        temp_fc = _row_to_fact_card(fc_row, sources)
        strength = compute_strength_tier(temp_fc)
        update_resp = self.client.table("fact_cards").update({
            "strength_tier": strength, "last_verified_at": datetime.utcnow().isoformat(),
            "needs_reverification": False,
        }).eq("id", fact_id).execute()
        fc = _row_to_fact_card(update_resp.data[0], sources)

        self.audit.record(case_id, None, "fact_card_proposed", "fact_card", fc.id,
                           {"fact_type": fact_type, "confidence": confidence, "strength_tier": fc.strength_tier})
        return fc

    def add_corroborating_source(self, fact_id, user_id, source_document_id, source_page, source_quote, confidence):
        self.client.table("fact_card_sources").insert({
            "fact_card_id": fact_id, "source_document_id": source_document_id,
            "source_page": source_page, "source_quote": source_quote, "confidence": confidence,
        }).execute()
        fc_resp = self.client.table("fact_cards").select("*").eq("id", fact_id).single().execute()
        sources = self._sources_for(fact_id)
        temp_fc = _row_to_fact_card(fc_resp.data, sources)
        strength = compute_strength_tier(temp_fc)
        update_resp = self.client.table("fact_cards").update({
            "strength_tier": strength, "last_verified_at": datetime.utcnow().isoformat(),
            "needs_reverification": False,
        }).eq("id", fact_id).execute()
        fc = _row_to_fact_card(update_resp.data[0], sources)
        self.audit.record(fc.case_id, user_id, "fact_card_corroborated", "fact_card", fact_id,
                           {"new_strength_tier": fc.strength_tier, "source_count": fc.source_count})
        return fc

    def review(self, fact_id, user_id, action, correction=None):
        payload = {"status": action, "reviewed_at": datetime.utcnow().isoformat()}
        if action == "corrected":
            payload["user_correction"] = correction
        resp = self.client.table("fact_cards").update(payload).eq("id", fact_id).execute()
        sources = self._sources_for(fact_id)
        fc = _row_to_fact_card(resp.data[0], sources)
        self.audit.record(fc.case_id, user_id, "fact_card_reviewed", "fact_card", fact_id,
                           {"action": action, "correction": correction})
        return fc

    def reverify(self, fact_id, user_id):
        resp = self.client.table("fact_cards").update({
            "last_verified_at": datetime.utcnow().isoformat(), "needs_reverification": False,
        }).eq("id", fact_id).execute()
        sources = self._sources_for(fact_id)
        fc = _row_to_fact_card(resp.data[0], sources)
        self.audit.record(fc.case_id, user_id, "fact_card_reverified", "fact_card", fact_id, {})
        return fc

    def scan_decay(self, case_id: str) -> List[FactCard]:
        facts = self.for_case(case_id)
        stale = []
        for fact in facts:
            if check_decay(fact):
                self.client.table("fact_cards").update(
                    {"needs_reverification": True}
                ).eq("id", fact.id).execute()
                stale.append(fact)
        return stale

    def scan_contradictions(self, case_id: str, document_categories: Optional[Dict[str, str]] = None) -> List[ContradictionFlag]:
        return scan_case_for_contradictions(self.for_case(case_id), document_categories=document_categories)

    def for_case(self, case_id: str) -> List[FactCard]:
        resp = self.client.table("fact_cards").select("*").eq("case_id", case_id).execute()
        rows = resp.data or []
        if not rows:
            return []
        fact_ids = [r["id"] for r in rows]
        sources_resp = self.client.table("fact_card_sources").select("*").in_("fact_card_id", fact_ids).execute()
        sources_by_fact: Dict[str, List[FactSource]] = {}
        for r in (sources_resp.data or []):
            sources_by_fact.setdefault(r["fact_card_id"], []).append(_row_to_fact_source(r))
        return [_row_to_fact_card(r, sources_by_fact.get(r["id"], [])) for r in rows]

    def confirmed_for_case(self, case_id: str) -> List[FactCard]:
        return [f for f in self.for_case(case_id) if f.status == "confirmed"]


class ContradictionService:
    def __init__(self, audit: AuditService, client):
        self.audit = audit
        self.client = client

    def _existing_pair_exists(self, case_id, a, b, contradiction_type) -> bool:
        """Checks both orderings of (fact_card_id_a, fact_card_id_b) so the
        same underlying pair is never flagged twice, in either direction,
        regardless of resolution status -- prevents the duplicate-row bug
        that would otherwise re-insert the same contradiction on every
        Streamlit rerun (step_5 re-scans on every interaction)."""
        resp = (
            self.client.table("contradiction_flags").select("id")
            .eq("case_id", case_id).eq("contradiction_type", contradiction_type)
            .or_(f"and(fact_card_id_a.eq.{a},fact_card_id_b.eq.{b}),"
                 f"and(fact_card_id_a.eq.{b},fact_card_id_b.eq.{a})")
            .execute()
        )
        return bool(resp.data)

    def store(self, flags: List[ContradictionFlag], user_id: Optional[str] = None):
        stored = []
        for flag in flags:
            if self._existing_pair_exists(flag.case_id, flag.fact_card_id_a, flag.fact_card_id_b,
                                            flag.contradiction_type):
                continue
            resp = self.client.table("contradiction_flags").insert({
                "case_id": flag.case_id, "fact_card_id_a": flag.fact_card_id_a,
                "fact_card_id_b": flag.fact_card_id_b, "contradiction_type": flag.contradiction_type,
                "severity": flag.severity, "detail": flag.detail,
            }).execute()
            new_flag = _row_to_contradiction_flag(resp.data[0])
            stored.append(new_flag)
            self.audit.record(new_flag.case_id, user_id, "contradiction_flagged", "contradiction_flag",
                               new_flag.id, {"type": new_flag.contradiction_type, "severity": new_flag.severity})
        return stored

    def resolve(self, flag_id, user_id, action, note=None):
        payload = {"resolution_status": action, "resolution_note": note, "resolved_at": datetime.utcnow().isoformat()}
        resp = self.client.table("contradiction_flags").update(payload).eq("id", flag_id).execute()
        flag = _row_to_contradiction_flag(resp.data[0])
        self.audit.record(flag.case_id, user_id, "contradiction_resolved", "contradiction_flag",
                           flag_id, {"action": action})
        return flag

    def for_case(self, case_id: str) -> List[ContradictionFlag]:
        resp = self.client.table("contradiction_flags").select("*").eq("case_id", case_id).execute()
        return [_row_to_contradiction_flag(r) for r in (resp.data or [])]

    def unresolved_for_case(self, case_id: str) -> List[ContradictionFlag]:
        resp = (
            self.client.table("contradiction_flags").select("*")
            .eq("case_id", case_id).eq("resolution_status", "unresolved").execute()
        )
        return [_row_to_contradiction_flag(r) for r in (resp.data or [])]


class TimelineService:
    def __init__(self, audit: AuditService, client):
        self.audit = audit
        self.client = client

    def add_event(self, case_id, user_id, title, event_type, event_date, date_precision, source_type,
                   description="", source_fact_card_id=None, source_document_id=None) -> TimelineEvent:
        payload = {
            "case_id": case_id, "title": title, "event_type": event_type, "event_date": event_date,
            "date_precision": date_precision, "source_type": source_type, "description": description,
            "source_fact_card_id": source_fact_card_id, "source_document_id": source_document_id,
        }
        resp = self.client.table("timeline_events").insert(payload).execute()
        ev = _row_to_timeline_event(resp.data[0])
        self.audit.record(case_id, user_id, "timeline_event_added", "timeline_event", ev.id,
                           {"title": title, "precision": date_precision, "source_type": source_type})
        return ev

    def for_case(self, case_id: str) -> List[TimelineEvent]:
        resp = (
            self.client.table("timeline_events").select("*").eq("case_id", case_id)
            .order("event_date", desc=False, nullsfirst=False).execute()
        )
        return [_row_to_timeline_event(r) for r in (resp.data or [])]
