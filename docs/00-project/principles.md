# Operating Principles

These are the principles that govern both the product's behavior and how it is engineered. Each one
exists because of a specific property JuriSense Gate needs, not as a generic engineering platitude —
the justification below each principle says why it matters *for this product specifically*, and where
in the domain model or architecture it is already enforced.

## Evidence over opinion

Every finding the product surfaces — a sanctions hit, a missing DPA, an unlimited liability clause —
must be traceable to a specific source: a document page/span, an external registry response, a named
policy rule. The product's entire value proposition is answering "why was this approved?" months
later with something better than "someone probably looked at it" (`docs/00-project/overview.md`); a
finding with no evidence behind it is exactly the kind of unverifiable claim the product exists to
eliminate. This is why `Clause` records must always carry a page/span citation before they can be used
as evidence in a `RuleEvaluation` (`BR-CON-004`), and why `RuleEvaluation.evidence_refs` is a required,
not optional, field.

## Deterministic where possible, AI where necessary

The APPROVE/REVIEW/BLOCK decision itself is computed by a deterministic rule engine, never by an LLM
call, precisely because a compliance decision must be explainable in one sentence to a customer's
Legal team and reproducible byte-for-byte from the same inputs years later (`ADR-010`) — properties
LLM output does not reliably have. AI is used exactly where it is strictly better than the
alternative: reading and structuring unstructured contract text at a volume no human reviewer can
sustain consistently (`docs/00-project/overview.md`, "Why AI makes sense here"). This split is
architecturally enforced, not a style preference: `AI-004` explicitly forbids `AI Services` output
from directly setting a `Decision` status — only `Policy & Compliance` may do so.

## Human-in-the-loop

Automatic `APPROVE` is reserved for cases where every rule genuinely passes; anything a rule flags as
`REVIEW` is routed to a specific human role and cannot silently resolve itself (`ADR-006`,
`BR-APR-001`). This matters because the failure mode this product is built to prevent is not "a
computer made a bad call" — it is "nobody with the right authority ever actually looked." Removing the
human from a `REVIEW`-tier decision would just relocate the original problem (unaccountable,
unreviewed approvals) one layer down instead of solving it, and would undermine the product's
credibility with exactly the Legal/Compliance buyers it is built for.

## Explain every decision

A bare status with no explanation is treated as a product defect, not an acceptable minimal output:
every `Decision` is accompanied by WHY, EVIDENCE, POLICY, SOURCE, RISK, REQUIRED ACTION, APPROVER,
AUDIT TRAIL, and VERIFICATION (`docs/00-project/overview.md`). This is not a UX nicety — it is what
separates a genuinely useful compliance tool from a black-box risk score that a Legal or Compliance
professional cannot act on or defend to their own leadership. It is also why the aggregation algorithm
itself was deliberately kept explainable-in-one-sentence rather than a weighted numeric score
(`ADR-010`, "Alternatives Considered").

## Version everything that a decision could depend on

Policies (`PolicyVersion`), contracts (`ContractVersion`), and decisions themselves (superseding
chains via `supersedes_decision_id`) are all immutable, append-only version sequences, never edited in
place (`BR-POL-001`, `BR-CON-002`, `BR-DEC-002`). If a customer tightens a policy next quarter, every
decision made under last quarter's policy must remain exactly reproducible against the policy version
that was actually in force at the time — a compliance product that let the ground shift under its own
past decisions would defeat its own purpose. This principle is what makes the Decision Passport
possible at all: reproducibility requires that nothing it depends on can silently change.

## Audit everything

Every meaningful state-changing action, without exception, emits an append-only `AuditEvent` that
cannot be edited or deleted by anyone, including an Admin (`BR-EVD-003`, `AUD-002`). This is a direct
response to the "institutional memory loss" failure mode described in `docs/00-project/problem.md` —
the departed reviewer, the Slack thread that rolled off retention. If the audit log itself could be
edited, it would be worthless as evidence the moment anyone needed to actually rely on it under
scrutiny (a regulator, an auditor, opposing counsel), so it is designed with no update or delete
operation exposed anywhere in the system, not merely restricted by permission.

## Privacy by design

No confidential document content or personal data is ever placed on-chain — only hashes and
commitments (`BR-EVD-002`); tenant isolation is enforced structurally via `organization_id` on every
tenant-owned table (`SEC-001`, `ADR-003`), not left to application-layer discipline alone. Given that
the product's core function is ingesting suppliers' and customers' contracts — which routinely contain
personal data, commercial secrets, and liability-sensitive terms — a privacy failure would not just be
a bug, it would directly contradict the LGPD-compliance promise the product is selling to Privacy and
Compliance buyers in the first place.

## Security by design

Every uploaded document is scanned before processing (`SEC-003`), every sprint's work must pass a
security audit before being considered done (`SEC-002`, `ADR-016`), and cross-tenant access is an
explicit, required test case, not an assumed property. A multi-tenant platform holding every
customer's supplier contracts and compliance findings is a uniquely attractive target — a cross-tenant
data leak in this specific product would simultaneously be a security incident and a compliance
failure for every affected customer, which is why security is a sprint gate rather than a
pre-launch checklist item.

## API-first

The Compliance Engine's decision capability is designed to be callable, not just clickable — this is
explicit in the long-term vision (`docs/00-project/vision.md`, "JuriSense API") and already present in
the hackathon-scope requirements as outbound webhooks for lifecycle events (`INT-002`). A product whose
end state is "compliance infrastructure other systems build on" cannot retrofit an API later; every
capability is built as a callable operation with a UI on top of it, not a UI with incidental API
access bolted on afterward.

## Modular architecture, not premature microservices

The backend is a single Python/FastAPI modular monolith with clean context boundaries (`ADR-001`,
`ADR-002`), not a microservices architecture, even though the domain is explicitly organized into
eight bounded contexts. At the company's current stage and team size, network-boundary overhead
between services would slow down the exact cross-context flows (extraction → policy evaluation →
decision → evidence) that need to stay fast and easy to reason about together, while the bounded-
context discipline (`docs/04-architecture/components.md` boundary rules — e.g., `AI Services` may
never directly set a `Decision`, `Integrations` may never write directly to business-domain tables)
already gives the team the option to extract a context into its own service later, if and when scale
or team topology actually demands it, without having paid the operational cost prematurely.

## No unnecessary blockchain — only where verifiability is the actual need

Blockchain is used for exactly one thing: anchoring the hash of an `EvidencePackage` so that a third
party can independently verify it was not altered after the fact (`ADR-007`) — never for storage,
never for computation, never as a marketing feature bolted onto unrelated parts of the product. This
restraint is explicit and intentional (`docs/00-project/overview.md`, "Why blockchain is NOT the
product"): the moment blockchain is used anywhere it isn't solving the specific "prove this wasn't
altered after the fact, to someone who doesn't have to trust our database" problem, it adds cost,
complexity, and a credibility risk (looking like a blockchain product chasing a hackathon sponsor)
without adding real customer value.

## Jurisdiction as configuration, not architecture

Brazil-specific logic — LGPD, CNPJ-based identity, CEIS/CNEP/CEPIM sanctions sources — lives in
swappable Jurisdiction Pack rule packs and Supplier Intelligence source adapters, not hardcoded into
the core domain model (`docs/00-project/overview.md`, "Internationalization"). Brazil is the right
first market for genuine go-to-market reasons (a large underserved mid-market with real procurement
volume and no TPRM tooling), but a compliance product whose core entities and Policy Engine only
understood one jurisdiction's rules would foreclose the international expansion the long-term vision
depends on, so the separation between the Core Platform and Jurisdiction Packs is a day-one
architectural decision, not a future refactor.
