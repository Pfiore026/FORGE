"""
services/timeline_engine.py

Builds the interactive Case Timeline (Chronology Extraction) and Deadline
Table structures specified in the FORGE master prompt's <OUTPUT_FORMATS>.

This module performs no legal analysis. It only structures, sorts, and
validates event data supplied by the caller (from document triage or user
input), flagging any missing required field as "UNKNOWN" rather than
guessing.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from typing import Optional, List
import json


REQUIRED_FIELDS = ["date", "event_title", "event_type", "source", "contribution"]


@dataclass
class TimelineEvent:
    event_title: str
    event_type: str
    source: str
    contribution: str
    date: Optional[date] = None
    date_confidence: str = "confirmed"  # "confirmed" | "estimated" | "unknown"

    def to_row(self) -> dict:
        return {
            "Date": self.date.isoformat() if self.date else "UNKNOWN",
            "Event Title": self.event_title,
            "Event Type": self.event_type,
            "Source (Doc / Docket)": self.source,
            "Contribution to Case": self.contribution,
        }


class TimelineBuilder:
    def __init__(self):
        self._events: List[TimelineEvent] = []

    def add_event(self, **kwargs) -> TimelineEvent:
        missing = [f for f in ("event_title", "event_type", "source", "contribution")
                   if not kwargs.get(f)]
        if missing:
            raise ValueError(
                f"Cannot add timeline event: missing required field(s) {missing}. "
                f"Per Document Triage Protocol, mark unavailable data as UNKNOWN "
                f"rather than omitting the event."
            )
        ev = TimelineEvent(**kwargs)
        self._events.append(ev)
        return ev

    def sorted_events(self) -> List[TimelineEvent]:
        dated = [e for e in self._events if e.date is not None]
        undated = [e for e in self._events if e.date is None]
        dated.sort(key=lambda e: e.date)
        return dated + undated  # UNKNOWN-dated events trail, flagged for follow-up

    def to_markdown_table(self) -> str:
        header = "| Date | Event Title | Event Type | Source (Doc / Docket) | Contribution to Case |\n"
        sep =    "| --- | --- | --- | --- | --- |\n"
        rows = "".join(
            "| {Date} | {Event Title} | {Event Type} | {Source (Doc / Docket)} | {Contribution to Case} |\n".format(**e.to_row())
            for e in self.sorted_events()
        )
        return header + sep + rows

    def to_json(self) -> str:
        return json.dumps([e.to_row() for e in self.sorted_events()], indent=2)

    def unknown_date_events(self) -> List[TimelineEvent]:
        """Surfaces exactly which events still need a clarification question,
        per CRITICAL_OVERRIDE: PROACTIVE_CLARIFICATION."""
        return [e for e in self._events if e.date is None]
