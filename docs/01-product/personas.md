# Personas

Each persona below maps to one or more `Role`s from `ADR-003` (`Admin, Procurement, Legal,
Compliance, Privacy, Security, Finance, Approver, Auditor, Viewer`). A real person may hold more
than one `Role` (e.g., a Head of Procurement at a 120-person company might also be the `Admin`), and
a `Role` may be held by more than one persona in different organizations (e.g., `Approver` might be
a Director, a CFO, or a founder depending on company size) — the mapping below states the *typical*
fit for a 50–1,000-employee Brazilian technology company, JuriSense Gate's initial target segment
(`docs/00-project/overview.md`, "Market").

---

## Procurement Manager

**Primary Role**: `Procurement`. Often also holds `Admin` in smaller organizations.

**Goals**
- Onboard new suppliers/vendors quickly without becoming the bottleneck between "the team wants
  this tool" and "we're allowed to sign."
- Keep a clean, current record of every active supplier and contract, without chasing Legal,
  Compliance, and Finance over email for status.
- Avoid being the person blamed six months later for a vendor relationship that turns out to have
  an unacceptable clause or a sanctions flag nobody caught.
- Hit internal SLAs for procurement cycle time that the business holds Procurement accountable for.

**Daily pains today**
- A new SaaS tool request comes from an engineering or marketing lead; the Procurement Manager has
  no systematic way to check the vendor's registration status or sanctions exposure beyond an ad hoc
  Google search.
- Contract review is a black box: the document goes to Legal via email or Slack and disappears for
  days or weeks, with no visibility into where it is in the process.
- There is no single place to see "every supplier we've approved, with what conditions, and when
  each needs re-review" — this lives in spreadsheets, if it lives anywhere.
- When someone asks "did we ever check if Vendor X processes personal data under our DPA
  requirements," the honest answer is often "I'd have to go dig through email."

**How they use JuriSense Gate**
- Registers new `Supplier`s (`SUP-001`) and uploads the first contract document (`CON-001`) as soon
  as a vendor relationship starts, before waiting for a signature to make it "official."
- Watches the `SupplierCheck` result (`SUP-002`, `SUP-003`) come back automatically — no more manual
  registry lookups.
- Tracks every supplier and contract's current status (`prospect/under_review/approved/blocked`) in
  one dashboard instead of a spreadsheet.
- Gets a plain-language `APPROVE/REVIEW/BLOCK` outcome with WHY/EVIDENCE/POLICY, and — critically —
  knows immediately whether they can proceed to signature or need to wait on a named approver.
- Receives outbound notifications (`INT-002` webhook events like `contract.review.completed`,
  `approval.required`) instead of having to poll anyone for status.

**What they see in the product (their `Procurement` role view)**
- Full read/write on `Supplier` and `Contract`/`Document` creation and status.
- Visibility into `ComplianceReview` outcomes and `Decision` status, but not edit rights over
  `Policy`/`Rule` definitions (that's Legal/Compliance's job) or resolution rights over
  `ApprovalRequest`s requiring a different role.
- A supplier/contract pipeline view (kanban- or list-style) showing where every active vendor
  relationship sits in the pipeline described in `docs/00-project/overview.md`.

---

## General Counsel / Legal Counsel

**Primary Role**: `Legal`.

**Goals**
- Make sure every signed contract has been checked for the clauses that create real legal exposure
  (unlimited liability, missing/weak indemnification, unfavorable jurisdiction, auto-renewal traps)
  — for every contract, not just the ones someone happened to flag.
- Spend review time on the contracts that actually need a lawyer's judgment, not on re-reading
  boilerplate that hasn't changed since the last vendor.
- Be able to answer, credibly and quickly, "why did we accept this term" for any contract, at any
  point in the future — including after they've left the company or forgotten the specific deal.
- Maintain control over what "acceptable" means for the company, rather than have that judgment
  made ad hoc by whoever happens to be negotiating.

**Daily pains today**
- Contracts arrive with no structure — a 40-page PDF with the liability clause on page 22 and the
  DPA terms scattered across an appendix. Finding the parts that matter is manual, every time.
- No systematic way to apply "our standing policy" (e.g., "we require a liability cap," "we require
  a DPA if personal data is processed") consistently across every contract that comes through;
  policy lives in the Counsel's head or in an old memo nobody re-reads.
- Legal is a bottleneck by necessity (there's often only one Legal Counsel for the whole company),
  and every contract review competes with actual legal work for their attention.
- No audit trail: when someone questions a past approval, the reconstruction is "let me check my
  email from eight months ago."

**How they use JuriSense Gate**
- Authors and versions the company's own `Policy`/`Rule` set in the DSL (`POL-001`, `POL-002`) —
  e.g., `LEGAL-008: unlimited liability → REVIEW, approver_role: legal`.
- Uses simulation/dry-run (`POL-003`) before publishing a policy change, to see how many active
  contracts would suddenly fail under a tightened rule before committing to it.
- Reviews the structured, cited extraction (`Clause` list with page/span provenance, `CON-004`)
  instead of re-reading the whole document from scratch — goes straight to the flagged clauses.
- Resolves `ApprovalRequest`s routed to the `legal` `approver_role` (`APR-002`) with a documented
  justification, and can invoke manual override (`DEC-002`) on a `Decision` when their judgment
  differs from the automated outcome — always with mandatory justification (`BR-DEC-003`).
- Relies on the Decision Passport (`docs/03-domain/evidence.md`) as their answer to "why did we
  accept this" months or years later, without depending on their own memory or a former colleague's.

**What they see in the product (their `Legal` role view)**
- Full read/write on `Policy`/`PolicyVersion`/`Rule` authoring and publishing.
- Full visibility into every `ContractVersion`'s extracted data and `Clause`-level citations.
- Approval queue filtered to requests where `approver_role = legal`, sorted by severity
  (`docs/03-domain/policy-engine.md`, "Severity & escalation").
- Override capability on `Decision`s, gated by role and always requiring justification.
- Explicitly does **not** see this as a legal-advice tool — see `docs/01-product/product-
  definition.md`'s "Boundary of responsibility" section, which the General Counsel persona is, not
  coincidentally, the most attentive reader of.

---

## Compliance Officer

**Primary Role**: `Compliance`.

**Goals**
- Ensure every supplier and contract that could create regulatory or reputational exposure gets
  caught before signature, not after an incident.
- Maintain a defensible, reproducible compliance program that can withstand an internal audit, a
  customer's due-diligence questionnaire, or a regulator's inquiry.
- Reduce the number of exceptions and overrides over time by tightening policy where the data shows
  recurring risk patterns.
- Be the credible owner of "how we do compliance here," backed by evidence rather than tribal
  knowledge.

**Daily pains today**
- Compliance checks (sanctions lists, registry status) are manual, inconsistent, and easy to skip
  under deadline pressure — "we'll check it after we sign" becomes the default when checking is
  slow.
- No consolidated view of risk across the supplier/contract portfolio — risk exposure is only
  visible one contract at a time, if at all.
- Exceptions and overrides, when they happen, aren't tracked systematically, so there is no way to
  see whether the same rule keeps getting waived (a signal that either the rule or the underlying
  process is wrong).
- Proving compliance posture to an external auditor or an enterprise customer's security/compliance
  questionnaire is a scramble of screenshots and emails.

**How they use JuriSense Gate**
- Owns the `ComplianceReview` process end to end: reviews `RuleEvaluation` outcomes across the
  portfolio, not just per-contract (`CMP-001`, `CMP-002`, `CMP-003`).
- Investigates `BLOCK` and `REVIEW` outcomes, reading WHY/EVIDENCE/SOURCE straight from the
  `RuleEvaluation` rationale and its linked `Clause`/`SupplierCheck` evidence.
- Grants time-boxed policy exceptions (`POL-004`) with mandatory justification when a specific,
  reasoned deviation is warranted — and can see the full history of exceptions granted, by whom,
  and why.
- Uses the audit event catalog (`docs/03-domain/audit.md`) and Decision Passports as the backbone of
  periodic compliance reporting and any external audit response.
- Is typically the primary or co-primary author of `SANC-001`-style critical rules (sanctions hits,
  `BR-SUP-004`) alongside Legal.

**What they see in the product (their `Compliance` role view)**
- Full visibility into `ComplianceReview`, `RuleEvaluation`, `Risk`, and exception records across the
  organization's entire portfolio, with filtering/sorting by severity and status.
- Rule-authoring rights on Compliance-owned rule categories (sanctions, regulatory), typically
  co-owned with `Legal` for legally-flavored rules.
- Approval queue for `approver_role = compliance`.
- Access to portfolio-level reporting views (aggregate BLOCK/REVIEW/APPROVE rates, exception
  frequency, override frequency) that a Procurement or Legal user would not need day to day.

---

## Privacy Officer / DPO (Data Protection Officer)

**Primary Role**: `Privacy`.

**Goals**
- Ensure every supplier that processes personal data on the company's behalf has a valid Data
  Processing Agreement (DPA) and appropriate LGPD-compliant terms before the relationship goes live.
- Maintain an accurate, current inventory of which vendors process personal data, what categories,
  and under what legal basis — the record LGPD (and any future GDPR-pack equivalent) expects a
  controller to keep.
- Avoid discovering a data-processing gap only after a data subject complaint or an ANPD inquiry.

**Daily pains today**
- "Does this vendor process personal data?" is a question buried inside a contract's fine print,
  not something Procurement or even Legal reliably flags for Privacy review.
- DPA presence/absence is tracked, if at all, in a separate spreadsheet that quickly goes stale as
  new vendors are added.
- No systematic linkage between "this contract processes personal data" and "therefore this
  specific clause set must be present," so gaps are found reactively.

**How they use JuriSense Gate**
- Relies on AI structured extraction to flag `contract.processes_personal_data` and
  `contract.dpa_present` as normalized fields (`docs/03-domain/policy-engine.md`, "Evaluation
  context & input normalization") rather than reading every contract personally.
- Owns and authors LGPD-category policy rules such as `LGPD-001` (DPA required when personal data is
  processed → `BLOCK` if absent) — the canonical example rule in `docs/03-domain/policy-engine.md`.
- Resolves `ApprovalRequest`s routed to `approver_role = privacy` for contracts that require a
  human privacy judgment call beyond the automated `BLOCK`/`PASS` on DPA presence.
- Uses the Decision Passport as their record of "we verified this vendor's data-processing terms
  before we started sending them personal data" — directly useful for LGPD Article 5/39-style
  accountability documentation and vendor-management obligations.

**What they see in the product (their `Privacy` role view)**
- Full visibility into the personal-data-processing fields of every `ContractVersion`'s extracted
  data, and every rule evaluation tagged to a privacy-category rule.
- Rule-authoring rights on privacy/LGPD-category rules.
- A dedicated "vendors processing personal data" register view — the closest in-product analogue to
  the recorded-processing-activities obligation LGPD expects a controller to maintain for its
  processors.
- Approval queue for `approver_role = privacy`.

---

## Security Lead

**Primary Role**: `Security`.

**Goals**
- Catch vendors and contracts with an inadequate security posture (no SOC 2/ISO 27001 equivalent,
  weak breach-notification terms, unclear sub-processor chains) before the company becomes
  dependent on them.
- Keep security review from being the thing that gets skipped when a deal is time-pressured.
- Have a record, for the company's own security audits and customer due-diligence, of what security
  posture every material vendor had at the time they were approved.

**Daily pains today**
- Security review of a vendor is often informal or entirely skipped for lower-profile purchases
  (a $200/month SaaS tool gets none of the scrutiny a $200,000 outsourcing contract gets, even
  though both can carry real security exposure — e.g., broad data access scopes).
- No structured link between "this vendor has access to X system/data" and "therefore requires Y
  level of security review."
- Breach-notification and security-related contract terms are buried in the same undifferentiated
  document as commercial terms, with nothing surfacing them specifically to Security's attention.

**How they use JuriSense Gate**
- Authors and maintains security-category policy rules (e.g., minimum required security
  certifications for a given contract value/data-access tier, breach-notification SLA thresholds).
- Reviews `RuleEvaluation`s in the security category as part of the compliance review, using the
  same structured extraction and citation model Legal and Privacy use.
- Resolves `ApprovalRequest`s routed to `approver_role = security` for higher-risk vendor
  relationships (e.g., a vendor requiring broad system access or handling sensitive infrastructure).
- Uses the immutable `SupplierCheck`/`Document` hash history as part of their own security audit
  evidence trail when a customer or regulator asks how the company vets its vendors.

**What they see in the product (their `Security` role view)**
- Full visibility into security-relevant extracted contract fields and security-category rule
  evaluations.
- Rule-authoring rights on security-category rules.
- Approval queue for `approver_role = security`.
- Read access to `Document`/`Evidence` hashes for their own audit-evidence purposes, without needing
  edit rights over Procurement's or Legal's own workflow.

---

## CFO / Finance Stakeholder

**Primary Role**: `Finance`.

**Goals**
- Ensure high-value contracts get the financial and legal scrutiny their size warrants, without
  every routine renewal needing the same level of attention.
- Have visibility into aggregate vendor spend commitments and contract-driven financial exposure
  (auto-renewal traps, penalty clauses, currency/FX exposure) across the portfolio.
- Trust that the approval thresholds tied to contract value (`FIN-003`, `FIN-004` in
  `docs/03-domain/policy-engine.md`) are actually enforced consistently, not applied selectively
  under deal pressure.

**Daily pains today**
- Finance frequently only learns about a new recurring vendor commitment when the invoice shows up,
  not before the contract is signed.
- Auto-renewal and penalty clauses are a recurring source of budget surprises because nobody
  systematically flags them at signature time.
- There's no consistent, enforced rule like "any contract above R$250,000 requires Legal sign-off,
  above R$1,000,000 requires Legal + Director" — thresholds like this exist informally at best.

**How they use JuriSense Gate**
- Authors or co-authors value-threshold policy rules (`FIN-003`: ≥ R$250,000 → REVIEW/legal;
  `FIN-004`: ≥ R$1,000,000 → REVIEW/legal+director), and trusts the Policy Engine to apply them
  identically to every contract, every time, with no exceptions unless explicitly and auditably
  granted (`POL-004`).
- Resolves `ApprovalRequest`s routed to `approver_role = finance` (e.g., budget-fit review) and, in
  smaller organizations, may also carry the `director`-equivalent `Approver` role for
  `FIN-004`-triggered reviews.
- Uses the extracted `contract.value`, renewal terms, and penalty clauses as structured, queryable
  data instead of manually tracking financial commitments contract-by-contract.

**What they see in the product (their `Finance` role view)**
- Full visibility into financial terms across the contract portfolio: value, currency, renewal
  terms, penalty clauses.
- Rule-authoring rights on value-threshold rules.
- Approval queue for `approver_role = finance`.
- A portfolio-level financial exposure view (aggregate committed spend, upcoming auto-renewals) —
  useful for budgeting conversations even outside the compliance-decision flow itself.

---

## Approver (e.g., Director / Executive Sponsor)

**Primary Role**: `Approver` (in practice often layered onto a Director, VP, or founder's account
alongside whatever functional role they also hold — e.g., a Director of Engineering approving a
`FIN-004`-triggered contract is `Approver` for that decision even if their day-to-day role in the
system is otherwise minimal).

**Goals**
- Make a fast, well-informed go/no-go call on the small number of high-stakes decisions escalated to
  them, without having to read the entire underlying contract or become an expert in the company's
  compliance policy.
- Trust that if something reaches their desk, it genuinely needs their judgment — not get buried in
  low-value approval requests that erode their attention for the ones that matter.
- Be able to justify their decision later if questioned, without relying on memory.

**Daily pains today**
- High-value or high-risk approvals arrive as an email thread with a contract attachment and no
  synthesis — the Approver has to either trust whoever forwarded it or spend time they don't have
  reading the source document themselves.
- No visibility into what specifically was flagged and why; approvals become a rubber stamp because
  the alternative (deep review) doesn't scale to their calendar.
- No record, after the fact, of exactly what information the Approver had when they said yes.

**How they use JuriSense Gate**
- Receives `ApprovalRequest`s (`APR-001`) only for the cases their `approver_role` is required for
  — by construction, this is already the filtered, high-signal subset (`FIN-004`-tier value,
  highest-severity REVIEW rules per `docs/03-domain/policy-engine.md`'s severity/escalation model).
- Sees a synthesized view: the WHY/EVIDENCE/POLICY/RISK summary, not the raw 40-page contract,
  with the option to drill into the cited clause if they want more.
- Approves or rejects (`approval.approved`/`approval.rejected`) with the system recording exactly
  what evidence was presented at the time of their decision — this becomes part of the permanent
  Decision Passport.
- Can be part of a multi-step chain (`APR-003`, e.g., Legal then Director for the highest-severity
  cases) so their decision is informed by an earlier specialist's review, not made in isolation.

**What they see in the product (their `Approver` role view)**
- A minimal, focused approval queue — only requests where they are the named approver, nothing else
  in the system's day-to-day operational surface.
- A decision summary screen optimized for a 2–5 minute review: outcome context, WHY, key evidence
  citations, risk severity, and the approve/reject action with a mandatory-when-rejecting (and
  recommended-when-approving-against-a-flag) justification field.
- No policy-authoring or supplier/contract-management surface — this role is intentionally narrow.
