"""Neutral deposition-preparation topic service for the FORGE Discovery Workspace.

Organizes source-cited people, documents, and events into preparation topics
that a user can review outside FORGE. This module never suggests examination
strategy, never assesses witness credibility, and never tells a user how to
use a fact against a party. It exists to keep written-discovery answers and
deposition preparation connected to the same underlying Fact Bank records.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

STATUS_FLOW = ["identified", "source_reviewed", "preparation_notes_added", "closed"]


@dataclass
class DepositionTopic:
    case_id: str
    label: str
    source_fact_ids: list[str]
    id: str = field(default_factory=lambda: f"deptopic_{uuid4().hex[:10]}")
    related_interrogatory_topic_ids: list[str] = field(default_factory=list)
    status: str = "identified"
    user_notes: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class DepositionTopicService:
    def __init__(self, audit_service=None):
        self.audit = audit_service
        self._topics: dict[str, DepositionTopic] = {}

    def _log(self, event_type: str, case_id: str, user_id: str, detail: str = "") -> None:
        if self.audit is None:
            return
        try:
            self.audit.log(event_type=event_type, case_id=case_id, user_id=user_id, detail=detail)
        except (AttributeError, TypeError):
            pass

    def add_topic(self, case_id: str, user_id: str, label: str, source_fact_ids: list[str]) -> DepositionTopic:
        if not label or not label.strip():
            raise ValueError("A deposition topic needs a short label describing the person or record.")
        topic = DepositionTopic(case_id=case_id, label=label.strip(), source_fact_ids=list(source_fact_ids))
        self._topics[topic.id] = topic
        self._log("deposition_topic_added", case_id, user_id, label)
        return topic

    def for_case(self, case_id: str) -> list[DepositionTopic]:
        return sorted(
            (t for t in self._topics.values() if t.case_id == case_id),
            key=lambda t: t.created_at,
        )

    def get(self, topic_id: str) -> DepositionTopic:
        return self._topics[topic_id]

    def advance_status(self, topic_id: str, user_id: str) -> DepositionTopic:
        topic = self._topics[topic_id]
        idx = STATUS_FLOW.index(topic.status)
        if idx + 1 < len(STATUS_FLOW):
            topic.status = STATUS_FLOW[idx + 1]
        self._log("deposition_topic_status_advanced", topic.case_id, user_id, topic.status)
        return topic

    def link_interrogatory_topic(self, topic_id: str, interrogatory_topic_id: str) -> None:
        topic = self._topics[topic_id]
        if interrogatory_topic_id not in topic.related_interrogatory_topic_ids:
            topic.related_interrogatory_topic_ids.append(interrogatory_topic_id)

    def set_notes(self, topic_id: str, notes: str) -> None:
        self._topics[topic_id].user_notes = notes


def neutral_deposition_prompt(person_or_record: str) -> str:
    return (
        f"{person_or_record} appears in a source-cited case record. This item is available "
        "as a deposition-preparation topic for your organizational notes."
    )
