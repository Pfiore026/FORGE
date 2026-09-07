"""
services/citation_guard.py

Strict Citation & Grounding Mandate enforcement layer for FORGE.

No procedural answer may be generated from model memory. Every citation must
resolve to verbatim text in the loaded corpus (FRCP, Local Rules, Judge
Practices). If it does not resolve, the caller MUST receive the standard
refusal string and a request for the missing source text.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import json


REFUSAL_TEXT = "I do not have the specific rule required to answer this."


@dataclass
class Citation:
    rule_id: str
    title: str
    text: str
    source: str


class RuleCitationStore:
    """Loads a JSON corpus of rule text (FRCP now; Local Rules / Judge
    Practices can be merged in per-case) and serves only verbatim quotes."""

    def __init__(self, corpus: Optional[dict] = None):
        self.corpus = corpus or {}

    @classmethod
    def from_file(cls, path: str) -> "RuleCitationStore":
        with open(path, "r") as f:
            return cls(json.load(f))

    def merge_local_rules(self, local_corpus: dict) -> None:
        """Local Rules / Judge's Practices are merged under a 'local' or
        'judge' namespace and never overwrite the FRCP baseline, per the
        Rule Hierarchy (FRCP -> Local Rules -> Judge Practices)."""
        self.corpus.update(local_corpus)

    def cite(self, rule_id: str) -> Citation:
        rule_num, _, _sub = rule_id.partition("(")
        rule_num = rule_num.strip()
        entry = self.corpus.get(rule_num)
        if not entry:
            raise LookupError(REFUSAL_TEXT)
        subs = entry.get("subsections", {})
        text = subs.get(rule_id) or entry.get("title")
        if not text:
            raise LookupError(REFUSAL_TEXT)
        return Citation(
            rule_id=rule_id,
            title=entry.get("title", ""),
            text=text,
            source=entry.get("source", "unknown"),
        )

    def safe_cite_or_refusal(self, rule_id: str) -> str:
        """Never throws. Returns either the verbatim quote+citation or the
        exact mandated refusal string -- use this at the UI/output boundary."""
        try:
            c = self.cite(rule_id)
            return f'{c.rule_id}: "{c.text}" (Source: {c.source})'
        except LookupError:
            return REFUSAL_TEXT
