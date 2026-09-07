"""Strict-citation rule library for the FORGE Discovery Workspace.

Mirrors the citation_guard / deadline_service pattern already used elsewhere in
FORGE: FORGE never answers a procedural question from memory. It only quotes
text that has been fetched and stored here, with its source URL and the date
it was verified. If a rule has not been loaded and verified, FORGE says so
rather than guessing or paraphrasing from training data.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class RuleEntry:
    citation: str
    verified_text: str | None
    source_url: str
    verified_on: str | None
    status: str  # "verified_excerpt" or "not_yet_verified"


RULE_LIBRARY: dict[str, RuleEntry] = {
    "FRCP 33(a)(1)": RuleEntry(
        citation="FRCP 33(a)(1) - Number",
        verified_text=(
            "Unless otherwise stipulated or ordered by the court, a party may "
            "serve on any other party no more than 25 written interrogatories, "
            "including all discrete subparts. Leave to serve additional "
            "interrogatories may be granted to the extent consistent with Rule 26(b)(1) and (2)."
        ),
        source_url="https://www.law.cornell.edu/rules/frcp/rule_33",
        verified_on="2026-09-07",
        status="verified_excerpt",
    ),
    "FRCP 26(d)(1)": RuleEntry(
        citation="FRCP 26(d)(1) - Timing",
        verified_text=(
            "A party may not seek discovery from any source before the parties "
            "have conferred as required by Rule 26(f), except in a proceeding "
            "exempted from initial disclosure under Rule 26(a)(1)(B), or when "
            "authorized by these rules, by stipulation, or by court order."
        ),
        source_url="https://www.law.cornell.edu/rules/frcp/rule_26",
        verified_on="2026-09-07",
        status="verified_excerpt",
    ),
    "FRCP 30(d)(1)": RuleEntry(
        citation="FRCP 30(d)(1) - Duration",
        verified_text=None,
        source_url="https://www.law.cornell.edu/rules/frcp/rule_30",
        verified_on=None,
        status="not_yet_verified",
    ),
    "FRCP 34": RuleEntry(
        citation="FRCP 34 - Producing Documents",
        verified_text=None,
        source_url="https://www.law.cornell.edu/rules/frcp/rule_34",
        verified_on=None,
        status="not_yet_verified",
    ),
    "FRCP 36": RuleEntry(
        citation="FRCP 36 - Requests for Admission",
        verified_text=None,
        source_url="https://www.law.cornell.edu/rules/frcp/rule_36",
        verified_on=None,
        status="not_yet_verified",
    ),
    "D.Me. Local Rules": RuleEntry(
        citation="District of Maine Local Rules",
        verified_text=None,
        source_url="https://www.med.uscourts.gov/local-rules",
        verified_on=None,
        status="not_yet_verified",
    ),
}


def get_rule(key: str) -> str:
    """Return a verified verbatim excerpt, or an honest not-yet-verified notice.

    This never fabricates rule text. It either quotes stored, source-linked
    text or tells the user it does not have what is required.
    """
    entry = RULE_LIBRARY.get(key)
    if entry is None:
        return f"I do not have the specific rule required to answer this for \"{key}\"."
    if entry.status != "verified_excerpt" or not entry.verified_text:
        return (
            f"I do not have a verified excerpt of {entry.citation} loaded yet. "
            f"Verify the current text at {entry.source_url} before relying on it."
        )
    return f"{entry.citation}: \"{entry.verified_text}\" (verified {entry.verified_on}, source: {entry.source_url})"


def rule_status(key: str) -> str:
    entry = RULE_LIBRARY.get(key)
    return entry.status if entry else "unknown"
