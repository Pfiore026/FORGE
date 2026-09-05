# FORGE -- Reference Build
## Phase 0 Intake + Phase 2 Document Intelligence + Phase 2A Safeguards + Sections 24.1/24.2

This build closes the workflow gaps identified against the FORGE product spec.

| Engine | File | Spec reference |
|---|---|---|
| Forge Path intake (5 steps) | app.py | Phase 0 |
| Document ingestion pipeline | services/document_pipeline.py | Phase 2 |
| Document Completeness Check + Discrepancy Prompt gate | services/completeness.py | Phase 2A |
| Multi-Source Corroboration (Strong/Moderate/Weak tiers) | services/corroboration.py | Section 24.1 |
| Confidence Decay & Scheduled Re-Verification (60-day window) | services/corroboration.py | Section 24.2 |
| Contradiction Detection (date/amount mismatch, severity-rated) | services/contradiction.py | Phase 2 |
| Curated state/federal source registry | services/state_registry.py | Phase 1 |
| Audit logging | services/case_service.py (AuditService) | Section 24.3 |

## What changed in this pass

Previously the build proposed Fact Cards from a single source and displayed them for
confirm/reject/correct, but did not run the Mandatory Completeness Check, enforce
Multi-Source Corroboration, track Confidence Decay, or run Contradiction Detection
across facts. All four are now wired end-to-end into Step 4 (Gather Your Record) and
Step 5 (Review Your Path), with dedicated UI panels, and are covered by an executable
test suite before delivery.

## What this protects

1. Do not overbuild before the first complete path works -- only PDF, DOCX, JPG, PNG
   supported; candidate-fact extraction is deliberately conservative until real OCR is
   wired into extract_text_stub in document_pipeline.py.
2. Keep the user's burden low -- every intake question accepts "I am not sure"; judge
   information is never required before a case is filed and assigned.
3. Make uncertainty visible -- every fact carries a strength_tier, every document a
   completeness_status, every contradiction a severity rating. Nothing is silently
   resolved by the system.

## Structure

```
app.py                          Streamlit entry point -- 5-step Forge Path wizard with
                                 completeness gate, corroboration display, decay warnings,
                                 and contradiction review panels
services/models.py               CaseProfile, CaseDocument, FactCard, FactSource,
                                 ContradictionFlag, TimelineEvent, AuditEntry
services/case_service.py         CaseService, DocumentService, FactCardService,
                                 ContradictionService, TimelineService
services/document_pipeline.py    Upload validation, hashing, extraction seam, fact proposer
services/completeness.py         Phase 2A: 7-check completeness scan + Discrepancy Prompt gate
services/corroboration.py        Section 24.1/24.2: strength-tier computation + decay scan
services/contradiction.py        Pairwise date/amount contradiction detection
services/state_registry.py       Curated, human-verified state and federal source links
database/schema.sql              Postgres/Supabase schema with RLS policies
requirements.txt                 Python dependencies
.env.example                     Configuration template
```

## Running locally

```
cd forge_app
pip install -r requirements.txt
streamlit run app.py
```

## Moving to production

1. Replace in-memory services with real Supabase calls -- method signatures are stable.
2. Apply database/schema.sql including completeness_flags, fact_card_sources, and
   contradiction_flags tables with their RLS policies.
3. Wire real OCR/text extraction into extract_text_stub in document_pipeline.py.
4. Replace the demo user_id with real authenticated identity (mandatory 2FA).
5. Add server-side encryption at rest and per-case storage isolation.
6. Expand state_registry.py state-by-state, verified only after human review.
7. Add a UI affordance for add_corroborating_source so users can explicitly link a
   second document to an existing Fact Card.

## Explicit non-goals for this build

- No statute-of-limitations calculation.
- No judge-specific procedural automation (data stored, not yet applied to deadlines).
- No claim-viability scoring, case-law research engine, or legal-strategy output.
- No automatic contradiction resolution -- always surfaced for human review.
- No damages module, adversarial review engine, or stage-briefing library yet.
