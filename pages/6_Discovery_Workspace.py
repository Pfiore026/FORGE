"""FORGE - Discovery Workspace: Interrogatories & Depositions.

A Streamlit multipage module. Files under pages/ are automatically added to
the app's sidebar navigation, so this integrates into the live FORGE product
without modifying app.py or risking the existing Forge Path / Case Workspace.

This page reuses the same session-state services app.py already initializes
(AuditService, CaseService, FactCardService) so Fact Cards created during the
Forge Path and Case Workspace are visible here too. It adds two new services,
InterrogatoryService and DepositionTopicService, following the same
propose/review lifecycle and MissingVariableError clarification pattern used
elsewhere in FORGE.

FORGE organizes and educates. It does not draft interrogatory language,
evaluate legal strength, recommend what to serve, or predict outcomes.
"""
import streamlit as st

from services.case_service import AuditService, CaseService, FactCardService
from services.interrogatory_service import (
    CATEGORY_OPTIONS, InterrogatoryService, MissingDiscoveryVariableError,
)
from services.deposition_service import DepositionTopicService
from services.discovery_rules import get_rule, rule_status, all_verified_keys

st.set_page_config(page_title="FORGE - Discovery Workspace", page_icon="scales", layout="centered")

try:
    from services.ui_theme import inject_theme, render_severity_badge, render_chip
    inject_theme()
except Exception:
    def render_severity_badge(label, severity):
        st.caption(f"[{severity.upper()}] {label}")
    def render_chip(label, value):
        st.caption(f"{label}: {value}")


def _ensure_services():
    if "audit" not in st.session_state:
        st.session_state.audit = AuditService()
    if "case_service" not in st.session_state:
        st.session_state.case_service = CaseService(st.session_state.audit)
    if "fact_service" not in st.session_state:
        st.session_state.fact_service = FactCardService(st.session_state.audit)
    if "user_id" not in st.session_state:
        st.session_state.user_id = "demo-user-0001"
    if "case_id" not in st.session_state:
        profile = st.session_state.case_service.create_case(st.session_state.user_id, "My FORGE Case")
        st.session_state.case_id = profile.id
    if "interrogatory_service" not in st.session_state:
        st.session_state.interrogatory_service = InterrogatoryService(st.session_state.audit)
    if "deposition_topic_service" not in st.session_state:
        st.session_state.deposition_topic_service = DepositionTopicService(st.session_state.audit)
    if "discovery_briefing_seen" not in st.session_state:
        st.session_state.discovery_briefing_seen = False


_ensure_services()

case_service = st.session_state.case_service
fact_service = st.session_state.fact_service
interrogatory_service = st.session_state.interrogatory_service
deposition_topic_service = st.session_state.deposition_topic_service
user_id = st.session_state.user_id
case_id = st.session_state.case_id
profile = case_service.get(case_id)

DISCOVERY_MAP = [
    ("Pleading and service", "Complaint filed, defendant served, proof of service filed or waived under FRCP 4."),
    ("Rule 26(f) conference and disclosures", "Parties confer and exchange required initial disclosures before most discovery may begin."),
    ("Discovery opens", "Interrogatories, document requests, admissions, and depositions become available, subject to any scheduling order."),
    ("Written discovery", "Interrogatories (FRCP 33) and document requests (FRCP 34) organize written answers and records."),
    ("Requests for admission", "Requests for admission (FRCP 36) organize discrete, narrow factual or legal propositions."),
    ("Depositions", "Depositions (FRCP 30) organize oral testimony, often after written discovery narrows the topics."),
    ("Motion practice", "Dispositive motions may test whether the case can proceed to trial on the developed record."),
    ("Pretrial and trial", "Remaining issues are prepared for trial using the organized fact and document record."),
]

BRIEFING_SECTIONS = [
    ("What interrogatories are",
     [
         "Interrogatories are written questions served on another party in a lawsuit.",
         "Federal Rule of Civil Procedure 33 governs them; answers must be in writing, separately, and under oath, unless objected to.",
         "They may only be directed to a party -- not an ordinary nonparty witness.",
         "Unless the court orders otherwise or the parties stipulate otherwise, Rule 33 limits a party to 25 interrogatories, including discrete subparts.",
     ]),
    ("When they are used",
     [
         "Interrogatories are a discovery tool. In most federal civil cases, discovery cannot begin until the Rule 26(f) conference, unless an exception, stipulation, or court order allows earlier discovery.",
         "The operative scheduling order, local rules, and any assigned judge's practices may set deadlines or requirements controlling when requests may be served and answered.",
         "Confirm that discovery is open and check your scheduling order before treating any draft as final.",
     ]),
    ("What they can help organize",
     [
         "Names and roles of people involved in events described in your case.",
         "Dates, locations, communications, documents, policies, and procedures identified in filings or evidence.",
         "The opposing party's stated factual basis for a denial, defense, or other position.",
         "The identity and location of records, electronic information, and people with relevant knowledge.",
     ]),
    ("Why focused questions matter",
     [
         "A clear, discrete question is easier to track and easier to compare against later evidence.",
         "Broad, compound, or vague questions can draw objections, produce incomplete answers, or complicate the discrete-subpart count.",
         "This workspace helps you break a broad topic into organized factual items and link each to its source -- it does not decide what you should ask.",
     ]),
    ("Important limits",
     [
         "Interrogatories are one discovery method among several; a written answer does not replace producing documents or testimony.",
         "FRCP 33(d) allows a party to answer by specifying business records in some circumstances, subject to its own requirements.",
         "A response is not a substitute for independently reviewing documents, preserving evidence, or tracking the court's deadlines.",
     ]),
    ("Not legal advice",
     [
         "FORGE provides educational and organizational information, not legal advice.",
         "FORGE does not tell you whether to bring a claim, assert a defense, serve a request, file a motion, or take any other legal action.",
         "You remain responsible for verifying rules, deadlines, court orders, and every document before use.",
     ]),
]


def render_discovery_briefing():
    st.markdown("## Discovery Learning Center")
    st.caption(
        "Educated. Organized. Never Alone. This refresher is always available here -- "
        "you do not need to complete it in one sitting."
    )
    for title, bullets in BRIEFING_SECTIONS:
        with st.expander(title, expanded=not st.session_state.discovery_briefing_seen):
            for b in bullets:
                st.markdown(f"- {b}")
    st.session_state.discovery_briefing_seen = True

    st.markdown("### How discovery tools connect")
    for stage, detail in DISCOVERY_MAP:
        with st.container(border=True):
            st.markdown(f"**{stage}**")
            st.caption(detail)


def render_interrogatory_deposition_bridge():
    st.markdown("### How Interrogatories and Depositions work together")
    st.caption(
        "Written answers can point you toward people, documents, and events worth preparing "
        "for a deposition. Neither tool tells you what to ask or how to use an answer."
    )
    bridge_rows = [
        ("A person or custodian is identified", "Available as a deposition-preparation topic."),
        ("A document or record system is identified", "Available as a document-tracking topic."),
        ("A date or event sequence is supplied", "Available to add to your case timeline."),
        ("An objection or incomplete answer is recorded", "Verify applicable rules and any meet-and-confer requirement before acting."),
        ("Two sources describe an item differently", "Both are preserved; review the original sources yourself."),
    ]
    for left, right in bridge_rows:
        st.markdown(f"- **{left}** -> {right}")


def render_verified_rule_library():
    st.markdown("### Verified Rule Library")
    st.caption(
        "FORGE only quotes rule text it has fetched and verified, with a source link "
        "and verification date. Anything not listed here has not been verified yet."
    )
    for key in all_verified_keys():
        st.caption(get_rule(key))
        st.divider()


def render_interrogatory_planner():
    st.markdown("### Interrogatory Planner")
    st.caption(get_rule("FRCP 33(a)(1)"))
    st.caption(get_rule("FRCP 26(d)(1)"))
    with st.expander("Related: document requests and admissions (for cross-linking, not drafting)"):
        st.caption(get_rule("FRCP 34(b)(2)(A)"))
        st.caption(get_rule("FRCP 36(a)(3)"))

    facts = [fc for fc in fact_service.for_case(case_id) if getattr(fc, "status", None) == "confirmed"]
    if not facts:
        st.info(
            "No confirmed Fact Cards yet. Confirm facts in your Case Workspace so you can "
            "link interrogatory topics to a source record."
        )

    fact_labels = {fc.id: fc.normalized_statement for fc in facts}

    with st.form("new_interrogatory_topic"):
        target_party = st.text_input("Target party (must be a party to the case)")
        category = st.selectbox("Information category", CATEGORY_OPTIONS)
        factual_topic = st.text_area("Factual topic in plain language")
        linked_fact_ids = st.multiselect(
            "Link to confirmed fact(s)", options=list(fact_labels.keys()),
            format_func=lambda fid: fact_labels.get(fid, fid),
        )
        subparts = st.number_input("Discrete subpart count", min_value=1, max_value=25, value=1)
        submitted = st.form_submit_button("Add topic to planner")

    if submitted:
        try:
            interrogatory_service.propose_topic(
                case_id, user_id, target_party=target_party, category=category,
                factual_topic=factual_topic, source_fact_ids=linked_fact_ids,
                discrete_subpart_count=int(subparts),
            )
            st.success("Topic added. It stays linked to the fact(s) you selected.")
            st.rerun()
        except MissingDiscoveryVariableError as e:
            st.error(e.question)

    topics = interrogatory_service.for_case(case_id)
    if topics:
        st.divider()
        for target in interrogatory_service.targets_for_case(case_id):
            count = interrogatory_service.subpart_count(case_id, target)
            severity = "high" if count > 25 else ("medium" if count >= 20 else "low")
            render_severity_badge(f"{count} / 25 discrete subparts (unless stipulated or ordered otherwise)", severity)
            st.caption(f"Target party: {target}")
            for t in interrogatory_service.for_target(case_id, target):
                with st.container(border=True):
                    st.markdown(f"**{t.factual_topic}**")
                    st.caption(f"Category: {t.category} | Status: {t.status} | Subparts: {t.discrete_subpart_count}")
                    for fid in t.source_fact_ids:
                        st.caption(f"Source fact: {fact_labels.get(fid, fid)}")
                    notes = st.text_input("Notes", value=t.user_notes, key=f"notes_{t.id}")
                    if notes != t.user_notes:
                        interrogatory_service.set_notes(t.id, notes)
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("Advance status", key=f"advance_{t.id}"):
                            interrogatory_service.advance_status(t.id, user_id)
                            st.rerun()
                    with c2:
                        dep_options = {d.id: d.label for d in deposition_topic_service.for_case(case_id)}
                        if dep_options:
                            chosen = st.selectbox(
                                "Link deposition topic", options=list(dep_options.keys()),
                                format_func=lambda did: dep_options.get(did, did), key=f"link_{t.id}",
                            )
                            if st.button("Link", key=f"link_btn_{t.id}"):
                                interrogatory_service.link_deposition_topic(t.id, chosen)
                                deposition_topic_service.link_interrogatory_topic(chosen, t.id)
                                st.rerun()


def render_deposition_panel():
    st.markdown("### Deposition Preparation Topics")
    st.caption(get_rule("FRCP 30(d)(1)"))
    st.caption(get_rule("FRCP 30(a)(2)(A)(i)"))

    facts = [fc for fc in fact_service.for_case(case_id) if getattr(fc, "status", None) == "confirmed"]
    fact_labels = {fc.id: fc.normalized_statement for fc in facts}

    with st.form("new_deposition_topic"):
        label = st.text_input("Person, role, or record this topic concerns")
        linked_fact_ids = st.multiselect(
            "Link to confirmed fact(s)", options=list(fact_labels.keys()),
            format_func=lambda fid: fact_labels.get(fid, fid), key="dep_fact_link",
        )
        submitted = st.form_submit_button("Add deposition topic")

    if submitted:
        try:
            deposition_topic_service.add_topic(case_id, user_id, label=label, source_fact_ids=linked_fact_ids)
            st.success("Deposition topic added.")
            st.rerun()
        except ValueError as e:
            st.error(str(e))

    topics = deposition_topic_service.for_case(case_id)
    for t in topics:
        with st.container(border=True):
            st.markdown(f"**{t.label}**")
            st.caption(f"Status: {t.status}")
            for fid in t.source_fact_ids:
                st.caption(f"Source fact: {fact_labels.get(fid, fid)}")
            if st.button("Advance status", key=f"dep_advance_{t.id}"):
                deposition_topic_service.advance_status(t.id, user_id)
                st.rerun()


def render_preflight_checklist():
    st.markdown("### Preflight Checklist Before Finalizing Outside FORGE")
    st.caption(
        "FORGE does not finalize or serve discovery requests. This checklist reflects what "
        "you should verify yourself before treating any planner topic as ready."
    )
    court_verified = getattr(profile, "federal_court_confirmed", False)
    checks = {
        "Court and case verified": bool(court_verified),
        "Discovery status confirmed (Rule 26(f) conference held, if required)": st.checkbox(
            "I have confirmed discovery is open in my case", key="pf_discovery_open"),
        "Local rules and scheduling order reviewed": st.checkbox(
            "I have reviewed the current District of Maine Local Rules and my scheduling order",
            key="pf_local_rules"),
        "Target confirmed as a party": st.checkbox(
            "Every planner topic above targets an actual party to the case", key="pf_target_party"),
        "Discrete subpart count reviewed": st.checkbox(
            "I have reviewed my discrete-subpart count against the 25-interrogatory limit",
            key="pf_subpart_count"),
        "Acknowledgment": st.checkbox(
            "I understand FORGE provides education and organization, not legal advice",
            key="pf_ack"),
    }
    missing = [k for k, v in checks.items() if not v]
    if missing:
        st.warning("Still open: " + "; ".join(missing))
    else:
        st.success(
            "All preflight items are checked. Review your planner topics with counsel or "
            "the applicable court rules before taking any topic outside FORGE."
        )


st.markdown("# Discovery Workspace")
st.caption("Interrogatories & Depositions -- part of FORGE's Case Workspace.")

tab_learn, tab_int, tab_dep, tab_preflight = st.tabs(
    ["Learn / Refresher", "Interrogatory Planner", "Deposition Topics", "Preflight Checklist"]
)

with tab_learn:
    render_discovery_briefing()
    st.divider()
    render_interrogatory_deposition_bridge()
    st.divider()
    render_verified_rule_library()

with tab_int:
    render_interrogatory_planner()

with tab_dep:
    render_deposition_panel()

with tab_preflight:
    render_preflight_checklist()

with st.sidebar:
    st.divider()
    st.caption(f"Case ID: {case_id[:8]}...")
    st.caption("FORGE organizes and educates. It is not legal advice.")
