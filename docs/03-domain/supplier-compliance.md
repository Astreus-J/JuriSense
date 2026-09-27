# Supplier Compliance

This document specifies the full behavioral lifecycle of supplier verification in the **Suppliers**
bounded context: what data is checked, which entities are involved, how a check runs end to end,
how its results feed the Policy Engine, and when a supplier gets re-checked. See
`docs/03-domain/domain-model.md` for the entity definitions this document elaborates
(`Supplier`, `SupplierProfile`, `SupplierCheck`), `docs/03-domain/business-rules.md` for the
invariants (`BR-SUP-*`), and `docs/03-domain/policy-engine.md` for how the resulting data enters
rule evaluation.

## Purpose

Before a company signs anything with a supplier, JuriSense Gate answers a narrower but
foundational question first: **"Is this a real, legally compliant, non-sanctioned entity we are
allowed to do business with?"** This is the Supplier Intelligence half of the product (see
`docs/00-project/overview.md` → "Supplier Intelligence"), and it runs independently of — and
before — contract-level analysis (`docs/03-domain/contract-compliance.md`), because a sanctioned
or non-existent supplier makes contract terms irrelevant.

## What is checked

A `SupplierCheck` verifies five categories of data. Every category maps to one or more fields on
`SupplierProfile` and, ultimately, to fields in the normalized evaluation context that
`docs/03-domain/policy-engine.md` describes.

1. **Registry status** — is the `tax_id` (CNPJ in the Brazil pack) valid, active, and not
   suspended/cancelled with the tax authority (Receita Federal)? A supplier whose registry status
   is anything other than "active" is a hard signal, surfaced to Policy & Compliance as
   `supplier.registry_status` (e.g. `active`, `suspended`, `cancelled`, `unknown`).
2. **Corporate structure** — legal nature (LTDA, S.A., MEI, etc.), incorporation date, capital
   structure, and — where the source exposes it — parent/subsidiary or group relationships.
   Corporate structure matters for two reasons the platform cares about: (a) shell-company /
   newly-incorporated-entity risk (an entity incorporated days before a large contract is a known
   fraud pattern), and (b) properly attributing sanctions hits that are registered against a
   *responsible party* rather than the contracting entity itself (see "Responsible parties" below).
3. **Responsible parties** — the individuals/entities listed as legal representatives, partners, or
   ultimate beneficial owners. These are checked against sanctions/restriction lists in their own
   right, not just the supplier's own `tax_id` — a common evasion pattern is operating a clean
   shell entity whose actual controller is individually sanctioned or debarred.
4. **CNAE / declared business activity and address** — does the supplier's declared economic
   activity code (CNAE in Brazil, or jurisdiction equivalent) plausibly match what the organization
   is contracting them for, and is the registered address consistent with an operating business
   (not, e.g., a residential address for a claimed large-scale logistics operation)? This is a
   heuristic signal surfaced as `supplier.activity_mismatch` (boolean) and `supplier.address_flag`
   (enum), not an automatic block — it feeds a `Risk` finding and a `REVIEW`-tier rule, never a
   `BLOCK`-tier rule on its own.
5. **Sanctions / restriction lists** — see the dedicated section below; this is the highest-severity
   check category and the only one wired to a `BLOCK`-tier rule in the default rule pack.

## Entities involved

- **`Supplier`** (`Suppliers` context) — the durable record of the third party. Its `status`
  (`prospect/under_review/approved/blocked/inactive`) reflects the aggregate outcome of its check
  history, not any single check in isolation.
- **`SupplierProfile`** — the current, normalized, materialized view of the supplier's
  registry/corporate data. There is exactly one active `SupplierProfile` per `Supplier` at any
  time; it is **replaced**, never mutated in place, whenever a `SupplierCheck` completes
  successfully (per its `domain-model.md` lifecycle: "replaced (not mutated) on every successful
  re-check"). This replace-not-mutate behavior is what lets the platform show "what did we believe
  about this supplier on the day we approved them?" months later, by pairing the `Decision`'s
  timestamp with the `SupplierCheck` that was current at that time (see
  `docs/03-domain/evidence.md`).
- **`SupplierCheck`** — one immutable, point-in-time verification run. Every check, successful or
  failed, is retained forever (`BR-SUP-004`'s "cannot be silently ignored" guarantee depends on this
  — a sanctions hit can never simply disappear because a later check didn't repeat it without an
  explicit record of why).

## Check lifecycle, end to end

```
Supplier created (or manual re-check requested)
    ↓
SupplierCheck: started
    ↓
Query configured external sources (see "Data sources" below)
    ↓
Aggregate raw_results from each source
    ↓
SupplierCheck: completed (or failed, e.g. source timeout/unavailable)
    ↓
On completed: build new SupplierProfile from raw_results (replaces prior profile)
    ↓
Emit supplier.check.completed → supplier.profile_updated
    ↓
Normalized fields (supplier.sanctions_hit, supplier.registry_status, ...) become available
to Policy & Compliance's evaluation context
    ↓
Any open ComplianceReview / new Contract activity for this Supplier can now evaluate against
the fresh profile
```

Step-by-step:

1. **Trigger.** A check starts on `Supplier` creation (`SUP-002`) or on manual re-check request by
   an authorized user. See "Re-check triggers and cadence" below for the additional automatic
   triggers.
2. **`SupplierCheck.started`.** A new `SupplierCheck` record is created with `status=started`,
   `started_at` set, and `sources_consulted` populated with the list of sources this check will
   query (not yet their results).
3. **Source querying.** Each configured source (registry, sanctions lists, and any
   organization-specific internal list) is queried independently; partial source failure does not
   automatically fail the whole check — a source that times out is recorded as
   `source_status=unavailable` inside `raw_results`, and the check can still `complete` with a
   caveat flag if at least the mandatory sources (registry + sanctions) responded. If a mandatory
   source is unavailable, the check moves to `failed` instead, because an incomplete sanctions
   check must never silently look like a clean one.
4. **`SupplierCheck.completed` (or `failed`).** On success, `completed_at` is set and the record
   becomes immutable (`domain-model.md`: "immutable once `completed`"). On failure, no
   `SupplierProfile` is produced or replaced — the prior profile (if any) remains current, and the
   `Supplier` cannot progress past `under_review` while its most recent check is a failure.
5. **`SupplierProfile` materialization.** `Suppliers`' application layer normalizes `raw_results`
   into the profile's typed fields (registry status, corporate structure, responsible parties,
   CNAE/address, and a boolean+detail sanctions result). This normalization step is what
   `docs/03-domain/policy-engine.md`'s evaluation-context section means by "current `SupplierProfile`"
   feeding the flat, typed context (`supplier.sanctions_hit`, etc.) — `Policy & Compliance` never
   parses `raw_results` directly.
6. **Downstream propagation.** `supplier.profile_updated` signals that any pending or future
   `ComplianceReview` referencing this supplier should use the new profile. A profile update after
   a `Decision` has already been issued does **not** retroactively change that `Decision`
   (`BR-DEC-002`); instead it is one of the conditions that can trigger
   `compliance.review_required` (`BR-DEC-004`) if the change is material (most notably: a new
   sanctions hit on a previously-approved supplier).

## How a sanctions hit propagates into policy evaluation

A positive hit on any configured sanctions/restriction list is the single highest-severity signal
Supplier Intelligence produces, and it is wired directly into the default rule pack via rule
`SANC-001` (`docs/03-domain/policy-engine.md`):

```yaml
rule:
  id: SANC-001
  name: Supplier on a Sanctions List
when:
  supplier.sanctions_hit: true
result:
  status: BLOCK
severity: critical
approver_role: null   # BLOCK has no approver — not overridable without an explicit override action
```

The propagation path is deliberate and mirrors `BR-SUP-004`:

1. `SupplierCheck` records a hit against the supplier's `tax_id` **or** any of its responsible
   parties in `raw_results`.
2. `SupplierProfile` normalizes this into `supplier.sanctions_hit = true` (plus a detail record of
   which list, which entity/individual, and when the list was last updated — retained for evidence,
   see `docs/03-domain/evidence.md`).
3. Any `ComplianceReview` that builds its evaluation context after this point picks up
   `supplier.sanctions_hit = true`, `SANC-001` fires, and — per the aggregation algorithm
   (`ADR-010`, `BR-CMP-002`) — **any `BLOCK` wins**, regardless of what every other rule concluded.
   The resulting `ComplianceReview`/`Decision` is `BLOCK` even if every contract-term rule would
   otherwise have passed.
4. Per `BR-SUP-004`, this cannot be silently bypassed by the workflow: because `SANC-001` has
   `approver_role: null`, it is not routed to an `ApprovalRequest` at all (there is nothing to
   approve — see `docs/03-domain/approvals.md`) and the only path past it is an explicit,
   justified `Decision` override (`BR-DEC-003`, `ADR-010` §3), which itself emits a
   `decision.overridden` audit event and never deletes the original `RuleEvaluation`.
5. Per `BR-SUP-003`, a `Supplier` cannot move to `approved` status while it carries an open
   (unresolved-by-override) sanctions flag newer than its last `completed` `SupplierCheck` — the
   `Supplier`-level status and the `ComplianceReview`-level decision are kept consistent by this
   rule.

A sanctions hit found on a **responsible party** rather than the contracting entity itself is
normalized the same way (`supplier.sanctions_hit = true`, with the detail record naming the
individual/entity actually listed) — the DSL does not need a separate rule for this case, because
the normalization step in `Suppliers` is what absorbs entity-vs-representative complexity before
`Policy & Compliance` ever sees it (consistent with the context boundary: AI/verification produces
facts, Policy & Compliance evaluates them).

## Re-check triggers and cadence

Automatic and manual triggers for a new `SupplierCheck`:

- **Supplier creation** (`SUP-002`) — always triggers an initial check.
- **Manual re-check** — any authorized user can request one at any time (e.g., before a renewal).
- **Contract-linked re-check** — starting a new `Contract` or `ContractVersion` for a `Supplier`
  whose most recent `SupplierCheck` is older than the periodic cadence (below) triggers a fresh
  check before the associated `ComplianceReview` runs, so decisions are never made against stale
  supplier data by accident.
- **Periodic/scheduled re-check** —

Status: TBD / Current preferred option: a fixed periodic cadence (candidate default: every 90 days
for `approved` suppliers, with a shorter cadence such as 30 days for suppliers already carrying a
non-blocking `Risk` finding) plus an event-driven re-check triggered by sanctions-list update
notifications where the data source supports them / Why undecided: the right cadence is a function
of plan tier (cost of running checks against external/paid sources), customer risk appetite, and
the actual update frequency and change-notification capabilities of the CEIS/CNEP/CEPIM datasets,
none of which have been validated with a real customer or a real integration spike yet / Resolution:
finalize during the Phase-2 Brazil-sources integration spike, informed by `docs/02-business/
pricing-strategy.md` plan-limit design and the actual polling/update cadence the chosen integration
method exposes / Decision artifact: an ADR to be written once the Phase-2 spike concludes (see
"Data sources" below for the same spike dependency).

## Data sources

| Category | Source (Brazil pack) | What it confirms |
|---|---|---|
| Registry status | CNPJ registry (Receita Federal) | Legal existence, active/suspended/cancelled status, registered corporate name, legal nature, incorporation date |
| Corporate structure / CNAE / address | CNPJ registry (Receita Federal) — same source, additional fields | Declared economic activity (CNAE), registered address, partners/legal representatives listed on the registry record |
| Sanctions / restriction — administrative sanctions | CEIS (Cadastro de Empresas Inidôneas e Suspensas) via Portal da Transparência open data | Entities barred from contracting with public administration due to administrative sanction |
| Sanctions / restriction — impediment for grants/transfers | CNEP (Cadastro Nacional de Empresas Punidas) via Portal da Transparência open data | Entities punished under the Anti-Corruption Law (Law 12,846/2013) |
| Sanctions / restriction — non-compliant entities | CEPIM (Cadastro de Entidades Privadas Sem Fins Lucrativos Impedidas) via Portal da Transparência open data | Non-profit entities barred from receiving public funds/transfers |
| Internal history | JuriSense internal `SupplierCheck` history for the organization | Prior findings, prior overrides, prior exceptions on the same supplier |

CEIS, CNEP, and CEPIM are real, confirmed-existing official Brazilian government data sources,
published as open data through Portal da Transparência. What is **not** yet decided is the exact
integration mechanism:

Status: TBD / Current preferred option: direct API integration against Portal da Transparência's
published API endpoints where available, falling back to scheduled batch download + local indexing
of the published open-data files (CSV/JSON dumps) for lists that are not exposed as a queryable API
/ Why undecided: Portal da Transparência's API coverage, rate limits, and update latency per
dataset have not been technically validated against JuriSense Gate's real-time check-on-demand
requirement (`SUP-002`) — a batch-file approach is safer for completeness but introduces a
freshness lag that direct API access would avoid / Resolution: a dedicated Phase-2 integration
spike will validate API availability/rate limits/latency per dataset and choose direct-API vs.
batch-file (or a hybrid: API for CNPJ registry lookups, batch indexing for CEIS/CNEP/CEPIM, which
tend to be published as periodic open-data extracts) per source / Decision artifact: an ADR to be
written once the Phase-2 spike concludes.

## Relationship to other domain documents

- The normalized fields this document describes (`supplier.sanctions_hit`,
  `supplier.registry_status`, etc.) are consumed exactly as specified in
  `docs/03-domain/policy-engine.md`'s "Evaluation context & input normalization" section.
- `BR-SUP-001` through `BR-SUP-004` (`docs/03-domain/business-rules.md`) are the authoritative
  invariants for everything described here; this document is the behavioral elaboration of those
  rules, not a replacement for them.
- What happens after a `SANC-001` (or any) `BLOCK`/`REVIEW` outcome reaches the workflow layer is
  specified in `docs/03-domain/approvals.md`.
- How a `SupplierCheck`'s `raw_results` and the resulting `RuleEvaluation` become durable,
  hash-anchored evidence is specified in `docs/03-domain/evidence.md`.
