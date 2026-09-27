# The Solution

`docs/00-project/problem.md` describes why "can we sign this?" is hard to answer well today: six
functions, no shared system of record, and a decision that lives in scattered emails, spreadsheets,
and memory. This document walks through how JuriSense Gate answers that question instead, mapped step
by step to the pipeline in `docs/00-project/overview.md`, and what concretely changes for each of the
six teams once it is in place.

```
Supplier
    ↓
Company verification (official sources)
    ↓
Documents / Contract ingestion
    ↓
AI structured extraction
    ↓
Company policies (Policy Engine)
    ↓
Compliance Engine
    ↓
Risk analysis
    ↓
APPROVE / REVIEW / BLOCK
    ↓
Human approval (when required)
    ↓
Decision Passport
    ↓
Audit Trail
    ↓
Blockchain verification (evidence anchoring)
```

## Step by step

### 1. Supplier

Instead of a vendor relationship starting as an email thread or a line item on a purchase order, it
starts as a `Supplier` record (`docs/03-domain/domain-model.md`) owned by the organization — one
canonical place that represents "this legal entity, as far as we're concerned." Anyone in Procurement,
Legal, Compliance, or elsewhere who is about to engage a vendor checks here first, which immediately
kills the most common failure mode from `problem.md`: two teams independently re-discovering and
re-evaluating the same vendor under inconsistent scrutiny, or a vendor relationship starting entirely
outside any review process because a support lead onboarded a tool directly.

### 2. Company verification (official sources)

Registering a `Supplier` triggers a `SupplierCheck` (SUP-002) against configured official and public
sources — starting with Brazilian registry status and sanctions/restriction lists (CEIS, CNEP, CEPIM)
— producing a normalized `SupplierProfile`. This is the check that, in the manual process, depended on
someone remembering to look it up and pasting a screenshot into a thread. Here it runs automatically,
every time, and a positive sanctions hit is not a note in a chat — it is a first-class blocking
condition (`BR-SUP-004`, rule `SANC-001`) that the workflow cannot silently pass over.

### 3. Documents / Contract ingestion

The contract (PDF/DOCX/TXT) is uploaded once, into the system that will also hold its review and
decision history, instead of being emailed between five people as an attachment with no shared version
of record. Every uploaded revision becomes a new, immutable `ContractVersion` (`BR-CON-002`) — so
"which version did Legal actually review" is never an ambiguous question again.

### 4. AI structured extraction

This is where JuriSense replaces "someone read the contract, hopefully closely" with a consistent,
repeatable read of every contract, every time. AI extraction produces structured data — parties,
value, duration, renewal/termination terms, liability caps, confidentiality, IP, data-processing/DPA
presence, jurisdiction, guarantees, penalties, obligations, deadlines — with each extracted `Clause`
citing the exact page/span it came from (`CON-004`, `docs/05-ai/structured-extraction.md`). This is
the direct fix for the liability-clause failure mode in `problem.md`: liability terms are no longer
found only if a rushed reviewer happens to scroll to section 14 — they are extracted as a structured,
always-checked field on every contract, unconditionally, before any human review even starts.

### 5. Company policies (Policy Engine)

The company's own standing rules — "DPA required whenever personal data is processed," "unlimited
liability requires Legal review," "contracts above R$250,000 require Legal approval," "sanctions hit
blocks outright" (`docs/03-domain/policy-engine.md`) — are encoded once, as versioned, executable
`Rule`s, instead of living in someone's head or an onboarding slide deck nobody re-reads. This is the
direct fix for the DPA failure mode in `problem.md`: whether a vendor "processes personal data" stops
being a judgment call an intake form-filler has to remember to make correctly — it becomes a field the
AI extraction populates and the Policy Engine checks unconditionally, on every single contract,
whether or not a human thought to ask the question.

### 6. Compliance Engine

The Compliance Engine evaluates every applicable `Rule` in the current `PolicyVersion` against the
normalized supplier + contract evidence for a `ComplianceReview` (`CMP-001`), producing one
`RuleEvaluation` per rule, each carrying its own evidence and rationale. This is the step that finally
gives one system visibility across what used to be six independently-run, uncoordinated checks: the
sanctions check, the DPA check, the liability check, and the value-threshold check are no longer five
separate people's separate jobs — they are rules evaluated together, against the same evidence, in the
same run.

### 7. Risk analysis

Individual findings (including ones that don't map cleanly to a single blocking rule) are surfaced as
named `Risk` records, giving reviewers a legible, prioritized view of what's actually concerning about
this specific supplier/contract pair — not a black-box score, but a named, evidenced list a Legal or
Compliance reviewer can act on directly.

### 8. APPROVE / REVIEW / BLOCK

The individual `RuleEvaluation`s aggregate into one final status using the algorithm in `ADR-010`:
any `BLOCK` wins, else any `REVIEW` wins, else `APPROVE`. This is the single sentence that replaces the
entire ad hoc "did everyone who needed to weigh in actually weigh in" coordination problem from
`problem.md` — the aggregation is deterministic and order-independent, so there is no scenario where a
missed check silently lets a bad contract through simply because nobody happened to raise it.

### 9. Human approval (when required)

A `REVIEW` outcome routes automatically to the correct `approver_role` via the configured
`ApprovalWorkflow` (APR-001) — Legal, Compliance, Finance, Security, Privacy, or a director, depending
on which rule fired and at what severity. This is the direct fix for the "Legal reviewed it under
deadline pressure without knowing Compliance never saw it" failure mode: the system, not an
overworked human's memory, is responsible for knowing who needs to sign off, and a human can only
resolve the request if their role actually matches what's required (`BR-APR-001`).

### 10. Decision Passport

Every completed review produces a `Decision`, packaged with everything needed to answer "why was this
approved?" months or years later: the exact `PolicyVersion` evaluated, every `RuleEvaluation` and its
evidence, the `SupplierCheck`s consulted, the AI extraction that ran (model and prompt version), and
the human approvers involved (`docs/03-domain/evidence.md`). This is the direct fix for the "nobody
can reconstruct why a vendor was approved eight months later" failure mode in `problem.md` — the
answer is no longer "someone probably looked at it," it is a reproducible record.

### 11. Audit Trail

Every meaningful action — from supplier registration to policy publication to an approval decision to
an override — emits an append-only `AuditEvent` (`docs/03-domain/audit.md`) that nobody, including an
Admin, can edit or delete (`BR-EVD-003`). Institutional memory loss (the departed reviewer, the
rolled-off Slack retention window) stops being a single point of failure for the company's ability to
answer questions about its own past decisions.

### 12. Blockchain verification (evidence anchoring)

The `EvidencePackage` backing each `Decision` is hashed (a deterministically recomputable Merkle
root, `BR-EVD-001`) and that hash — never raw contract or personal data (`BR-EVD-002`) — is anchored
via a provider-agnostic `AnchoringProvider` (`ADR-007`). This adds something an internal database log
alone cannot offer: a third party (an auditor, a regulator, a counterparty, an acquirer's due-diligence
team) can independently verify that the evidence behind a decision has not been altered after the
fact, without having to simply trust the vendor operating the internal database.

## What changes for each team

### Procurement

**Before:** originates vendor relationships with no visibility into whether Legal, Compliance, or
Security ever actually reviewed them; tracks status in a spreadsheet that goes stale the moment
someone forgets to update it.
**After:** registers a `Supplier` once and gets a real-time, single source of truth on where every
vendor stands (prospect/under review/approved/blocked), with automatic routing to whoever needs to
review next — no more chasing five people over email to find out if a deal is actually clear to sign.

### Legal

**Before:** reviews contracts under deadline pressure, often without knowing whether Compliance,
Security, or Privacy have weighed in, and manually hunts for liability/IP/termination terms buried in
long documents.
**After:** receives contracts pre-extracted into structured, citable terms (liability, IP, termination,
DPA presence) and is routed only the contracts a rule actually flagged for Legal review — spending
review time on judgment calls instead of on finding the clauses in the first place.

### Compliance

**Before:** finds out about new vendors inconsistently, runs sanctions checks manually per vendor, and
has no systematic way to confirm every vendor was actually checked before signature.
**After:** every supplier is checked automatically against sanctions/restriction sources on
registration and on an ongoing basis, policy is authored once as executable rules instead of
tribal knowledge, and Compliance can query, at any time, exactly which vendors were evaluated against
which policy version.

### Finance

**Before:** typically sees a vendor only when an invoice or PO appears, disconnected from whatever
contract review happened (if any) earlier.
**After:** value-threshold rules (`FIN-003`, `FIN-004`) trigger automatically the moment contract value
is extracted, routing high-value contracts to the right approval chain before commitment, not after
the invoice arrives.

### Security

**Before:** security review is the check most likely to be skipped entirely under deadline pressure,
because it's the slowest and most specialized to perform manually for every vendor.
**After:** vendor and contract data relevant to security posture is captured as structured evidence
alongside everything else, and security-relevant policy rules (e.g., data-access scope, sub-processor
exposure) are evaluated automatically as part of the same review — instead of depending on someone
explicitly scheduling a separate security review that may never happen.

### Privacy

**Before:** depends on someone correctly recognizing "this vendor processes personal data" at intake —
an easy classification step to skip, with no systematic way to confirm it was made correctly.
**After:** the DPA-required rule (`LGPD-001`) fires unconditionally whenever the AI extraction flags
personal-data processing without a corresponding DPA — turning a rule anyone could plausibly forget
into a check the system can never forget to make.

## Before / after, in one story

**Before:** a support-tooling vendor is picked by a team lead, onboarded via a purchase order Finance
processes without context, contracted on the vendor's standard terms that nobody reads past the
pricing page, and never reviewed by Legal, Compliance, or Security — because no single person or
system was ever responsible for making sure it was. A year later, a customer's own security
questionnaire asks whether this vendor has a signed DPA, and the honest answer is "we don't think so,
let us check" — followed by a scramble to retroactively produce documentation that should have existed
from day one, with no record of what, if anything, was actually reviewed before onboarding.

**After:** the same vendor is registered as a `Supplier`, its contract is ingested and extracted, the
extraction flags personal-data processing with no DPA present, `LGPD-001` fires `BLOCK` automatically,
and the vendor cannot progress to `approved` until a valid DPA is in place and Privacy has signed off —
all recorded, from the first check to the final `Decision`, in one reproducible package any customer
can hand to their own auditor with confidence, months or years after the fact.
