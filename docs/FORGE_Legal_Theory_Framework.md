# FORGE Legal Theory & Design Framework
_Grounding document for design philosophy only — not a source of procedural rule text._

This document explains the academic and doctrinal framework that shapes *why* FORGE is
built the way it is (mechanical, citation-strict, non-advisory). It draws on published
work and clinical program design from Cornell, Harvard, Yale, Georgetown, and CUNY
School of Law. **None of this theory is ever injected into FORGE's live procedural
outputs** — those remain governed exclusively by the Strict Citation & Grounding
Mandate (FRCP / Local Rules / Judge Practices text only). This document is a design
rationale, kept separate from the runtime rule corpus.

## 1. Cornell — Structural Source of Truth
Cornell Law School's Legal Information Institute (LII, law.cornell.edu/rules/frcp) is
FORGE's canonical text source for the Federal Rules of Civil Procedure. This project's
own configuration prioritizes Cornell LII specifically because it publishes the
restyled rule text alongside the Advisory Committee Notes that explain *why* each
computation rule works the way it does (e.g., the 2009 amendment to Rule 6(a) that
unified day-counting after courts found the old "count only business days under 11"
rule produced counterintuitive results — a 10-day period sometimes ran longer than a
14-day period). FORGE's `deadline_engine.py` encodes that exact history: it always
counts calendar days per the 2009 standard, never the pre-2009 short-period exclusion,
because that is what the current, currently-controlling rule text says.

## 2. Harvard — Access-to-Justice as Infrastructure, Not Charity
Harvard Law School's Access to Justice work (including its "Access to Justice in the
Digital World" program and CLP research on Limited License Legal Technicians) frames
the pro se crisis as a structural infrastructure gap: pro se litigants are the
majority of parties in high-volume, high-stakes civil forums (housing, family, small
claims) that get the least attorney attention. Harvard's research on LLLT programs is
instructive for FORGE's own boundary line: even licensed legal technicians in these
frameworks are authorized to "inform clients about procedures and deadlines" but are
walled off from "representation" and "negotiation." FORGE's ABSOLUTE_UPL_BOUNDARIES
mirrors that exact split — deadlines and mechanics, never strategy or advocacy.

## 3. Yale — Rigor in Procedural Doctrine
Yale's civil procedure scholarship is used here as a check on precision, not sourcing.
Where Cornell supplies the rule text, Yale-style procedural analysis is the discipline
of never treating a "specific calendar day" deadline the same as a "computed" one — a
distinction the 2009 Advisory Committee Notes make explicit and that FORGE's engine
respects: `compute_forward_deadline()` only ever operates on periods stated as "X days
after an event," never on court-ordered fixed dates, which must instead be
transcribed verbatim from the order.

## 4. Georgetown — Clinical Practice Discipline
Georgetown Law runs 17 in-house clinics (including its Civil Justice Clinic) built
around the discipline of "practical art of lawyering" performed under supervision —
every filing checked against a formal requirement before it goes out the door. FORGE's
CORE_PROTOCOLS Document Triage Protocol borrows this clinical intake discipline:
before any substantive step, extract court, document type, key dates, and — critically —
an explicit "Missing Context" field, the same gate a clinical supervisor would apply
before letting a filing proceed.

## 5. CUNY School of Law — Section 1983 / Civil Rights Procedural Terrain
CUNY's Equality & Justice In-House Clinic focuses specifically on Section 1983 civil
rights litigation — "our nation's core civil rights statute" — and trains students to
navigate the procedural barriers that exist for civil rights plaintiffs in court. This
is directly relevant to FORGE's own reference case (Fiore et al. v. Town of Oxford,
No. 2:25-cv-00611-SDN, D. Maine), which pleads Section 1983 / Monell claims. CUNY's
clinical framing — that procedural mastery is itself a tool of pressure and a platform
for civil rights plaintiffs who often cannot afford counsel — is the strongest
doctrinal justification for why a mechanical, no-fluff procedural tool has independent
value distinct from legal advice: the procedural barrier itself is often the practical
obstacle, separate from the merits.

## 6. The Common Thread: "Access, Not Indulgence"
Across all five schools, the recurring doctrine is procedural parity — pro se
litigants are entitled to the same access as represented parties, not a lower bar and
not a shortcut. Courts have repeatedly held that pro se status does not excuse missed
deadlines or defective filings. FORGE's entire design exists in that gap: it cannot
lower the bar (no legal advice, no drafting), but it can close the information gap
that separates "access" from actually being able to use it — exact citations, exact
dates, exact structural requirements, nothing more and nothing less.

## Source List
- Cornell LII, Federal Rules of Civil Procedure: https://www.law.cornell.edu/rules/frcp
- Harvard Law School, "Access to Justice in the Digital World": https://hls.harvard.edu/courses/access-to-justice-in-the-digital-world/
- Harvard Law CLP, "Who Accesses Justice?": https://clp.law.harvard.edu/article/who-accesses-justice/
- Yale Law School, Civil Procedure course catalog: https://courses.law.yale.edu/
- Georgetown Law, Clinical Programs: https://www.law.georgetown.edu/experiential-learning/clinics/
- CUNY School of Law, Equality & Justice In-House Clinic: https://www.law.cuny.edu/academics/clinical-programs/equality-justice-in-house-clinic/
