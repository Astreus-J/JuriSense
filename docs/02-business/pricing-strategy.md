# Subscription plans and cost model

> Proposed launch catalog, 2026-10-07. Replaces the earlier feature-gated tier hypothesis at
> the project owner's request: **every plan includes the same released product features;
> only usage allowances differ**. Prices are in BRL per organization. These are cost-based
> planning estimates, not verified expenses or validated willingness-to-pay results.
> This document does not activate billing or change existing subscriptions.

## 1. Product scope and feature parity

JuriSense Gate is the supplier, contract, and compliance platform described in
[the product definition](../01-product/product-definition.md), not the archived legal ERP.
All plans include released supplier verification, contract extraction, policy authoring and
versioning, deterministic compliance evaluation, approval workflows, Decision Passports,
evidence, audit history, verification, and role-based permissions. Use the same AI quality
criteria, security controls, workflow capabilities, and standard support across tiers.

API access, integrations, SSO, OCR, and additional standard compliance packs must follow the
same feature-parity rule **when released**. Their presence in a roadmap is not availability.
The current extraction implementation explicitly rejects scanned PDFs without extractable
text; OCR cannot be advertised as delivered. The configured evidence provider defaults to a
signed transparency log; do not describe that fallback as an active blockchain anchor.
Constellation DED requires provisioning and a confirmed production price.

No tier gets exclusive automation, better decision quality, or exclusive security. Enterprise
negotiates capacity. Bespoke implementation work is separately scoped professional services,
not a hidden requirement to use standard features. No differentiated support SLA is assumed.

## 2. Recommended launch catalog

| Allowance | Starter | Business | Growth | Enterprise |
|---|---:|---:|---:|---|
| Monthly price | R$149 | R$349 | R$799 | Individually costed quote |
| Annual prepaid total (10% discount) | R$1,609.20 | R$3,769.20 | R$8,629.20 | Negotiated |
| Annual equivalent per month | R$134.10 | R$314.10 | R$719.10 | Negotiated |
| Active users | 5 | 15 | 50 | Finite agreed quota |
| Active suppliers | 100 | 500 | 1,500 | Finite agreed quota |
| Supplier verification bundles / month | 100 | 300 | 800 | Finite agreed quota |
| Contract analyses / month | 30 | 100 | 300 | Finite agreed quota |
| AI processing units / month | 60 | 200 | 600 | Finite agreed quota |
| Stored documents and evidence | 15 GB | 50 GB | 150 GB | Finite agreed quota |
| Active policies | 10 | 40 | 120 | Finite agreed quota |
| External API requests / month, when released | 10,000 | 50,000 | 200,000 | Finite agreed quota |
| Product features and standard support | All released features | All released features | All released features | All released features |

The expanded allowance revision keeps the original prices. Seats, supplier stock, policies,
and API allowances grow substantially; storage grows 1.5–3 times. Contract and AI allowances
grow 33–50%, preserving two budgeted AI units per ordinary contract. Support and operational
reserves also increase to reflect more users and traffic; capacity still needs load validation.
Active supplier capacity is intentionally larger than monthly refresh capacity on Business and
Growth: storing a supplier does not imply refreshing every supplier each month. Automatic
refreshes must share the visible verification allowance and expose pending checks to the user.

Starter supports a small cross-functional team; Business is the suggested default for recurring
procurement; Growth serves several teams. These are introductory price hypotheses, not claims
that customer affordability or capacity has already been validated. There is no unlimited paid
resource, including in Enterprise. Existing backend identifiers remain `starter`, `business`,
`growth`, and `enterprise`.

Offer a 14-day trial with the same feature set, 3 users, 10 active suppliers, 10 verification
bundles, 3 contract analyses, 6 AI units, 1 GB, and 5 active policies. These are total trial
allowances, not daily resets. No permanent free plan: supplier checks, AI, support, and retention
continue to have costs. Trial conversion is manual while ADR-014 defers a payment gateway.

## 3. What each quota means

- **Organization:** quotas are shared by the organization's users, not multiplied by seats.
  Active users plus valid reserved invitations count toward the seat limit.
- **Active suppliers:** a stock limit, not monthly consumption. Archiving frees an active slot
  but does not erase evidence, refund verifications, or free retained storage.
- **Supplier verification bundle:** one requested refresh against the standard source set.
  Repeated uncached refreshes consume another bundle. An idempotent retry consumes no second
  customer unit. The cost model assumes R$0.05 per bundle; paid sources require re-costing.
- **Contract analysis:** one successfully processed contract version or explicitly requested
  reanalysis. A normal analysis includes extraction and downstream compliance evaluation;
  it consumes one contract allowance and its displayed AI units, never a separate automatic fee.
- **AI processing unit:** proposed metering abstraction, not a current gateway feature. One unit
  budgets at most 20,000 input plus 4,000 output tokens across the job's provider attempts.
  Aggregate retries and fallback when measuring provider cost; refund customer units on technical
  failure. Provider failures are an operator cost, not a surprise charge. Reserve units before
  work starts. Longer jobs need a visible estimate and sufficient units before processing.
  Two units per ordinary contract are budgeted; actual consumption can be lower. This avoids
  treating an arbitrarily long document as one cheap call. Until token-aware metering and full
  document handling exist, these allowances are a launch specification, not a promise of
  supported document length. The existing 60,000-character truncation needs explicit handling.
- **Storage:** total retained originals, versions, and evidence, in decimal GB. It never resets
  monthly. Audit metadata/backup overhead is costed internally; no paid security-history gate.
- **Policies:** simultaneously active policies. Historical versions stay available and count
  toward storage where applicable. Authoring and routing capabilities are identical by plan.
- **API requests:** external integration traffic, not ordinary dashboard requests or public
  verification. A request that triggers analysis also consumes the relevant analysis quota.
  Public verification still needs abuse protection; paid quotas must not prevent third-party
  verification of an already issued proof. Webhook retries need bounded platform retry policies.

Monthly allowances reset on subscription anniversaries using stored UTC cycle boundaries,
including on annual subscriptions; annual payment does not release twelve months of AI at once.
Unused monthly processing allowances expire. Stock limits do not reset. Before execution, show
which quota will be consumed; do not promise every contract allowance remains usable after the
customer spends its AI units on other tasks.

## 4. Evidence behind the costs

Repository evidence:

- [Deployment](../04-architecture/deployment.md): VPS + Docker Compose, Neon, Redis on the VPS,
  S3-compatible object storage, external AI, SMTP, and evidence provider.
- [Configuration](../../backend/app/core/config.py): OpenRouter and free-model defaults;
  25 MB upload limit; 60,000-character extraction ceiling; transparency-log default.
- [Current plan constants](../../backend/app/identity/domain/constants.py): old placeholder
  limits, including Enterprise `None` values meaning unlimited; not the catalog above.
- [Provider findings](../06-blockchain/anchoring-providers.md): DED credentials pending and
  fallback semantics. Free test operation is not evidence of zero production cost.

The owner reported approximately **R$500/month for the VPS** on 2026-10-07, plus AI API
expenses without a quantified amount. Treat the VPS figure as an owner-provided estimate, not an
audited invoice. No consumption export was supplied; all other figures below remain assumptions.
Do not report the remaining budgets as current spend. Do not base sustainable prices on promotional cloud credits
or free AI models.

Public reference tariffs consulted on 2026-10-07:

| Service | Published reference | Use in this model |
|---|---|---|
| Cloudflare R2 Standard | US$0.015/GB-month; writes US$4.50/million; reads US$0.36/million | Storage provision R$0.15/GB-month including headroom; operations in the miscellaneous reserve |
| Neon Launch | Official compute-price announcement: US$0.106/CU-hour | Illustrative 0.25 CU × 730 hours × US$0.106 × R$6 = R$116.07; budget R$150 including storage/headroom, subject to actual tariff and utilization |
| Gemini 2.5 Flash Lite via OpenRouter | US$0.10/million input tokens; US$0.40/million output tokens | Reference only, not a model selection or quality endorsement |

Sources: [R2 pricing](https://developers.cloudflare.com/r2/pricing/),
[Neon compute pricing announcement](https://neon.com/blog/major-compute-price-reduction-on-neon),
[OpenRouter model pricing](https://openrouter.ai/google/gemini-2.5-flash-lite).
Check the actual account tariff before purchase; the Neon announcement is not an account quote.

**Planning exchange rate: R$6/US$**, a scenario assumption rather than today's FX quote.
At the illustrative AI tariff, 20,000 input + 4,000 output tokens cost US$0.0036, or R$0.0216.
Reserve **R$0.40 per included AI unit**, substantially above this narrow reference, for more
expensive validated models, retries, gateway charges, and workload variation. This is a budget,
not a measured unit cost or a promise that every model fits. Validate on representative contracts
with the project's quality evaluation before changing providers. No model switch is made here.

### Shared monthly operating budget

| Shared expense | Scenario budget |
|---|---:|
| VPS, application, workers, Redis (owner estimate) | R$500 |
| Neon compute and database storage | R$150 |
| Base SMTP, monitoring, backups, domain amortization | R$100 |
| Shared infrastructure contingency | R$50 |
| **Total shared infrastructure** | **R$800/month** |

The VPS budget uses the owner's figure; ancillary figures are allowances, not supplier quotes. R2 tenant storage is counted below,
not twice in this table. This budget assumes an early cohort fits the shared infrastructure;
benchmark and increase it when CPU, database, queues, or backup requirements grow.

### Direct monthly cost at full quota consumption

| Direct expense | Starter | Business | Growth |
|---|---:|---:|---:|
| AI units × R$0.40 | R$24.00 | R$80.00 | R$240.00 |
| Verification bundles × R$0.05 | R$5.00 | R$15.00 | R$40.00 |
| Full storage × R$0.15 | R$2.25 | R$7.50 | R$22.50 |
| Support labor provision | R$15.00 | R$30.00 | R$60.00 |
| Evidence submission, API traffic, email and operations reserve | R$8.00 | R$15.00 | R$30.00 |
| **Direct cost** | **R$54.25** | **R$147.50** | **R$392.50** |

Support provisions correspond to 15/30/60 minutes at an assumed R$60/hour, not different support
entitlements. If onboarding or support uses more time, replace the provision with observed cost.
The evidence reserve is not a confirmed DED fee. Paid anchoring, paid registry sources, OCR,
embedding/RAG expansion, higher API traffic, or vendor minimum commitments can invalidate these
figures. Cost those features before general release while preserving feature parity.

## 5. Sustainability and sensitivity

Reserve a combined **10% of gross receipts** for payment charges and taxes as a modeling input,
not a statement of the company's tax rate. Replace it with the applicable accountant-confirmed
rate and contracted payment fees before invoicing.

```text
contribution = collected monthly-equivalent price × (1 - deduction rate) - direct cost
operating result = sum(contributions) - shared infrastructure - other fixed operating costs
minimum price = (direct cost + allocated fixed costs) / (1 - deduction rate - target margin)
```

| At full included usage | Starter | Business | Growth |
|---|---:|---:|---:|
| Monthly contribution before shared fixed costs | R$79.85 | R$166.60 | R$326.60 |
| Contribution / monthly price | 53.6% | 47.7% | 40.9% |
| Annual-plan contribution per equivalent month | R$66.44 | R$135.19 | R$254.69 |
| Monthly contribution if AI unit cost doubles to R$0.80 | R$55.85 | R$86.60 | R$86.60 |
| Annual-plan contribution if AI unit cost doubles to R$0.80 | R$42.44 | R$55.19 | R$14.69 |
| Monthly-only customers to cover R$800 infrastructure | 11 | 5 | 3 |

The last row assumes every customer buys the same plan. With 6 Starter, 3 Business, and 1 Growth
monthly subscriptions, revenue is R$2,740, contribution is R$1,305.50, and R$505.50 remains after
R$800 infrastructure. This is **not net profit**: founder compensation, development, acquisition,
accounting, legal work, and other unbudgeted costs still need funding. With R$5,000 additional
fixed expenses, the same average mix requires approximately 45 monthly customers to cover
R$5,800, provided infrastructure and unit costs still hold at that scale.

At full usage, doubling AI cost leaves the annual Growth plan only R$14.69/month before
shared infrastructure and other fixed expenses. That stress case is not a sustainable target.
The 10% annual discount remains a proposal contingent on measured paid-model costs; do not
combine it with further promotions or expand AI quotas again without re-costing. Existing
prepaid agreements must retain their contracted terms.

If costs exceed assumptions, first measure per-tenant provider tokens, paid-source requests,
storage, evidence operations, and support. Recalculate new offers and future renewals; never
silently reduce quality or change a prepaid customer's contracted allowance.

## 6. Limits, upgrades, and optional capacity

Send usage alerts at 70%, 90%, and 100%. At a cap, pause only new operations requiring that
resource; preserve access to existing records, audit history, exports, and completed proofs
(BR-ORG-003). Completion of an already reserved job, including its evidence creation, must not
be stranded halfway by another quota. Preserve human review of existing decisions.

No automatic overage invoice. Offer an upgrade or a clearly priced, explicitly purchased
capacity pack. Suggested initial packs, subject to the same cost validation:

| Optional pack | Price | Direct cost assumption |
|---|---:|---:|
| 10 additional contract analyses + 20 AI units, current cycle | R$49 | R$8 AI plus operations reserve |
| 100 additional supplier verification bundles, current cycle | R$29 | R$5 source provision plus operations reserve |
| Additional retained storage, 10 GB/month | R$19/month | R$1.50 storage plus operations reserve |

Packs do not bypass active-user, supplier-stock, or API caps. A higher volume requirement across
several dimensions should trigger a plan comparison, not an accumulation of confusing add-ons.
Recurring storage capacity requires explicit consent. Cancelling it follows the same no-deletion
rule as downgrade. Existing evidence retention follows the agreed retention policy; never promise
unlimited free retention after subscription cancellation.

Upgrades charge a disclosed prorated difference and add prorated allowance differences without
resetting consumed usage. Downgrades take effect at renewal; over-quota stock remains readable
and new growth pauses until within quota. Failed/cancelled job reservations are released
idempotently. Payment lifecycle remains governed by ADR-014, not automatic billing inferred from
this document.

## 7. Implementation and validation handoff

This is a completed commercial proposal; runtime rollout is separate work. Before describing
these limits as enforced or selling them as an automated subscription:

1. Confirm actual invoices, provider agreements, taxes, and the paid AI quality/cost benchmark.
   Measure full-quota and doubled-cost scenarios rather than assuming average light use.
2. Version the catalog with BRL integer-cent prices, entitlements, quota definitions, and cycle
   rules. Bind a subscription to a catalog version; preserve existing customer terms.
3. Replace placeholder plan limits through an explicit organization migration. Organizations
   store their own limit columns, so changing `PLAN_LIMITS` alone is insufficient. Replace
   Enterprise unlimited values with contract-specific finite allowances.
4. Add counters and atomic reservations for contract jobs, AI/token budgets, supplier checks,
   policy stock, storage, and external API usage. Enforce before provider calls and uploads,
   across both UI and API. Existing user-limit checks are not proof of complete quota enforcement.
5. Add usage visibility, trial lifecycle, upgrade/downgrade behavior, and idempotency/refunds;
   validate tenant isolation and concurrent quota exhaustion. Update customer-facing pricing
   consistently across supported locales once these launch conditions are satisfied.
6. Pilot with the first 10–20 organizations and review after 30–60 days: actual per-plan cost,
   support minutes, conversion, over-quota frequency, and willingness to pay. Monitor free-trial
   acquisition cost separately. Revisit discounts if heavy annual usage erodes contribution.

This policy supersedes earlier suggestions of exclusive API access, SSO, workflow sophistication,
or paid standard packs by tier in business-model and expansion discussions. It does not accelerate
the roadmap or make unreleased features available.
