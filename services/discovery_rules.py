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
    "FRCP 30(a)(2)(A)(i)": RuleEntry(
        citation="FRCP 30(a)(2)(A)(i) - Leave for more than 10 depositions per side",
        verified_text=(
            "A party must obtain leave of court, and the court must grant leave to the "
            "extent consistent with Rule 26(b)(1) and (2): if the parties have not "
            "stipulated to the deposition and: (i) the deposition would result in more "
            "than 10 depositions being taken under this rule or Rule 31 by the "
            "plaintiffs, or by the defendants, or by the third-party defendants."
        ),
        source_url="https://www.law.cornell.edu/rules/frcp/rule_30",
        verified_on="2026-09-07",
        status="verified_excerpt",
    ),
    "FRCP 30(d)(1)": RuleEntry(
        citation="FRCP 30(d)(1) - Duration",
        verified_text=(
            "Unless otherwise stipulated or ordered by the court, a deposition is "
            "limited to 1 day of 7 hours. The court must allow additional time "
            "consistent with Rule 26(b)(1) and (2) if needed to fairly examine the "
            "deponent or if the deponent, another person, or any other circumstance "
            "impedes or delays the examination."
        ),
        source_url="https://www.law.cornell.edu/rules/frcp/rule_30",
        verified_on="2026-09-07",
        status="verified_excerpt",
    ),
    "FRCP 34(b)(2)(A)": RuleEntry(
        citation="FRCP 34(b)(2)(A) - Time to Respond",
        verified_text=(
            "The party to whom the request is directed must respond in writing within "
            "30 days after being served or -- if the request was delivered under Rule "
            "26(d)(2) -- within 30 days after the parties' first Rule 26(f) conference. "
            "A shorter or longer time may be stipulated to under Rule 29 or be ordered "
            "by the court."
        ),
        source_url="https://www.law.cornell.edu/rules/frcp/rule_34",
        verified_on="2026-09-07",
        status="verified_excerpt",
    ),
    "FRCP 36(a)(3)": RuleEntry(
        citation="FRCP 36(a)(3) - Time to Respond; Effect of Not Responding",
        verified_text=(
            "A matter is admitted unless, within 30 days after being served, the party "
            "to whom the request is directed serves on the requesting party a written "
            "answer or objection addressed to the matter and signed by the party or its "
            "attorney. A shorter or longer time for responding may be stipulated to "
            "under Rule 29 or be ordered by the court."
        ),
        source_url="https://www.law.cornell.edu/rules/frcp/rule_36",
        verified_on="2026-09-07",
        status="verified_excerpt",
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


def all_verified_keys() -> list[str]:
    return [key for key, entry in RULE_LIBRARY.items() if entry.status == "verified_excerpt"]
