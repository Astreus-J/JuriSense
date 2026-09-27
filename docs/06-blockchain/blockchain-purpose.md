# Why Blockchain — Purpose and Scope

> Related: `docs/00-project/overview.md` ("Why blockchain makes sense here" / "Why blockchain is NOT
> the product"), `ADR-007`, `docs/06-blockchain/evidence-model.md`, `docs/06-blockchain/privacy.md`,
> `docs/03-domain/business-rules.md` (`BR-EVD-001`, `BR-EVD-002`).

## The one-sentence version

JuriSense Gate anchors a hash of each Decision's Evidence Package on a public, tamper-evident
ledger so that anyone who does **not** trust JuriSense's own database — an auditor, a regulator, an
acquirer's due-diligence team, or a counterparty in a dispute — can independently check whether that
evidence was altered after the decision was made, without JuriSense being in the loop at
verification time.

That is the entire purpose. Nothing else about the product depends on blockchain: no token, no
NFT, no DAO, no cryptocurrency, and no document or personal data ever goes on-chain (see
"Why blockchain is NOT the product" in `docs/00-project/overview.md` and the privacy boundary in
`docs/06-blockchain/privacy.md`).

## The problem this solves: auditability that survives time and organizational memory loss

JuriSense Gate's core commercial promise is captured in one recurring scenario across
`docs/02-business/business-case.md`: eighteen months, three years, or five years after a supplier
was approved, someone — a new compliance officer, an external auditor, a regulator investigating a
data breach, or an acquirer's legal team during M&A due diligence — asks:

> "Why did we approve this vendor's unlimited-liability clause? Prove it was actually reviewed, on
> the date you say, against the policy that was in force at the time."

By that point, the people who made the decision may have left the company, the Slack thread is
gone, the spreadsheet was overwritten, and "someone probably looked at it" is the only honest
answer most companies can give today (see the Problem section of
`docs/00-project/overview.md`). JuriSense Gate's Decision Passport (see `docs/03-domain/evidence.md`
and the `Decision` / `EvidencePackage` entities in `docs/03-domain/domain-model.md`) is built to make
that question answerable at any point in the future, not just immediately after the decision.
Answering it requires more than storing the answer — it requires proving the stored answer has not
been quietly edited since.

## What an internal audit log can and cannot prove

JuriSense already maintains an append-only `AuditEvent` log (`BR-EVD-003`,
`docs/03-domain/domain-model.md`) and immutable-by-construction records (`Decision`,
`ComplianceReview`, `RuleEvaluation`, `EvidencePackage` are all documented as immutable once
created, per their Invariants). This internal design is genuinely useful:

- It stops ordinary application bugs or careless UI actions from silently mutating a decision.
- It gives JuriSense's own team, and a customer's own admins, a reliable operational record.
- It satisfies most day-to-day "show me what happened" requests.

But an internal database — no matter how well designed — has one structural limitation: **every
guarantee it offers is a guarantee about JuriSense's own systems, verified using JuriSense's own
tools, on JuriSense's own infrastructure.** An external party evaluating that guarantee has to trust:

1. that JuriSense's application code actually enforces "immutable" and "append-only" as designed
   (no bypass, no forgotten admin backdoor, no bug);
2. that no one with database-level access (a JuriSense engineer, a compromised credential, a
   subpoenaed insider, a future acquirer of JuriSense itself) altered a row and its timestamp
   directly, below the application layer; and
3. that JuriSense's own account of "when we checked, the log was intact" is itself trustworthy —
   which is precisely the thing in question when the audit stakes are highest (a regulatory
   investigation, a lawsuit, a due-diligence dispute).

None of this makes the internal log dishonest or poorly engineered. It makes it **privately
verifiable** rather than **publicly verifiable**: the only entity that can check it is the entity
whose behavior is being checked. For most software products that is an acceptable limitation. For a
*compliance* product — whose entire pitch is "trust our record of why this was approved" — asking
the skeptical party to also trust the record-keeper is circular, and the parties who most need to
ask "prove it" (auditors, regulators, opposing counsel, an acquirer's diligence team) are, by
construction, the parties least willing to accept "trust us" as the proof.

## Why this gap matters specifically for a compliance product

A generic SaaS product's audit log answers "what did our system do?" — useful mostly to the
product's own operator. JuriSense Gate's audit trail is asked to answer a materially harder
question on behalf of *someone else*: "can a party outside JuriSense, who has no operational access
to JuriSense's infrastructure, independently confirm this evidence is exactly what it was on the day
of the decision?" That is the question an auditor signs off on, a regulator bases a finding on, or
an acquirer prices into a deal. If the only available answer is "our internal log says so," the
compliance value proposition collapses back into the same "someone probably looked at it" status quo
JuriSense Gate exists to replace (see the Problem section of `docs/00-project/overview.md`).

Anchoring a hash of the Evidence Package on a public, tamper-evident ledger changes what is being
asked of the skeptical party. Instead of "trust JuriSense's claim that this record wasn't altered,"
the claim becomes: "recompute this hash yourself from the evidence you were given (or that JuriSense
still holds), compare it to the hash that a public, JuriSense-independent network recorded as
existing at a specific point in time, and reach your own conclusion." The verifying party runs
`AnchoringProvider.verify(evidence_hash, proof)` (see `docs/06-blockchain/anchoring-providers.md`
and `docs/06-blockchain/verification.md`) against a network that keeps running, and keeps its
history, regardless of what JuriSense's own database says, whether JuriSense's servers are up, or
even whether JuriSense still exists as a company.

## What blockchain proves, and — precisely — what it does not

This is a trust-*minimization* argument, not a trust-*elimination* argument, and it is important to
be precise about the boundary:

- **What it proves**: that a specific hash value existed, unaltered, as of a specific point in time
  attested to by a decentralized network JuriSense does not control. If the underlying Evidence
  Package is later produced and its recomputed Merkle root (`BR-EVD-001`,
  `docs/06-blockchain/evidence-model.md`) does not match the anchored hash, tampering after the
  anchor date is provable — by anyone, using only public information and the AnchoringProvider's
  `verify()` method, with no need to trust JuriSense's database.
- **What it does not prove**: that the evidence was true, complete, or fairly evaluated at the
  moment it was hashed. Blockchain anchoring timestamps a snapshot; it says nothing about whether
  the AI extraction was accurate, whether the policy rule was well-designed, or whether a human
  approver acted in good faith. Those are the jobs of the Compliance Engine, the Policy Engine, and
  the Approval workflow (see `docs/03-domain/policy-engine.md`, `docs/03-domain/approvals.md`), not
  of the Trust Layer. The Trust Layer's job starts exactly where those jobs end: once a Decision and
  its Evidence Package exist, prevent — and make provably detectable — any change to that record
  after the fact, by anyone, including JuriSense itself.

## Relationship to the rest of the Evidence & Audit context

Blockchain anchoring is additive to, not a replacement for, the internal audit trail:

- The `AuditEvent` log, `Decision`, `ComplianceReview`, and `RuleEvaluation` immutability
  (`docs/03-domain/domain-model.md`) remain the operational source of truth for day-to-day product
  use — evidence retrieval, dashboards, internal review, and export all read from them directly.
- The `BlockchainAnchor` (one per `EvidencePackage`, per `ADR-007` and the domain model) exists
  purely to give an *external* party a way to check that operational source of truth was not altered
  after the anchor was submitted, without needing privileged access to it.
- `BR-EVD-001` — "an `EvidencePackage`'s `merkle_root` must be deterministically recomputable from
  its `Evidence` set at any time" — is what makes this check mechanically possible: anyone holding
  (or being given, e.g. via a Decision Passport export) the original Evidence set can recompute the
  same root JuriSense computed, and compare it to what is anchored on-chain, independent of anything
  JuriSense currently says about it.

See `docs/06-blockchain/evidence-model.md` for exactly how that hash is built, and
`docs/06-blockchain/verification.md` for the concrete verification flow an external party follows.
