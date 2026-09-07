"""
FORGE -- Main Application Entry Point
The Forge Path: a five-step guided intake plus the Document Intelligence
Engine's full safeguard stack (completeness check, corroboration, decay,
contradiction detection), followed by a persistent Case Workspace with
FRCP Rule 6 deadline computation and strict-citation rule lookups.

Run with: streamlit run app.py
"""
import streamlit as st
import datetime

from services.case_service import (
    AuditService, CaseService, DocumentService, FactCardService,
    ContradictionService, TimelineService
)
from services.state_registry import US_STATES
from services.corroboration import STRENGTH_LABELS
from services.completeness import SECOND_LOOK_WARNING
from services.deadline_service import DeadlineService, KNOWN_TRIGGERS
from services.deadline_engine import MissingVariableError
from services.ui_theme import inject_theme, render_hero, render_stepper, render_chip

st.set_page_config(page_title="FORGE - Your Path to Justice", page_icon="scales", layout="centered")
inject_theme()


def init_services():
    if "audit" not in st.session_state:
        st.session_state.audit = AuditService()
    if "case_service" not in st.session_state:
        st.session_state.case_service = CaseService(st.session_state.audit)
    if "document_service" not in st.session_state:
        st.session_state.document_service = DocumentService(st.session_state.audit)
    if "fact_service" not in st.session_state:
        st.session_state.fact_service = FactCardService(st.session_state.audit)
    if "contradiction_service" not in st.session_state:
        st.session_state.contradiction_service = ContradictionService(st.session_state.audit)
    if "timeline_service" not in st.session_state:
        st.session_state.timeline_service = TimelineService(st.session_state.audit)
    if "deadline_service" not in st.session_state:
        st.session_state.deadline_service = DeadlineService(st.session_state.audit)
    if "user_id" not in st.session_state:
        st.session_state.user_id = "demo-user-0001"
    if "case_id" not in st.session_state:
        profile = st.session_state.case_service.create_case(st.session_state.user_id, "My FORGE Case")
        st.session_state.case_id = profile.id
    if "forge_step" not in st.session_state:
        st.session_state.forge_step = 1


init_services()

case_service = st.session_state.case_service
document_service = st.session_state.document_service
fact_service = st.session_state.fact_service
contradiction_service = st.session_state.contradiction_service
timeline_service = st.session_state.timeline_service
deadline_service = st.session_state.deadline_service
user_id = st.session_state.user_id
case_id = st.session_state.case_id
profile = case_service.get(case_id)

STEP_LABELS = {
    1: "Set Your Foundation", 2: "Tell Your Story", 3: "Map Your Case",
    4: "Gather Your Record", 5: "Review Your Path",
}


def render_progress():
    step = st.session_state.forge_step
    st.markdown(f"### Step {step} of 5 - {STEP_LABELS[step]}")
    st.progress(step / 5)
    render_chip("Foundation strength", f"{profile.completion_percent()}%")
    st.caption("This reflects how much of your record is organized, not how strong your case is.")
    st.divider()


def go_to(step: int):
    st.session_state.forge_step = step
    st.rerun()


EVENT_TYPE_OPTIONS = [
    "Arrest, detention, or criminal charge", "Police or law-enforcement encounter",
    "Search, seizure, or property taken", "Injury or use-of-force incident",
    "Action by a government agency", "Employment or workplace event",
    "Housing, property, or contract-related event", "Another type of event", "I am not sure",
]

DOCUMENT_CATEGORY_OPTIONS = [
    "Complaint, petition, answer, or other court filing", "Court order, notice, or scheduling order",
    "Docket sheet", "Summons or service document", "Police, arrest, or incident report",
    "Criminal docket, judgment, or disposition",
    "Photograph, video, medical record, email, letter, or message", "I do not have a document ready",
]

DOCUMENT_CATEGORY_TO_GUIDANCE = {
    "Complaint, petition, answer, or other court filing": "Upload every page, including exhibits if available.",
    "Court order, notice, or scheduling order": "Upload the full order. Note any stated deadlines when reviewing extracted facts.",
    "Docket sheet": "Upload the most recent full docket, not a partial screenshot.",
    "Summons or service document": "Upload all pages, including the proof of service if attached.",
    "Police, arrest, or incident report": "Upload the entire report, including supplements if you have them.",
    "Criminal docket, judgment, or disposition": "Upload the docket sheet and any judgment or dismissal order.",
    "Photograph, video, medical record, email, letter, or message": "Upload the file as-is.",
    "I do not have a document ready": "That is okay. You can add a document later.",
}


def step_1():
    render_progress()
    st.write("You do not need every document or answer today. Start with what you know. "
             "You can return and add information as you find it.")

    filing_status = st.radio(
        "What best describes where you are today?",
        [
            "I am gathering information and have not filed a civil case.",
            "I have already filed a civil case.",
            "Someone else filed a civil case involving me.",
            "I am not sure.",
        ], index=None, key="filing_status_radio",
    )

    st.info(
        "FORGE is currently set up for federal civil cases in the "
        "United States District Court for the District of Maine."
    )
    court_confirmed = st.radio(
        "Is this the federal court connected to your matter?",
        ["Yes", "No", "I am not sure"], index=None, key="court_confirmed_radio",
    )
    if court_confirmed in ("No", "I am not sure"):
        st.warning(
            "FORGE can still help you organize your information. Court-specific federal "
            "procedure will remain unverified until the correct court is confirmed."
        )

    state_options = ["I am not sure yet"] + sorted(US_STATES.keys())
    incident_state = st.selectbox(
        "What state is most connected to what happened?", state_options, key="incident_state_select",
    )

    st.divider()
    col1, col2 = st.columns(2)
    with col2:
        if st.button("Continue", type="primary", use_container_width=True):
            if filing_status is None or court_confirmed is None:
                st.error("Please answer both questions above before continuing.")
            else:
                case_service.update_fields(
                    case_id, user_id,
                    filing_status={
                        "I am gathering information and have not filed a civil case.": "pre_filing",
                        "I have already filed a civil case.": "filed",
                        "Someone else filed a civil case involving me.": "filed_against_me",
                        "I am not sure.": "unsure",
                    }[filing_status],
                    federal_court_confirmed=(court_confirmed == "Yes"),
                    incident_state=None if incident_state == "I am not sure yet" else incident_state,
                    state_source_jurisdiction=None if incident_state == "I am not sure yet" else incident_state,
                )
                st.success("Foundation set. FORGE now knows the starting court workspace "
                           "and the state sources that may be relevant for your records.")
                go_to(2)


def step_2():
    render_progress()
    st.write("Use your own words. Do not worry about legal terms, perfect dates, or organizing everything at once.")

    event_types = st.multiselect(
        "What type of event started this matter? Select all that apply.",
        EVENT_TYPE_OPTIONS, key="event_types_select",
    )

    precision = st.radio(
        "When did the earliest event happen?",
        ["I know the exact date.", "I know the approximate date.", "I do not know yet."],
        index=None, key="date_precision_radio",
    )

    event_date = None
    if precision == "I know the exact date.":
        event_date = st.date_input("Date", max_value=datetime.date.today(), key="exact_date_input")
    elif precision == "I know the approximate date.":
        event_date = st.text_input("Approximate date (month / year)", key="approx_date_input")

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        city = st.text_input("City", key="event_city")
    with col_b:
        county = st.text_input("County", key="event_county")
    with col_c:
        state = st.text_input("State", key="event_state_text")

    narrative = st.text_area(
        "In a few sentences, what happened?", key="event_narrative",
        help="FORGE will keep this as your own account and will not treat it as document-verified "
             "unless a source record is later connected.",
    )

    st.divider()
    involves_arrest = any(
        t in event_types for t in
        ["Arrest, detention, or criminal charge", "Police or law-enforcement encounter"]
    )

    if involves_arrest:
        st.markdown("#### Arrest and related proceeding")
        st.radio("Was anyone arrested or charged in connection with this event?",
                 ["Yes", "No", "I am not sure"], index=None, key="arrest_yn")
        if st.session_state.get("arrest_yn") == "Yes":
            st.radio("Who was arrested or charged?",
                      ["Me", "Another person", "Both", "I prefer not to answer yet"],
                      index=None, key="arrest_person")
            num_additional = st.number_input(
                "How many additional arrests, detentions, or charges are connected to this matter?",
                min_value=0, max_value=10, value=0, key="num_additional_arrests")
            for i in range(int(num_additional)):
                st.markdown(f"Additional event #{i+1}")
                st.text_input(f"Date (exact, approximate, or 'unknown') #{i+1}", key=f"add_date_{i}")
                st.selectbox(f"Person involved #{i+1}", ["Me", "Another person", "Unknown"], key=f"add_person_{i}")
                st.text_input(f"What happened #{i+1}", key=f"add_type_{i}")
                st.radio(f"Related document available? #{i+1}", ["Yes", "No", "Not sure"],
                          index=None, key=f"add_doc_{i}")

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Back", use_container_width=True):
            go_to(1)
    with col2:
        if st.button("Continue", type="primary", use_container_width=True):
            date_iso, date_precision_value = None, "unknown"
            if precision == "I know the exact date." and event_date:
                date_iso, date_precision_value = event_date.isoformat(), "exact"
            elif precision == "I know the approximate date." and event_date:
                date_iso, date_precision_value = str(event_date), "approximate"

            case_service.update_fields(
                case_id, user_id, event_types=event_types, primary_event_date=date_iso,
                primary_event_date_precision=date_precision_value,
                primary_event_city=city or None, primary_event_county=county or None,
                primary_event_state=state or None, primary_event_narrative=narrative or None,
            )

            if profile.primary_event_narrative or date_iso:
                timeline_service.add_event(
                    case_id, user_id, title="Earliest known event",
                    event_type=", ".join(event_types) if event_types else "unspecified",
                    event_date=date_iso, date_precision=date_precision_value,
                    source_type="user_stated", description=narrative or "",
                )

            st.success("Your first timeline point is in place. FORGE has saved the beginning of "
                       "your story. Later, you can connect documents and other records to confirm or add detail.")
            go_to(3)


def step_3():
    render_progress()
    st.write("This helps FORGE show the right organizational tools. You can change an answer later "
             "if you receive new paperwork.")

    related = st.radio(
        "Is there a related criminal or administrative matter?",
        ["No.", "Yes, and it is still pending.", "Yes, and it has ended.", "I am not sure."],
        index=None, key="related_proceeding_radio",
    )

    related_outcome = None
    if related == "Yes, and it has ended.":
        related_outcome = st.radio(
            "Which description best matches the result?",
            ["Dismissed or not pursued", "Plea or conviction", "Another outcome",
             "I do not know", "I prefer to add the document instead"],
            index=None, key="related_outcome_radio",
        )

    st.divider()
    civil_filed = st.radio(
        "Has a civil case been filed?",
        ["Yes, I filed a civil case.", "Yes, someone else filed a civil case involving me.",
         "No, not yet.", "I am not sure."],
        index=None, key="civil_filed_radio",
    )

    case_number = None
    judge_assigned = None
    district_judge = None
    magistrate_judge = None

    if civil_filed in ("Yes, I filed a civil case.", "Yes, someone else filed a civil case involving me."):
        case_number = st.text_input("Federal case number (if you have it)", key="case_number_input")
        judge_assigned = st.radio("Has the court assigned a judge?",
                                    ["Yes", "No", "I am not sure"], index=None, key="judge_assigned_radio")
        if judge_assigned == "Yes":
            district_judge = st.text_input("Assigned district judge", key="district_judge_input")
            magistrate_judge = st.text_input("Assigned magistrate judge, if any", key="magistrate_judge_input")
            st.file_uploader("Upload a scheduling order, standing order, or judge-issued order (optional now)",
                              type=["pdf", "docx", "jpg", "png"], key="judge_order_upload_step3")
        else:
            st.caption("That's fine - judge information is not required yet. FORGE will prompt you "
                       "again once your case shows an assignment.")

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Back", use_container_width=True, key="back3"):
            go_to(2)
    with col2:
        if st.button("Continue", type="primary", use_container_width=True, key="continue3"):
            related_map = {"No.": "none", "Yes, and it is still pending.": "pending", "I am not sure.": "unsure"}
            if related == "Yes, and it has ended.":
                outcome_map = {
                    "Dismissed or not pursued": "dismissed", "Plea or conviction": "conviction_or_plea",
                    "Another outcome": "other", "I do not know": "ended_unknown",
                    "I prefer to add the document instead": "ended_unknown",
                }
                related_value = outcome_map.get(related_outcome, "ended_unknown")
            else:
                related_value = related_map.get(related, None)

            civil_filed_map = {
                "Yes, I filed a civil case.": "filed_by_me",
                "Yes, someone else filed a civil case involving me.": "filed_against_me",
                "No, not yet.": "not_yet", "I am not sure.": "unsure",
            }

            judge_practices_status = "not_applicable_yet"
            if civil_filed in ("Yes, I filed a civil case.", "Yes, someone else filed a civil case involving me."):
                if judge_assigned == "Yes":
                    judge_practices_status = "verified" if district_judge else "pending_order_upload"
                else:
                    judge_practices_status = "pending_assignment"

            case_service.update_fields(
                case_id, user_id, related_proceeding_status=related_value,
                civil_case_filed=civil_filed_map.get(civil_filed), federal_case_number=case_number or None,
                judge_assigned=(judge_assigned == "Yes") if judge_assigned else None,
                assigned_district_judge=district_judge or None, assigned_magistrate_judge=magistrate_judge or None,
                judge_practices_status=judge_practices_status,
            )
            st.success("Your case position is mapped. FORGE will now tailor the next workspace "
                       "to the stage you selected. Judge-specific procedures can be added later.")
            go_to(4)


def step_4():
    render_progress()
    st.write("You do not need to upload everything. Choose the document that best explains "
             "where your matter stands today.")

    category = st.radio(
        "Which document would help FORGE understand your matter first?",
        DOCUMENT_CATEGORY_OPTIONS, index=None, key="doc_category_radio",
    )

    uploaded_file = None
    if category and category != "I do not have a document ready":
        st.caption(DOCUMENT_CATEGORY_TO_GUIDANCE.get(category, ""))
        uploaded_file = st.file_uploader(
            "Upload your document", type=["pdf", "docx", "jpg", "jpeg", "png"], key="first_document_uploader",
        )
        st.caption(
            "FORGE will preserve the original file, identify pages and text where possible, "
            "and show you every proposed fact before it becomes part of your organized record."
        )
    elif category == "I do not have a document ready":
        st.info("That is okay. Your case foundation has been saved. When you find a document, "
                "return here and add it to strengthen your record.")

    if uploaded_file is not None and st.button("Process this document", type="primary"):
        from services.document_pipeline import run_pipeline
        file_bytes = uploaded_file.getvalue()
        result = run_pipeline(uploaded_file.name, uploaded_file.type, file_bytes)

        if result["status"] == "rejected":
            st.error(result["reason"])
        else:
            vault = case_service.get_vault(case_id)
            doc = document_service.register_upload(
                case_id, vault.id, user_id, uploaded_file.name, uploaded_file.type,
                result["sha256"], len(file_bytes), document_category=category,
            )
            document_service.set_processing_status(
                doc.id, user_id, "needs_review", ocr_confidence=result["ocr_confidence"],
                page_count=result["page_count"], extracted_text=result["extracted_text"],
            )
            for cf in result["candidate_facts"]:
                fact_service.propose(
                    case_id, normalized_statement=cf["normalized_statement"], fact_type=cf["fact_type"],
                    confidence=cf["confidence"], source_document_id=doc.id,
                    source_page=cf["source_page"], source_quote=cf["source_quote"],
                )
            document_service.run_completeness_check(doc.id, user_id)
            case_service.update_fields(case_id, user_id, first_document_category=category)
            st.session_state.last_uploaded_doc_id = doc.id
            st.success(f"Uploaded and queued for review: {uploaded_file.name}")
            st.rerun()

    docs = document_service.for_case(case_id)
    if docs:
        st.divider()
        st.markdown("### Document Completeness Check")
        st.caption(
            "FORGE treats every uploaded document as a starting point for verification, "
            "never as an automatically accurate or complete record."
        )
        for doc in docs:
            flags = document_service.get_flags(doc.id)
            with st.container(border=True):
                st.markdown(f"{doc.original_filename} - status: {doc.completeness_status}")
                if not flags:
                    st.success("No completeness issues detected. You may still confirm below after your own review.")
                for flag in flags:
                    icon = {"red": "[!]", "amber": "[?]", "info": "[i]"}[flag.severity]
                    st.markdown(f"{icon} {flag.check_name} - {flag.detail}  \n"
                                 f"Status: {flag.resolution_status}")
                    if flag.resolution_status == "unresolved":
                        c1, c2 = st.columns(2)
                        with c1:
                            if st.button("Mark resolved", key=f"resolve_{flag.id}"):
                                document_service.resolve_flag(doc.id, flag.id, user_id, "resolved",
                                                                "User indicated this was fixed or was a false flag.")
                                st.rerun()
                        with c2:
                            if st.button("Acknowledge and continue", key=f"ack_{flag.id}"):
                                document_service.resolve_flag(doc.id, flag.id, user_id, "acknowledged",
                                                                "User reviewed and chose to proceed as-is.")
                                st.rerun()

                remaining = [f for f in flags if f.resolution_status == "unresolved"]
                if not remaining and doc.completeness_status != "user_confirmed_complete":
                    st.warning(SECOND_LOOK_WARNING)
                    confirmed = st.checkbox(
                        "I have reviewed the full original document, not just this summary, and confirm "
                        "it is accurate and complete to the best of my knowledge.",
                        key=f"confirm_complete_{doc.id}",
                    )
                    if st.button("Confirm document as reviewed", key=f"confirm_btn_{doc.id}", disabled=not confirmed):
                        document_service.confirm_completeness(doc.id, user_id, True)
                        st.rerun()
                elif doc.completeness_status == "user_confirmed_complete":
                    st.success("You have confirmed this document as reviewed and complete.")

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Back", use_container_width=True, key="back4"):
            go_to(3)
    with col2:
        if st.button("Continue", type="primary", use_container_width=True, key="continue4"):
            if category:
                case_service.update_fields(case_id, user_id, first_document_category=category)
            st.success("Your record is beginning. FORGE will organize the document without "
                       "replacing your review. You remain in control of what is confirmed.")
            go_to(5)


def step_5():
    render_progress()

    docs = document_service.for_case(case_id)
    facts = fact_service.for_case(case_id)

    new_contradictions = fact_service.scan_contradictions(case_id)
    contradiction_service.store(new_contradictions, user_id)
    stale_facts = fact_service.scan_decay(case_id)
    unresolved_contradictions = contradiction_service.unresolved_for_case(case_id)

    st.markdown("## Your Forge Path")

    with st.container(border=True):
        st.markdown(f"Court Workspace: {profile.federal_court}")
        st.markdown(f"State Source Library: {profile.state_source_jurisdiction or 'Not yet confirmed'}")
        st.markdown(f"Starting Event: "
                     f"{profile.primary_event_date or 'Date not yet provided'} "
                     f"({profile.primary_event_date_precision}) - "
                     f"{', '.join(profile.event_types) if profile.event_types else 'Type not yet specified'}")
        st.markdown(f"Current Position: {profile.filing_status or 'Not yet specified'}")
        st.markdown(f"Record Status: {len(docs)} document(s) uploaded, "
                     f"{len(facts)} proposed fact(s) awaiting your review")

        next_step = "Upload your first document"
        if any(d.completeness_status == "flagged_incomplete" for d in docs):
            next_step = "Resolve outstanding completeness flags on your uploaded document(s)"
        elif unresolved_contradictions:
            next_step = f"Review {len(unresolved_contradictions)} contradiction(s) flagged across your facts"
        elif stale_facts:
            next_step = f"Re-verify {len(stale_facts)} fact(s) that have not been checked in over 60 days"
        elif docs and any(fc.status == "proposed" for fc in facts):
            next_step = "Review the proposed facts from your uploaded document"
        elif profile.civil_case_filed in ("filed_by_me", "filed_against_me") and not profile.federal_case_number:
            next_step = "Add your federal case number when you locate it"
        elif profile.primary_event_date_precision == "unknown":
            next_step = "Confirm the earliest event date when you are able"
        st.markdown(f"Next Foundation Step: {next_step}")

    confirmed = st.checkbox("I have reviewed this summary. It reflects what I know today.",
                             key="final_review_checkbox")

    st.divider()
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Edit My Answers", use_container_width=True):
            go_to(1)
    with col2:
        if st.button("Save and Finish Later", use_container_width=True):
            case_service.mark_intake_complete(case_id, user_id, confirmed=False)
            st.info("Saved. You can return anytime - your progress is preserved.")
    with col3:
        if st.button("Save and Enter My Case Workspace", type="primary", use_container_width=True,
                      disabled=not confirmed):
            case_service.mark_intake_complete(case_id, user_id, confirmed=True)
            st.session_state.just_completed_intake = True
            go_to(6)

    if unresolved_contradictions:
        st.divider()
        st.markdown("### Contradictions detected across your facts")
        st.caption(
            "FORGE never resolves a contradiction automatically. Review each one and tell FORGE "
            "how you want to proceed."
        )
        for flag in unresolved_contradictions:
            severity_icon = {"high": "[!]", "medium": "[?]", "low": "[i]"}[flag.severity]
            with st.container(border=True):
                st.markdown(f"{severity_icon} {flag.contradiction_type.replace('_', ' ').title()} "
                             f"({flag.severity} severity)  \n{flag.detail}")
                note = st.text_input("Add a note explaining how you resolved or are treating this",
                                       key=f"contra_note_{flag.id}")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Mark resolved", key=f"contra_resolve_{flag.id}"):
                        contradiction_service.resolve(flag.id, user_id, "resolved", note)
                        st.rerun()
                with c2:
                    if st.button("Acknowledge both facts as correct", key=f"contra_ack_{flag.id}"):
                        contradiction_service.resolve(flag.id, user_id, "acknowledged", note)
                        st.rerun()

    if stale_facts:
        st.divider()
        st.markdown("### Facts due for re-verification")
        st.caption(
            "These facts have not been checked in over 60 days. Case law, rules, and even "
            "your own case posture can change - please confirm they are still accurate."
        )
        for fc in stale_facts:
            with st.container(border=True):
                st.markdown(f"{fc.normalized_statement}  \nLast verified: {fc.last_verified_at[:10]}")
                if st.button("I have re-checked this - still accurate", key=f"reverify_{fc.id}"):
                    fact_service.reverify(fc.id, user_id)
                    st.rerun()

    if facts:
        st.divider()
        st.markdown("### Proposed facts awaiting your review")
        st.caption("Nothing below is treated as confirmed until you act on it. Strength reflects "
                    "how many independent sources support each fact - not its legal significance.")
        for fc in facts:
            tier_icon = {"strong": "[+]", "moderate": "[~]", "weak": "[-]"}[fc.strength_tier]
            with st.container(border=True):
                st.markdown(f"{tier_icon} {fc.normalized_statement}  \n"
                             f"{STRENGTH_LABELS[fc.strength_tier]} - status: {fc.status}")
                for src in fc.sources:
                    st.caption(f"Source quote: {src.source_quote} (page {src.source_page}), "
                                f"confidence {src.confidence:.0%}")
                c1, c2, c3 = st.columns(3)
                with c1:
                    if st.button("Confirm", key=f"confirm_{fc.id}"):
                        fact_service.review(fc.id, user_id, "confirmed")
                        st.rerun()
                with c2:
                    if st.button("Reject", key=f"reject_{fc.id}"):
                        fact_service.review(fc.id, user_id, "rejected")
                        st.rerun()
                with c3:
                    correction = st.text_input("Correction", key=f"correction_{fc.id}",
                                                 label_visibility="collapsed",
                                                 placeholder="Type a correction, then click Save")
                    if st.button("Save correction", key=f"save_correction_{fc.id}"):
                        fact_service.review(fc.id, user_id, "corrected", correction=correction)
                        st.rerun()


def render_workspace():
    """Post-intake Case Workspace. Renders the Case Timeline and the FRCP
    Rule 6 Deadline Table (OUTPUT_FORMATS from the FORGE master prompt).
    Never estimates a missing trigger date or service method -- surfaces
    the MissingVariableError question instead."""
    if st.session_state.pop("just_completed_intake", False):
        st.balloons()
        st.success("Your path is forged, not finished. You have created a starting "
                   "record for your matter. As you add documents and confirm facts, FORGE will "
                   "help you build a clearer, source-linked case file.")

    st.markdown("## Your Case Workspace")
    st.caption("Educated. Organized. Never Alone.")

    events = timeline_service.for_case(case_id)

    st.markdown("### Case Timeline")
    if not events:
        st.info("No timeline events yet. Add one from Step 2, or add a deadline-triggering "
                 "event directly below.")
    else:
        for ev in events:
            with st.container(border=True):
                st.markdown(f"{ev.event_date or 'UNKNOWN DATE'} - {ev.title} ({ev.event_type})")
                st.caption(f"Source: {ev.source_type} - {ev.description or 'No description provided.'}")

    st.divider()
    st.markdown("### Deadlines")
    st.caption(
        "FORGE computes deadlines mechanically from FRCP Rule 6. It will never estimate "
        "a missing date or service method -- it will ask you for it instead, per the "
        "Proactive Clarification rule in FORGE's master prompt."
    )

    exact_events = [ev for ev in events if ev.date_precision == "exact" and ev.event_date]
    event_date_lookup = {}
    for ev in exact_events:
        try:
            parsed = datetime.date.fromisoformat(ev.event_date)
        except (ValueError, TypeError):
            continue
        label = f"{ev.event_date} - {ev.title}"
        event_date_lookup[label] = parsed

    with st.form("add_deadline_form"):
        trigger_label = st.selectbox(
            "What triggering event do you want to calculate a deadline for?",
            list(KNOWN_TRIGGERS.keys()), key="deadline_trigger_select",
        )

        prefill_choice = "Enter the date manually"
        if event_date_lookup:
            prefill_choice = st.selectbox(
                "Use a date already in your timeline, or enter one manually",
                ["Enter the date manually"] + list(event_date_lookup.keys()),
                key="deadline_prefill_select",
            )

        if prefill_choice != "Enter the date manually" and prefill_choice in event_date_lookup:
            trigger_date_input = event_date_lookup[prefill_choice]
            st.caption(f"Using date from your timeline: {trigger_date_input.isoformat()}")
        else:
            trigger_date_input = st.date_input(
                "Date of this triggering event", value=None, max_value=datetime.date.today(),
                key="deadline_trigger_date",
            )

        service_method = st.selectbox(
            "How was this served (if applicable)?",
            ["not_applicable", "personal", "mail", "electronic"], key="deadline_service_method",
        )

        with st.expander("Local Rule or Judge's Practice modifier (optional)"):
            st.caption(
                "Per FORGE's Rule Hierarchy, a Local Rule or a Judge's standing order can "
                "modify the standard FRCP deadline. FORGE will only apply a modifier if you "
                "paste its exact text below -- it will never infer or assume one."
            )
            local_rule_text = st.text_area(
                "Paste the exact Local Rule text that modifies this deadline, if any",
                key="deadline_local_rule_text",
            )
            judge_practice_text = st.text_area(
                "Paste the exact Judge's Practice / standing order text that modifies this "
                "deadline, if any",
                key="deadline_judge_practice_text",
            )

        submitted = st.form_submit_button("Calculate deadline")

    if submitted:
        preset = KNOWN_TRIGGERS[trigger_label]
        try:
            comp = deadline_service.compute(
                case_id, user_id, trigger_event=trigger_label, trigger_date=trigger_date_input,
                rule_cited=preset["rule_cited"], period_days=preset["period_days"],
                service_method=None if service_method == "not_applicable" else service_method,
                local_rule_text=local_rule_text or None,
                judge_practice_text=judge_practice_text or None,
            )
            st.success(f"Deadline computed: {comp.resulting_deadline.isoformat()}")
            if local_rule_text or judge_practice_text:
                st.warning(
                    "A Local Rule or Judge's Practice modifier was recorded with this "
                    "computation. FORGE quotes it verbatim in the computation steps below "
                    "but does not independently verify it matches your court's actual order."
                )
        except MissingVariableError as e:
            st.error(e.question)

    deadlines = deadline_service.for_case(case_id)
    if deadlines:
        st.markdown("#### Deadline Table")
        st.table([d.as_table_row() for d in deadlines])

        for d in deadlines:
            with st.expander(f"Rule text relied on - {d.rule_cited}"):
                preset = KNOWN_TRIGGERS.get(next(
                    (k for k, v in KNOWN_TRIGGERS.items() if v["rule_cited"] == d.rule_cited), ""
                ), {})
                for key in preset.get("citation_keys", ["6(a)(1)"]):
                    st.write(deadline_service.cite(key))
                if d.added_days_rule_6d:
                    st.write(deadline_service.cite("6(d)"))
                if d.local_rule_modifier:
                    st.write(f"Local Rule modifier (as pasted): \"{d.local_rule_modifier}\"")
                if d.judge_practice_modifier:
                    st.write(f"Judge's Practice modifier (as pasted): \"{d.judge_practice_modifier}\"")
    else:
        st.caption("No deadlines calculated yet.")

    st.divider()
    if st.button("Back to Review", use_container_width=True, key="workspace_back"):
        go_to(5)


render_hero()

STEP_FUNCS = {1: step_1, 2: step_2, 3: step_3, 4: step_4, 5: step_5}
if st.session_state.forge_step == 6:
    render_workspace()
else:
    STEP_FUNCS[st.session_state.forge_step]()

with st.sidebar:
    st.markdown("### Your Forge Path")
    is_workspace = st.session_state.forge_step == 6
    render_stepper(
        STEP_LABELS,
        current_step=st.session_state.forge_step,
        extra_step_label="Case Workspace",
        extra_step_active=is_workspace,
    )
    st.divider()
    st.caption(f"Case ID: {case_id[:8]}...")
    st.caption("All actions are recorded in an audit log for your protection.")
