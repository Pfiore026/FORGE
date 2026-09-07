"""
FORGE Section 24.1 -- Multi-Source Corroboration Requirement
FORGE Section 24.2 -- Confidence Decay & Scheduled Re-Verification

24.1: A single document can produce a "Moderate" Fact Card at most. A Fact
Card reaches "Strong" only once at least two independent sources corroborate it.

24.2: Every Fact Card has a decay window (default 60 days). Once elapsed since
last_verified_at, the fact is flagged needs_reverification=True.
"""
from __future__ import annotations
from datetime import datetime, timedelta
from typing import List
from .models import FactCard, FactSource

# NOTE: The canonical default decay window lives on FactCard.decay_window_days
# in services/models.py (default=60). This module previously declared its own
# DEFAULT_DECAY_WINDOW_DAYS = 60 constant that was never referenced anywhere
# -- two sources of truth for the same number that could silently drift out
# of sync if one were changed without the other. Removed; models.py is the
# single source of truth for this default.

STRENGTH_LABELS = {
    "strong": "Strong -- corroborated by 2+ independent sources",
    "moderate": "Moderate -- supported by a single source",
    "weak": "Weak -- low-confidence or unverified extraction",
}

# Maps directly to the --forge-green/--forge-amber/--forge-red CSS variables
# in services/ui_theme.py, so fact-strength badges use the same color
# language as every other severity indicator in the app (completeness flags,
# contradiction flags). Use with ui_theme.render_severity_badge().
STRENGTH_COLOR = {"strong": "green", "moderate": "amber", "weak": "red"}


def compute_strength_tier(fact: FactCard) -> str:
    if not fact.sources:
        return "weak"
    distinct_documents = {s.source_document_id for s in fact.sources if s.source_document_id}
    max_conf = fact.max_confidence
    if len(distinct_documents) >= 2 and max_conf >= 0.6:
        return "strong"
    if len(distinct_documents) >= 1 and max_conf >= 0.4:
        return "moderate"
    return "weak"


def add_source_and_recompute(fact: FactCard, source: FactSource) -> FactCard:
    fact.sources.append(source)
    fact.strength_tier = compute_strength_tier(fact)
    fact.last_verified_at = datetime.utcnow().isoformat()
    fact.needs_reverification = False
    return fact


def check_decay(fact: FactCard, now: datetime = None) -> bool:
    now = now or datetime.utcnow()
    try:
        last_verified = datetime.fromisoformat(fact.last_verified_at)
    except (ValueError, TypeError):
        fact.needs_reverification = True
        return True
    elapsed = now - last_verified
    is_stale = elapsed > timedelta(days=fact.decay_window_days)
    fact.needs_reverification = is_stale
    return is_stale


def scan_case_for_decay(facts: List[FactCard], now: datetime = None) -> List[FactCard]:
    stale = []
    for fact in facts:
        if check_decay(fact, now=now):
            stale.append(fact)
    return stale


def reverify(fact: FactCard):
    fact.last_verified_at = datetime.utcnow().isoformat()
    fact.needs_reverification = False
    return fact
