# FORGE Discovery Workspace -- Interrogatories & Depositions

## Integration approach

This workspace ships as a Streamlit multipage module (`pages/6_Discovery_Workspace.py`)
rather than as edits to `app.py`. Streamlit automatically adds files under `pages/`
to the sidebar navigation, so this integrates into the live product without risking
the existing Forge Path intake or Case Workspace. It reuses the same session-state
services `app.py` already creates (`AuditService`, `CaseService`, `FactCardService`),
so Fact Cards confirmed during the Forge Path and Case Workspace are visible here.

## New services

- `services/discovery_rules.py` -- a strict-citation rule library. FORGE only quotes
  rule text that has been fetched and verified, with its source URL and verification
  date. If a rule has not been verified, FORGE says so instead of guessing. Two
  entries currently carry verified excerpts (FRCP 33(a)(1) and FRCP 26(d)(1)); the
  rest are marked `not_yet_verified` pending a source fetch.
- `services/interrogatory_service.py` -- `InterrogatoryService` organizes source-cited
  factual topics for written interrogatories. It raises `MissingDiscoveryVariableError`
  (mirroring `deadline_engine.MissingVariableError`) instead of guessing a missing
  target party, factual topic, or source link.
- `services/deposition_service.py` -- `DepositionTopicService` organizes source-cited
  people, documents, and events into deposition-preparation topics, and links back to
  interrogatory topics.

## What the workspace does

- Learn / Refresher tab: a persistent, always-available briefing on what interrogatories
  are, when they are used, what they can help organize, why focused questions matter,
  their limits, and the not-legal-advice boundary. It also shows how every discovery
  stage and tool connects (pleading, Rule 26(f), written discovery, admissions,
  depositions, motion practice, trial).
- Interrogatory Planner: lets the user link a plain-language factual topic to one or
  more confirmed Fact Cards, tracks the discrete-subpart count per target party against
  the Rule 33(a)(1) default 25-item limit, and lets the user link a topic to a
  deposition-preparation topic.
- Deposition Topics: lets the user create a preparation topic tied to confirmed Fact
  Cards and link it back to an interrogatory topic.
- Preflight Checklist: a non-binding checklist (discovery-open confirmation, local-rule
  and scheduling-order review, target-party confirmation, subpart-count review, and a
  not-legal-advice acknowledgment) that the user must work through before treating any
  planner topic as ready to take outside FORGE.

## What the workspace intentionally does not do

- It never drafts interrogatory or deposition question language.
- It never evaluates legal strength, claim viability, or witness credibility.
- It never tells the user what to serve, when to serve it, or how to use an answer.
- It never treats an extracted or confirmed fact as legal proof.
- It never finalizes or transmits a discovery request; "finalized_outside_forge" is a
  status label only.

## Known follow-up work

- `InterrogatoryService` and `DepositionTopicService` currently store topics in memory
  per Streamlit session. They should be migrated to the same persistence layer as
  `services/db.py` so topics survive across sessions like Fact Cards and documents do.
- Most entries in `services/discovery_rules.py` are placeholders pending a verified
  fetch of the exact rule text (FRCP 30(d)(1), 34, 36, and the District of Maine Local
  Rules). Do not present these as reliable until verified text is loaded.
- The `discovery/` package added in an earlier commit on this branch used an
  incompatible parallel data model (`DocumentRecord`, `FactAssertion`, etc.) and is
  superseded by this integration, which instead extends `FactCardService`,
  `DocumentService`, and the existing audit/citation patterns. See
  `docs/DEPRECATED_discovery_package.md`.
