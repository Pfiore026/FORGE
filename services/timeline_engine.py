"""
services/timeline_engine.py

Formats the REAL TimelineEvent objects produced by services.case_service
(TimelineService) into the Case Timeline structure required by the FORGE
master prompt's OUTPUT_FORMATS -- a Markdown table or JSON array with
columns: Date | Event Title | Event Type | Source (Doc / Docket) |
Contribution to Case.

IMPORTANT: This module does NOT define its own TimelineEvent. An earlier
version of this file defined a separate, incompatible dataclass
(event_title/source/contribution/date as a real date object) that was never
imported by app.py and silently diverged from the actual data model in
services/models.py (event_date as an ISO string, title, source_type,
description, no "contribution" field at all). That divergence has been
removed. This module now operates exclusively on the real TimelineEvent
objects returned by TimelineService.for_case(), duck-typed on the fields
that model actually has.

"Contribution to Case" is derived mechanically, never invented:
  - If the event's title/type matches a known deadline-triggering event
    (see services.deadline_service.KNOWN_TRIGGERS), the contribution states
    the procedural consequence in neutral terms (e.g. "Triggers a deadline
    under FRCP 12(a)(1)(A)(i)").
  - Otherwise, the contribution falls back to the user's own description,
    or "No procedural contribution identified yet" if none was provided.
This module never characterizes the strength, credibility, or legal
significance of an event -- that would violate the ABSOLUTE_UPL_BOUNDARIES
in the FORGE master prompt.
"""
from __future__ import annotations
from typing import List, Optional
import json

try:
    from .deadline_service import KNOWN_TRIGGERS
except ImportError:
    KNOWN_TRIGGERS = {}


def _infer_contribution(ev) -> str:
    title = (getattr(ev, "title", "") or "").strip().lower()
    event_type = (getattr(ev, "event_type", "") or "").strip().lower()
    for trigger_label, preset in KNOWN_TRIGGERS.items():
        if trigger_label.lower() in title or trigger_label.lower() in event_type:
            return f"Triggers a deadline under {preset['rule_cited']} ({preset['period_days']} days)."
    description = getattr(ev, "description", None)
    if description:
        return description
    return "No procedural contribution identified yet."


def _source_label(ev) -> str:
    source_type = getattr(ev, "source_type", None) or "unknown"
    doc_id = getattr(ev, "source_document_id", None)
    if doc_id:
        return f"{source_type} (document {doc_id[:8]}...)"
    return source_type


def event_to_row(ev) -> dict:
    """Maps a real services.models.TimelineEvent to the OUTPUT_FORMATS row
    shape. Never guesses a date: an event with no event_date, or with
    date_precision other than 'exact', is rendered with its actual value
    plus a precision flag rather than a bare 'UNKNOWN'."""
    event_date = getattr(ev, "event_date", None)
    precision = getattr(ev, "date_precision", "unknown")
    if event_date and precision == "exact":
        date_display = event_date
    elif event_date and precision == "approximate":
        date_display = f"{event_date} (approximate)"
    else:
        date_display = "UNKNOWN"

    return {
        "Date": date_display,
        "Event Title": getattr(ev, "title", "") or "UNKNOWN",
        "Event Type": getattr(ev, "event_type", "") or "UNKNOWN",
        "Source (Doc / Docket)": _source_label(ev),
        "Contribution to Case": _infer_contribution(ev),
    }


def sort_events_for_display(events: List) -> List:
    """Exact and approximate dates sort chronologically by their string
    value (ISO-prefixed strings sort correctly); UNKNOWN-dated events trail
    at the end, flagged for follow-up rather than silently dropped."""
    dated = [e for e in events if getattr(e, "event_date", None)]
    undated = [e for e in events if not getattr(e, "event_date", None)]
    dated.sort(key=lambda e: e.event_date)
    return dated + undated


def to_markdown_table(events: List) -> str:
    ordered = sort_events_for_display(events)
    header = "| Date | Event Title | Event Type | Source (Doc / Docket) | Contribution to Case |\n"
    sep =    "| --- | --- | --- | --- | --- |\n"
    rows = "".join(
        "| {Date} | {Event Title} | {Event Type} | {Source (Doc / Docket)} | {Contribution to Case} |\n".format(
            **event_to_row(e)
        )
        for e in ordered
    )
    return header + sep + rows


def to_json(events: List) -> str:
    ordered = sort_events_for_display(events)
    return json.dumps([event_to_row(e) for e in ordered], indent=2)


def unknown_date_events(events: List) -> List:
    """Surfaces exactly which events still need a clarification question,
    per CRITICAL_OVERRIDE: PROACTIVE_CLARIFICATION -- callers should prompt
    the user for these dates rather than leaving them silently unresolved."""
    return [e for e in events if not getattr(e, "event_date", None)]
