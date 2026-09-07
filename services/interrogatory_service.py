"""Neutral interrogatory-planning service for the FORGE Discovery Workspace.

Organizes source-cited factual topics for written interrogatories directed at
a party. This module never drafts question language, never assesses legal
strength or claim viability, and never tells a user what to serve or when.
It mirrors the propose/review lifecycle already used by FactCardService and
the MissingVariableError clarification pattern used by the deadline engine
elsewhere in FORGE, so the same UPL and citation guardrails apply here.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4


class MissingDiscoveryVariableError(Exception):
    """Raised instead of guessing. Carries a direct question for the user,
    matching the deadline_engine.MissingVariableError pattern in this app."""
    def __init__(self, question: str):
        self.question = question
        super().__init__(question)


STATUS_FLOW = [
    "idea", "organized", "user_reviewed", "rules_check_pending", "finalized_outside_forge",
]

CATEGORY_OPTIONS = [
    "identity_of_person", "date_or_sequence", "communication", "document_or_record_location",
    "policy_or_procedure", "damages_related_fact", "other_factual_topic",
]


@dataclass
class InterrogatoryTopic:
    case_id: str
    target_party: str
    category: str
    factual_topic: str
    source_fact_ids: list[str]
    id: str = field(default_factory=lambda: f"inttopic_{uuid4().hex[:10]}")
    discrete_subpart_count: int = 1
    status: str = "idea"
    related_deposition_topic_ids: list[str] = field(default_factory=list)
    user_notes: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class InterrogatoryService:
    """In-memory service for the initial build. Follow-up work should move
    storage to the same persistence layer used by services/db.py so topics
    survive across sessions the same way Fact Cards and documents do."""

    def __init__(self, audit_service=None):
        self.audit = audit_service
        self._topics: dict[str, InterrogatoryTopic] = {}

    def _log(self, event_type: str, case_id: str, user_id: str, detail: str = "") -> None:
        if self.audit is None:
            return
        try:
            self.audit.log(event_type=event_type, case_id=case_id, user_id=user_id, detail=detail)
        except (AttributeError, TypeError):
            pass  # Defensive: audit signature may differ; never break the workspace over logging.

    def propose_topic(self, case_id: str, user_id: str, target_party: str, category: str,
                       factual_topic: str, source_fact_ids: list[str],
                       discrete_subpart_count: int = 1) -> InterrogatoryTopic:
        if not target_party or not target_party.strip():
            raise MissingDiscoveryVariableError(
                "Which party should this interrogatory topic be directed to? Under FRCP 33, "
                "interrogatories may only be served on a party to the case, not a nonparty witness."
            )
        if not factual_topic or not factual_topic.strip():
            raise MissingDiscoveryVariableError(
                "What factual topic should this cover? Describe the specific information "
                "gap in plain language before organizing it as a topic."
            )
        if not source_fact_ids:
            raise MissingDiscoveryVariableError(
                "This topic has no linked source fact. Link it to at least one confirmed "
                "Fact Card so it stays traceable to your case record."
            )
        topic = InterrogatoryTopic(
            case_id=case_id, target_party=target_party.strip(), category=category,
            factual_topic=factual_topic.strip(), source_fact_ids=list(source_fact_ids),
            discrete_subpart_count=max(1, int(discrete_subpart_count)),
        )
        self._topics[topic.id] = topic
        self._log("interrogatory_topic_proposed", case_id, user_id, topic.factual_topic)
        return topic

    def for_case(self, case_id: str) -> list[InterrogatoryTopic]:
        return sorted(
            (t for t in self._topics.values() if t.case_id == case_id),
            key=lambda t: t.created_at,
        )

    def for_target(self, case_id: str, target_party: str) -> list[InterrogatoryTopic]:
        return [t for t in self.for_case(case_id) if t.target_party == target_party]

    def subpart_count(self, case_id: str, target_party: str) -> int:
        return sum(t.discrete_subpart_count for t in self.for_target(case_id, target_party))

    def targets_for_case(self, case_id: str) -> list[str]:
        seen: list[str] = []
        for t in self.for_case(case_id):
            if t.target_party not in seen:
                seen.append(t.target_party)
        return seen

    def get(self, topic_id: str) -> InterrogatoryTopic:
        return self._topics[topic_id]

    def advance_status(self, topic_id: str, user_id: str) -> InterrogatoryTopic:
        topic = self._topics[topic_id]
        idx = STATUS_FLOW.index(topic.status)
        if idx + 1 < len(STATUS_FLOW):
            topic.status = STATUS_FLOW[idx + 1]
        self._log("interrogatory_topic_status_advanced", topic.case_id, user_id, topic.status)
        return topic

    def set_status(self, topic_id: str, user_id: str, status: str) -> InterrogatoryTopic:
        if status not in STATUS_FLOW:
            raise ValueError(f"Unknown status: {status}")
        topic = self._topics[topic_id]
        topic.status = status
        self._log("interrogatory_topic_status_set", topic.case_id, user_id, status)
        return topic

    def link_deposition_topic(self, topic_id: str, deposition_topic_id: str) -> None:
        topic = self._topics[topic_id]
        if deposition_topic_id not in topic.related_deposition_topic_ids:
            topic.related_deposition_topic_ids.append(deposition_topic_id)

    def set_notes(self, topic_id: str, notes: str) -> None:
        self._topics[topic_id].user_notes = notes


def neutral_gap_prompt(reference_label: str, missing_detail: str) -> str:
    """A non-advisory prompt: describes a gap, never recommends serving anything."""
    return (
        f"{reference_label} references {missing_detail}. You may add this as a "
        "source-linked factual topic in your interrogatory planner."
    )
