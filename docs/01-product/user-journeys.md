# User Journeys

Each journey narrates an end-to-end experience from one persona's point of view, crossing multiple
use cases (`docs/01-product/use-cases.md`) in sequence. These are illustrative, concrete scenarios —
names and numbers are representative examples, not commitments — meant to make the product's value
tangible beyond the individual use-case specifications. Persona detail: `docs/01-product/
personas.md`. Roles cited are from `ADR-003`.

---

## Journey 1: A Procurement Manager onboards a new SaaS vendor from first contact to signed contract

**Persona**: Ana, Procurement Manager (`Procurement` role) at a 300-person Brazilian fintech.

**Trigger**: The engineering team wants to adopt a new observability SaaS tool, "MonitorTech," and
has asked Ana to get it approved so they can start a paid pilot.

1. Ana registers MonitorTech as a new `Supplier` in JuriSense Gate — legal name, CNPJ (it has a
   Brazilian subsidiary), jurisdiction Brazil (UC-1). The system immediately validates the CNPJ
   format and confirms no duplicate exists in the organization.
2. Within seconds, the system automatically kicks off a `SupplierCheck` (UC-2) against Brazil's
   registry status and CEIS/CNEP/CEPIM sanctions lists. Ana doesn't have to do anything — she moves
   on to requesting the contract from MonitorTech's sales team while the check runs in the
   background.
3. The check completes clean: registered, active, no sanctions hits. `Supplier.status` advances
   toward `under_review`, on track for `approved` pending contract review.
4. MonitorTech sends over their standard SaaS subscription agreement (a PDF). Ana uploads it,
   attaching it to the MonitorTech `Supplier` record as a new `Contract` (UC-3). The system scans it
   for malware/type-spoofing, hashes it, and creates the first `ContractVersion`.
5. AI extraction (UC-4) runs automatically. Within a couple of minutes, Ana sees a structured
   summary: parties, US$18,000/year (converted and flagged for FX exposure since the contract is
   billed in USD), 12-month term with auto-renewal, standard limitation-of-liability clause capped
   at fees paid, no DPA attached despite the tool ingesting application logs that may contain user
   IPs.
6. Policy execution (UC-5) runs against her company's published policy. Two rules fire: `FIN-003`
   does not trigger (value is well under the R$250,000 threshold), but `LGPD-001` (DPA required for
   personal-data processing) triggers `BLOCK` — no DPA is present, and the extracted data flags log
   content as potentially containing personal data.
7. Ana sees the outcome immediately: **BLOCK** — WHY: "No DPA present while contract processes
   personal data (LGPD-001, critical)." EVIDENCE: the specific clause span showing log ingestion
   scope, with a citation directly into the source PDF. She doesn't need to guess what's wrong or
   escalate blind — the reason is right there.
8. Ana goes back to MonitorTech's sales team with a specific, informed ask: "We need a signed DPA
   before we can proceed — here's what our policy requires." MonitorTech's legal team sends over
   their standard DPA the next day.
9. Ana uploads the DPA as a new document; the contract's `ContractVersion` is updated with a new
   negotiation round reflecting the now-attached DPA terms (UC-3 A1), and extraction/policy
   execution re-run automatically (UC-4, UC-5).
10. This time, `LGPD-001` passes. No other rule triggers. The aggregated outcome (UC-9) is
    **APPROVE** — fully automatic, no human approval step required, because every applicable rule
    passed.
11. Ana tells engineering they're clear to sign. The whole cycle — from first registering the vendor
    to a defensible APPROVE — took two business days, almost entirely gated by MonitorTech's own
    response time, not by any internal review bottleneck.
12. Months later, when Finance asks "did we ever verify MonitorTech has a DPA in place," Ana pulls up
    the Decision Passport (UC-11) in seconds instead of searching old email threads.

---

## Journey 2: A Compliance Officer investigates why a contract was blocked and resolves it

**Persona**: Rafael, Compliance Officer (`Compliance` role) at the same fintech.

**Trigger**: A `BLOCK` notification lands in Rafael's queue for a contract with "DataSync
Consultoria," a data-migration consultancy the company wants to bring on for a six-month project.

1. Rafael opens the `ComplianceReview` for the DataSync contract (UC-6). Two `RuleEvaluation`s are
   flagged: `SANC-001` (sanctions hit) at `critical` severity, and `FIN-003` (value ≥ R$250,000) at
   `medium` severity, correctly routed for Legal review — but the `SANC-001` `BLOCK` dominates the
   aggregated outcome regardless (`ADR-010`: any BLOCK wins).
2. Rafael inspects the `SANC-001` evidence (UC-6, step 3): the `SupplierCheck` (UC-2) shows a hit
   against the CEPIM (Cadastro de Empresas Inidôneas e Suspensas) list — but the hit is against a
   company with a similar name and a different CNPJ, not an exact match on DataSync's own tax id.
3. Rafael recognizes this as a false-positive risk inherent to fuzzy name-matching in the underlying
   source data, not a defect in JuriSense's check logic itself. He requests a manual re-check
   (UC-2, Alternative flow A1) to confirm the CNPJ-level match explicitly, rather than trusting a
   name-similarity signal alone.
4. The re-check confirms: DataSync's actual CNPJ has zero hits on any sanctions list; the earlier
   flag was a data-quality artifact from the source's fuzzy matching on company name. This new,
   `completed` `SupplierCheck` becomes the current basis for the profile (UC-2 step 4), but the
   original flagged check remains in the immutable history — nothing is erased.
5. Rafael triggers a re-evaluation (`compliance.review_required`, UC-5 Alternative flow A2). The new
   `ComplianceReview` runs against the corrected `SupplierProfile`. `SANC-001` now evaluates to
   `PASS`. `FIN-003` still fires (`REVIEW`, approver role `legal`).
6. The aggregated outcome is now `REVIEW`, not `BLOCK`. An `ApprovalRequest` is routed to Legal
   (UC-8) since the contract's value crosses the R$250,000 threshold.
7. General Counsel reviews the now-clean supplier evidence alongside the contract terms, approves
   (UC-8 main flow), and the `Decision` finalizes as `APPROVE` (UC-9).
8. Rafael's investigation is fully preserved: the original `BLOCK`'s `RuleEvaluation`, the re-check
   that superseded the sanctions flag, and the final `APPROVE` all remain visible in sequence in the
   contract's history — a future auditor sees exactly how the false positive was caught and
   resolved, not just the final clean answer. This is precisely the kind of reconstructable
   narrative that email-and-spreadsheet compliance processes could never produce reliably.

---

## Journey 3: A Legal Counsel reviews and approves a high-value contract

**Persona**: Beatriz, General Counsel (`Legal` role), sole in-house lawyer at the company.

**Trigger**: Procurement has ingested a 3-year, R$1.4 million outsourced-development contract with
"NearShore Dev Partners," well above the `FIN-004` threshold (≥ R$1,000,000 → Legal + Director
approval).

1. Beatriz gets a routed `ApprovalRequest` (UC-8) — she's the first of two required approvers in
   this chain (`APR-003`); the second is the company's COO, acting in the `Approver` role, who will
   only see the request once Beatriz's step resolves.
2. Instead of reading all 60 pages of the contract cold, she opens the structured extraction (UC-4
   output): liability is capped at 2x annual fees (not unlimited — clears `LEGAL-008` automatically,
   no flag), jurisdiction is São Paulo courts (acceptable per standing policy), IP assignment terms
   are standard work-for-hire, and a DPA is attached and complete (personal data of the company's own
   customers will be accessible to NearShore's developers during the engagement).
3. The only triggered rule is `FIN-004` itself (value-based, `REVIEW`, requiring Legal + Director) —
   there is no substantive clause-level problem the Policy Engine flagged; the review requirement
   here is purely a function of contract size, exactly the kind of routine-but-mandatory scrutiny
   `FIN-004` exists to guarantee never gets skipped under deal pressure.
4. Beatriz still reads the liability and IP clauses in full via the cited page/span links (UC-6 step
   3) — a R$1.4M engagement warrants an actual human read, not just a rubber stamp — and confirms
   the extraction accurately reflects the source text.
5. Satisfied, she approves her step (UC-8 step 4-6), recording a brief note: "Reviewed liability cap,
   IP assignment, and DPA terms directly against source document — no issues; approving on value-
   threshold review requirement only."
6. The COO receives the second-step `ApprovalRequest` (UC-8 step 7), now with Beatriz's synthesized
   note visible alongside the same WHY/EVIDENCE summary, and approves within the day.
7. Both steps resolved `approved`, the `Decision` finalizes as `APPROVE` (UC-9), and the Evidence
   Package (UC-11) captures both approvers' identities, timestamps, and Beatriz's review note as
   permanent parts of the Decision Passport.
8. Eighteen months into the three-year engagement, a new CFO joins and asks why the company accepted
   a 2x liability cap instead of an uncapped indemnity on a deal this size. Beatriz — or whoever holds
   the General Counsel role by then — pulls up the Decision Passport and has a complete, contemporaneous
   answer in under a minute, including her own reasoning at the time, not a reconstruction from
   memory.

---

## Journey 4: An external auditor verifies a two-year-old decision using the public verification page

**Persona**: Carla, an independent auditor engaged by an enterprise customer that is running
due diligence ahead of acquiring the fintech from Journeys 1–3. Carla has no JuriSense account and no
relationship with JuriSense at all — she only has a decision reference the fintech's own team gave
her as part of the data room.

**Trigger**: The acquiring company's due-diligence checklist includes "demonstrate that vendor
compliance decisions were not altered after the fact" as a specific, material item — exactly the
scenario `docs/00-project/overview.md`'s "Why blockchain makes sense here" describes.

1. The fintech's Compliance Officer (Rafael, from Journey 2) shares a decision reference — a stable
   URL — for the DataSync Consultoria contract's now two-year-old `Decision`, pointing Carla to the
   public verification page (UC-12).
2. Carla opens the link. No login is required — this is the one surface in the product explicitly
   designed to be usable by someone outside the customer's organization entirely
   (`docs/06-blockchain/verification.md`).
3. The page shows: the anchored evidence hash, the anchoring provider and reference, the anchoring
   timestamp (which predates the acquisition conversation by well over a year), and a "Verify"
   action.
4. Carla clicks "Verify." The system calls `AnchoringProvider.verify(evidence_hash, proof)` against
   the public ledger itself — not against JuriSense's own database — and confirms the hash was
   anchored at the claimed time and has not been altered since (UC-12 main flow, step 6).
5. Carla notes in her due-diligence report that the vendor-compliance evidence trail for this
   contract is independently, cryptographically verifiable as unaltered since the original decision
   date — a materially stronger claim than "the vendor says their internal database logs weren't
   touched," which is the best any purely internal system could offer.
6. For a deeper check, Rafael (who does have platform access) additionally recomputes the
   `EvidencePackage`'s Merkle root directly from the underlying `Evidence` set (UC-12, Alternative
   flow A1) and confirms it matches the publicly anchored hash exactly — demonstrating not just "a
   hash was anchored," but "this specific, complete evidence bundle is the one that produced that
   hash," the strongest verification level available.
7. Carla never sees the underlying contract text, personal data, or any confidential detail through
   the public verification page itself (`BR-EVD-002`) — only the hash, timestamp, and proof; the
   substantive evidence review she needs for her broader audit happens separately, through
   controlled, permissioned access the fintech grants her directly, keeping the public surface
   genuinely public-safe while still supporting a rigorous audit when deeper access is warranted.
8. This single interaction — a two-minute check on a public page — becomes a concrete, citable line
   in the acquisition due-diligence report, exactly the kind of durable, third-party-checkable
   evidence the product's core promise (`docs/01-product/product-definition.md`) is built to
   deliver.
