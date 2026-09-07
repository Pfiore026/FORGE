# FORGE Discovery Workspace

## Purpose

The Discovery Workspace is FORGE's evidence-first organization and procedural-education layer for federal civil discovery. It is available after initial filing so users can learn how the civil case stages connect, collect source records, and prepare organized discovery topics before discovery is open. It does not provide legal advice, predict outcomes, determine what a user should serve, or assess legal strength.

## Evidence Intelligence Standard

1. The immutable original upload is the source record.
2. Every original is stored with a SHA-256 hash, source classification, upload timestamp, version identifier, and immutable storage-object identifier.
3. Native PDF text is preferred when available. Image-only or unusable pages are routed to high-quality rendered-page OCR.
4. OCR, classifications, extracted fields, summaries, timelines, and workspace records are derived records; they are never substituted for the original.
5. Every material extracted value requires a document ID, document-version ID, page number, normalized bounding box, verbatim source text, extraction method, confidence values, and review state.
6. Conflicting records are preserved and displayed together. FORGE must not choose a controlling value without user review.
7. Low-confidence, handwritten, incomplete, unsupported, or high-risk values enter a review queue.

## Authority hierarchy

FORGE must present procedural sources in this sequence:

1. Federal Rules of Civil Procedure.
2. Current District of Maine Local Rules.
3. Assigned judge's practices and case-management orders.
4. Operative scheduling order and docket-specific directives.

No deadline calculation, discovery-availability statement, or finalization pathway may treat a rule as current unless the source version, effective date, source URL, and verification date are attached.

## Discovery learning map

The permanent, user-accessible refresher explains: pleading and service; Rule 26 conference and disclosures; discovery timing; interrogatories; document requests; requests for admission; depositions; discovery responses; motion practice; pretrial preparation; and trial. The system shows each tool's mechanics and connections but does not recommend substantive legal choices.

## Interrogatories and depositions

Interrogatories organize written party responses around source-cited factual topics. Depositions organize people, events, and records into source-cited preparation topics. A response identifying a person, date, policy, document, event, or communication may be linked to the Fact Bank, evidence timeline, document-reference record, and a neutral deposition topic.

The tool may state: "This response identifies a person with information. It is available for your witness and deposition-preparation records." It may not state that the user should ask a question, serve a request, use information against a party, or rely on any record as proof.

## Preflight controls

Before a user marks an interrogatory set finalized, FORGE requires the following recorded confirmations:

- Court and case verified
- Federal rule source attached
- Local rule source attached
- Scheduling order source attached
- Judge-practices source attached when applicable
- Discovery status confirmed
- Target confirmed as a party
- Interrogatory count and discrete-subpart count reviewed
- Every topic linked to source records
- User acknowledges that FORGE provides education and organization, not legal advice

## Implementation status

The `discovery` package contains the initial domain layer: immutable document records, citations, extraction fields, fact assertions, rule sources, review tasks, neutral interrogatory/deposition topics, inspection routing, validation, conflict detection, and a source graph. Provider-specific OCR calls and user-interface components should be implemented as adapters around this layer.
