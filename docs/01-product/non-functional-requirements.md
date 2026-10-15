# Non-Functional Requirements

This document states the non-functional requirements (NFRs) for JuriSense Gate: qualities the
system must exhibit regardless of which functional requirement (`docs/01-product/functional-
requirements.md`) is being exercised. Numeric targets below are stated as **targets to design and
test toward**, not contractual guarantees — several are explicitly marked `TBD` where a real number
would require load-testing or production data this early-stage product does not yet have. Overlap
with `docs/07-engineering/security.md` is intentional; that document owns implementation-level
security detail, this document owns the product-level requirement it must satisfy.

## Performance

Target latencies below assume a well-formed, typical-size input (a contract under ~50 pages; a
supplier check against up to 5 configured sources) under normal load, not worst-case adversarial
input.

- **Supplier check turnaround**: target end-to-end completion (from trigger to `SupplierCheck.
  status = completed`) under 30 seconds for a single supplier against Brazil-pack sources, assuming
  all external sources respond normally. Slower external source responses degrade this linearly and
  are surfaced as an in-progress state (UC-2), not a silent delay.
- **AI extraction turnaround**: target under 2 minutes from `ContractVersion` creation to
  `contract.analysis_completed` for a typical contract (under 50 pages), including fallback-provider
  scenarios. Documents requiring OCR (scanned, non-text-layer PDFs) are expected to take
  meaningfully longer; exact target is a `TBD` pending the OCR pipeline's own performance
  characterization (`docs/05-ai/document-intelligence.md`).
- **Policy execution (rule evaluation)**: target under 2 seconds to evaluate a full `PolicyVersion`
  (dozens of rules) against one normalized evaluation context — this step is deterministic,
  in-process computation with no external calls, so it should be the fastest stage of the pipeline
  by a wide margin; a regression here is a strong signal something has gone wrong architecturally
  (e.g., an accidental external call leaking into evaluation-context construction).
- **Interactive page load (dashboard, supplier/contract detail, approval queue)**: target
  first-meaningful-content under 2 seconds on a typical broadband connection, consistent with
  standard modern web-app expectations for a B2B SaaS product used daily by operational staff.
- **Blockchain anchoring confirmation**: inherently dependent on the chosen `AnchoringProvider`'s own
  confirmation time (`ADR-007`), which varies materially by chain/provider (seconds to several
  minutes). Because anchoring never gates a `Decision`'s own validity (`docs/01-product/use-
  cases.md`, UC-12 failure cases), this latency is explicitly decoupled from the decision pipeline's
  own performance target.

Status: TBD / Current preferred option: the targets above as directional design goals / Why
undecided: the first real load test (`docs/07-engineering/performance-baseline.md`, 2026-10-14)
only ran against a single-developer-machine dev environment, not production-equivalent
infrastructure — enough to confirm the architecture has no correctness bugs under concurrency
(and, in the process, found and fixed three real bugs invisible to the test suite), not enough to
set production capacity targets / Resolution: re-run the same baseline against production-
equivalent infrastructure before general availability / Decision artifact: `docs/07-engineering/
performance-baseline.md` (now exists; will be updated, not re-created, for the production-grade
re-run).

## Availability

- Target **99.5% monthly uptime** for the core web application and API during the initial commercial
  phase (single-VPS hosting per `docs/00-project/overview.md`'s current architecture decision),
  rising toward a higher target as hosting matures beyond a single VPS. This is a design target for
  a young product on modest infrastructure, not an SLA commitment to customers until formally
  offered as one.
- Planned maintenance windows are communicated in advance and scheduled outside Brazilian business
  hours (09:00–18:00 BRT) wherever feasible, given the initial market is Brazil-first.
- A single-VPS architecture (current hosting decision) means the AI provider APIs and the managed
  PostgreSQL database are the only externalized dependencies; an outage of either directly limits
  availability of AI-extraction-dependent and data-dependent flows respectively — this is an
  accepted tradeoff at current scale (`docs/00-project/overview.md`, "Hosting"), revisited as the
  product and customer base grow (see `docs/09-planning/roadmap.md` for when infrastructure
  investment is planned to scale beyond a single VPS).

Status: TBD / Current preferred option: 99.5% monthly target, no formal SLA yet / Why undecided: no
paying customers yet to size an SLA commitment against, and single-VPS hosting has known scaling
ceilings / Resolution: revisit once the first paying customers are onboarded and hosting scales
beyond a single VPS / Decision artifact: a future customer-facing SLA document, tracked alongside
`docs/02-business/pricing-strategy.md`.

## Scalability

- **Multi-tenant volume assumption**: designed for the initial target segment of technology
  companies with 50–1,000 employees (`docs/00-project/overview.md`, "Market"). A representative
  organization is assumed to register on the order of tens to low hundreds of active suppliers and
  process a similar order of contract reviews per year — not thousands of transactions per day. This
  assumption directly shapes the single-VPS + managed-Postgres + Redis/Celery architecture decision
  as adequate for the initial commercial phase, rather than requiring a distributed system from day
  one.
- **Logical multi-tenancy** (`organization_id` scoping, `ADR-003`) is the chosen isolation model,
  optimized for many small-to-mid organizations sharing infrastructure efficiently, at the cost of
  weaker isolation guarantees than schema-per-tenant — mitigated by mandatory cross-tenant-access
  testing in every sprint's security audit (`SEC-002`, `ADR-016`).
- **AI execution volume** scales with contracts reviewed, not with organization headcount directly;
  plan limits (`BR-ORG-003`) exist specifically to keep AI-provider cost proportional to what a
  customer is actually paying for, and to give early warning before infrastructure capacity is
  threatened by a single large customer's usage spike.
- **Horizontal scaling path**: Celery workers (`ADR-006`) are the first component expected to need
  horizontal scaling as AI-extraction and supplier-check volume grows, since they are already
  decoupled from the request/response cycle by design; the web/API tier and database are expected to
  scale later, once single-VPS capacity is genuinely challenged.

Status: TBD / Current preferred option: tens-to-low-hundreds of active suppliers per organization as
the initial capacity-planning assumption / Why undecided: no real customer usage data exists yet to
validate this assumption / Resolution: validate against actual usage after the first cohort of
paying customers onboards, and revisit the single-VPS ceiling explicitly if any customer approaches
it / Decision artifact: a future capacity-planning note in `docs/07-engineering/`.

## Security

Full implementation-level security requirements, controls, and the sprint-gate audit process live in
`docs/07-engineering/security.md` (cross-reference; that document is the authoritative source,
this section states the product-level requirement it exists to satisfy). At the product level:

- Tenant isolation (`SEC-001`) is a non-negotiable, always-on property of every tenant-owned table
  and every query path — never an opt-in setting.
- Every sprint's work is gated on a passing security audit including an explicit cross-tenant-access
  test before being considered done (`SEC-002`, `ADR-016`) — this is a process requirement as much
  as a technical one, and applies uniformly regardless of feature urgency.
- Uploaded documents are validated and scanned for malware/type-spoofing before any processing
  begins (`SEC-003`); no code path exists that processes an unscanned upload.
- Authentication uses stateless JWT with refresh-token rotation (`ADR-011`); passwords are hashed
  with Argon2id (`domain-model.md`, `User` entity); 2FA is supported at the account level.
- RBAC is enforced server-side on every action, never trusted from client-side role display alone
  (elaborated per-use-case in `docs/01-product/use-cases.md`'s "Permissions" and "Security
  considerations" sections).

## Privacy & LGPD compliance

- The platform is **LGPD-first by design**, not retrofitted: tenant isolation, data minimization in
  what's placed on-chain (`BR-EVD-002`), and explicit data-processing-terms tracking for the
  organization's own suppliers (the very thing `LGPD-001` checks for in customer contracts) are all
  first-class, not optional add-ons.
- Personal data handled by the platform falls into two categories with different treatment: (1)
  personal data of the *customer's own staff* (users of the platform itself — names, emails,
  authentication data), handled as any SaaS product's own controller obligations require; and (2)
  personal data that may appear *within* uploaded contract/supplier documents (e.g., a supplier's
  responsible party's name in a registry record, or a data subject's information referenced within a
  contract's scope) — handled as data the platform processes on the customer's behalf, under the
  customer's own LGPD controller responsibilities, with JuriSense acting as an operator/processor for
  that content.
- No raw contract text or personal data is ever included in any on-chain payload — only hashes/
  commitments (`BR-EVD-002`, `EVD-004`; full treatment in `docs/06-blockchain/privacy.md`). This is
  the single most important LGPD-relevant architectural guarantee in the product, since it means the
  irreversibility/immutability of blockchain anchoring (which would otherwise be in tension with data
  subject rights like erasure) never applies to actual personal data — only to hashes that reveal
  nothing about the underlying content.
- Data Processing Agreements with any third-party AI provider onboarded into the AI Gateway
  (`ADR-005`) are a contractual prerequisite, including provider data-retention and
  training-opt-out terms (`docs/05-ai/ai-strategy.md`), before that provider handles any customer
  document content.
- Data subject rights (access, correction, deletion, portability) for the platform's own users are
  supported through standard account-management flows; data subject rights concerning personal data
  *within* customer-uploaded documents are the customer's own responsibility as controller, with
  JuriSense providing the technical means (e.g., locating and, where the immutability requirements of
  evidence retention allow, redacting or restricting further processing of specific records) to
  fulfill them.

Status: TBD / Current preferred option: JuriSense as operator/processor for document content, with a
standard Data Processing Agreement offered to every customer / Why undecided: exact contractual DPA
language and the interaction between data-subject erasure requests and immutable evidence retention
(`BR-EVD-001`, `BR-EVD-003`) needs legal review / Resolution: legal review before general
availability, producing a customer-facing DPA and an internal erasure-request handling procedure /
Decision artifact: a future `docs/02-business/legal-and-compliance-posture.md` and `docs/06-
blockchain/privacy.md`.

## Data retention

- **Audit events** (`AuditEvent`) are retained indefinitely by design — the append-only, no-delete
  invariant (`BR-EVD-003`, `AUD-002`) applies even to Admin roles, since the audit log's evidentiary
  value depends on nobody, including the platform operator's own privileged users, being able to
  shorten it.
- **Decisions, Evidence Packages, and RuleEvaluations** are retained indefinitely for the same
  reason: the product's core promise is verifiability that survives time, which requires the
  underlying evidence to actually still exist years later, not just the anchored hash.
- **SupplierCheck history** is retained indefinitely per supplier (`SUP-005`) — this is what makes
  "what did we know, and when" answerable for compliance and audit purposes.
- **Documents** (uploaded contracts and supporting evidence) are retained for the life of the
  associated `Contract`/`Supplier` relationship plus a retention period after termination/
  inactivation, to support post-relationship audits and disputes.
- **Account/session data** (e.g., login history, expired refresh tokens) follows a shorter,
  operational retention window distinct from compliance-evidence retention, since it serves a
  different purpose (security monitoring, not compliance evidence).

Status: TBD / Current preferred option: indefinite retention for all compliance-evidence-bearing
records (decisions, evidence packages, rule evaluations, supplier checks, audit events); a
multi-year but finite retention window for raw uploaded documents post-relationship-termination /
Why undecided: exact document-retention duration after contract termination requires legal input on
Brazilian statute-of-limitations considerations for contractual disputes and any sector-specific
retention obligations a given customer might carry / Resolution: legal review before general
availability / Decision artifact: a future `docs/02-business/legal-and-compliance-posture.md`.

## Internationalization readiness

- The architecture separates a **Core Platform** from **Jurisdiction Packs** (Brazil Pack today; US/
  EU/UK/LATAM packs as future work), per `docs/00-project/overview.md`'s "Internationalization"
  section and `docs/04-architecture/architecture-overview.md`. Jurisdiction-specific logic — CNJ-
  equivalent identifiers, sanctions/registry source adapters, LGPD-specific policy rule templates —
  lives in Policy Engine rule packs and Supplier Intelligence source adapters, never hardcoded into
  the core domain model.
- The product's UI copy and content are being written in English (per this project's current
  documentation-language convention) but the **product itself** must support localized UI text as a
  forward-looking requirement, since the initial customer base operates in Portuguese (pt-BR) day to
  day even though internal engineering/product documentation is in English.
- Currency and value fields (`contract.value.brl`, per `docs/03-domain/policy-engine.md`'s evaluation
  context example) are explicitly typed with a currency field, not assumed to be a single hardcoded
  currency, so that a future non-Brazil jurisdiction pack does not require a schema change to
  represent contract value.
- Date/time handling assumes explicit timezone-awareness throughout (critical for SLA timers on
  `ApprovalRequest` expiration, `BR-APR-003`, and for any future jurisdiction-specific business-day/
  holiday calendar logic a jurisdiction pack might introduce).

Status: TBD / Current preferred option: English-only UI at initial launch, with the underlying
architecture kept i18n-ready rather than i18n-complete / Why undecided: full UI localization
infrastructure (translation management, locale-aware formatting throughout) is not yet built and is
not required for the Brazil-first hackathon/early-commercial phase / Resolution: revisit when a
non-Brazil jurisdiction pack is scheduled (Phases 9–11 and beyond, `docs/01-product/future-product-
vision.md`) / Decision artifact: `docs/02-business/international-market.md`.

## Observability

- Every state-changing action across all 8 bounded contexts emits a structured, append-only
  `AuditEvent` (`AUD-001`) — this is simultaneously a compliance requirement and the backbone of the
  product's own operational observability, since the audit log doubles as a rich, queryable record of
  system behavior.
- Application-level logging, metrics, and tracing (request latency, AI Gateway provider
  success/fallback rates, Celery queue depth/latency, external source-adapter response times) are
  expected standard operational tooling for a production service; exact tooling choice (e.g.,
  OpenTelemetry, a specific APM vendor) is an implementation detail owned by `docs/07-engineering/`
  rather than a product-level NFR.
- AI Gateway executions specifically log model/provider used, prompt version, latency, and
  fallback-trigger events (`docs/05-ai/ai-strategy.md`) — both for debugging and because this data
  feeds directly into the Decision Passport's "AI executions (model/prompt version)" field
  (`docs/00-project/overview.md`).
- Alerting thresholds for the failure modes described throughout `docs/01-product/use-cases.md`
  (e.g., "all supplier-check sources unreachable," "both AI providers fail," "anchoring provider
  permanently unavailable") are expected to exist as operational monitors, not just documented
  failure cases with no corresponding alert.

## Accessibility

- The web application targets **WCAG 2.1 Level AA** conformance as the baseline accessibility
  standard for a B2B SaaS product used daily by operational staff across multiple roles/functions,
  some of whom may have accessibility needs the product must not exclude.
- Specific attention areas given the product's own information density: the approval synthesis
  screen and Decision Passport (dense, evidence-heavy views) must remain navigable via keyboard and
  screen-reader-compatible, since these are exactly the screens a time-pressured Approver or an
  Auditor depends on most.
- Clause-citation highlighting (linking a `RuleEvaluation` back to a specific page/span in a source
  document) must have a non-color-dependent visual treatment (e.g., not relying on color alone to
  indicate "this text triggered a BLOCK") to remain usable for colorblind users, given how central
  color-coded severity (`critical/high/medium/low`) and outcome (`APPROVE/REVIEW/BLOCK`) states are
  to the product's core UI vocabulary.

Status: TBD / Current preferred option: WCAG 2.1 AA as the target, verified via automated + manual
audit before general availability / Why undecided: no formal accessibility audit has been performed
yet at this early implementation stage / Resolution: schedule an accessibility audit ahead of general
availability, not deferred indefinitely as a "nice to have" / Decision artifact: a future `docs/07-
engineering/accessibility-audit.md`.
