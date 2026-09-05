"""
FORGE State Source Registry -- curated, human-verified links only.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Optional

US_STATES = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA",
    "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE", "Florida": "FL", "Georgia": "GA",
    "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA",
    "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
    "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH",
    "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY", "North Carolina": "NC",
    "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA",
    "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD", "Tennessee": "TN",
    "Texas": "TX", "Utah": "UT", "Vermont": "VT", "Virginia": "VA", "Washington": "WA",
    "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY", "District of Columbia": "DC",
}


@dataclass
class StateSources:
    state_name: str
    statutes_title: Optional[str]
    statutes_url: Optional[str]
    civil_rules_title: Optional[str]
    civil_rules_url: Optional[str]
    court_home_url: Optional[str]
    source_status: str
    last_verified: Optional[str] = None


STATE_SOURCE_REGISTRY: Dict[str, StateSources] = {
    "ME": StateSources(
        state_name="Maine", statutes_title="Maine Revised Statutes",
        statutes_url="https://legislature.maine.gov/statutes/",
        civil_rules_title="Maine Rules of Civil Procedure",
        civil_rules_url="https://www.courts.maine.gov/rules/rules-civil.html",
        court_home_url="https://www.courts.maine.gov/",
        source_status="verified", last_verified="2026-08-25",
    ),
}

FEDERAL_SOURCES = {
    "med": {
        "label": "United States District Court for the District of Maine",
        "frcp_title": "Federal Rules of Civil Procedure",
        "frcp_url": "https://www.law.cornell.edu/rules/frcp",
        "local_rules_title": "District of Maine Local Rules",
        "local_rules_url": "https://www.med.uscourts.gov/local-rules",
        "court_home_url": "https://www.med.uscourts.gov/",
        "source_status": "verified", "last_verified": "2026-08-25",
    }
}


def get_state_sources(state_name: str) -> Optional[StateSources]:
    code = US_STATES.get(state_name)
    if not code:
        return None
    return STATE_SOURCE_REGISTRY.get(code)
