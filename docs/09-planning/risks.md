# Risks

Concrete, named project risks with likelihood, impact, and mitigation. Ordered roughly by how much
they threaten the Hackathon Cut (`roadmap.md` Phase 8, judging window 2026-11-05 to 2026-12-05).
Cross-referenced from `roadmap.md` (per-phase risks) and `milestones.md` (schedule risk). This is
the consolidated register; per-phase entries in `roadmap.md` are the same risks in their local
context, not a separate list.

## 1. Hackathon timeline risk

- **Description**: today is 2026-09-27; the hackathon judging window opens 2026-11-05 — roughly
  **5.6 weeks** away. Eight sequential-spine phases (0 through 8, per `dependencies.md`) must land
  in that window, including one context-migration effort (Phase 0), two AI/external-integration
  builds (Phases 2–3), one open technical spike with an explicitly "Proposed" ADR status
  (`ADR-004`, Phase 4), and one more open technical spike with an explicitly "Proposed" ADR status
  (`ADR-007`, Phase 8).
- **Likelihood**: high. Two of eight phases depend on the outcome of a spike whose duration cannot
  be known in advance; `milestones.md` already flags M3 and M4 as `TBD`-timed for this reason.
- **Impact**: critical. Missing the judging window entirely forfeits the hackathon submission,
  which `docs/00-project/overview.md` treats as "the first public milestone of a real commercial
  product," not a disposable deadline.
- **Mitigation**: the explicit Hackathon Cut line after Phase 8 exists specifically to bound scope
  (see risk 5, scope-creep); Phase 2/3 parallelization (`dependencies.md`) recovers real calendar
  time; both open spikes (`ADR-004`, `ADR-007`) have a documented fallback (see risks 3 and 4 below)
  so a "spike goes badly" outcome degrades the demo rather than blocking it entirely; re-forecast
  M3/M4 immediately once Phase 0–1 actual velocity is known, per `milestones.md`.

## 2. AI extraction accuracy risk

- **Description**: Phase 3's AI Services extraction pipeline must reliably turn real Brazilian
  contract PDFs/DOCX into structured, page/span-cited fields (`CON-003`, `CON-004`,
  `docs/05-ai/structured-extraction.md`). Real contracts vary wildly in formatting, may be
  scanned images requiring OCR, and use inconsistent legal phrasing for the same clause type
  (liability, DPA, termination, etc.).
- **Likelihood**: medium-high. This is a known-hard problem class even with modern LLMs; no
  extraction-accuracy baseline exists yet for this specific document domain.
- **Impact**: high — inaccurate extraction directly corrupts the Policy Engine's evaluation
  context (`docs/03-domain/policy-engine.md`), which means a wrong `APPROVE`/`REVIEW`/`BLOCK`
  outcome for a real contract. This is the product's core trust promise, so this risk is not
  cosmetic.
- **Mitigation**: `CON-005`/`BR-CON-003` already build a minimum-confidence human-confirmation gate
  into the domain model — low-confidence fields never silently flow into a compliance decision;
  `ADR-005`'s multi-provider fallback (OpenAI/Anthropic) reduces single-provider failure modes but
  does **not** address systematic accuracy gaps, so it is a partial mitigation only; for the
  Hackathon Cut demo specifically, curate a small set of known-good demo contracts alongside
  whatever real/messy documents are used for stress-testing, so a demo-day accuracy dip on an edge
  case does not sink the whole presentation.

## 3. Policy engine expressiveness risk — RESOLVED 2026-09-30

- **Description** (as originally written, kept for the record): `ADR-004` was "Proposed — pending
  prototype/benchmark," not "Accepted." The Phase 4 spike could reveal that `cel-python` (or
  JSONLogic) cannot cleanly express the nested, cross-entity conditions the Rule DSL promises
  (`docs/03-domain/policy-engine.md`), or that hiding CEL's raw syntax from non-technical policy
  authors is harder in practice than the ADR assumes.
- **Resolution**: the Phase 4 spike (EPIC-4 STORY #55) ran, built a working YAML-to-CEL compiler and
  rule-execution engine against all 5 worked-example rules plus real Supplier/Contract evidence end
  to end, and found CEL works cleanly for this grammar — the one real wrinkle (CEL's `has()` macro
  not guarding an explicitly-`null` field, only a genuinely-absent one) has a documented, tested fix
  (the context builder never emits `null` leaves; a two-phase presence/condition CEL compilation
  distinguishes `NOT_APPLICABLE` from `PASS`). `ADR-004`'s status is now **Accepted** — see its
  "Spike findings" section for the full live-verified detail (real performance numbers, the
  null-handling strategy, the bare-field-name resolution rule). This risk no longer threatens the
  remaining sequential spine; Compliance (Phase 5) can build on a validated expression language.
- **Likelihood/impact** (historical, pre-resolution): medium likelihood, high impact if it had
  happened — see the original description above; both are moot now that the spike is done.
- **Mitigation**: the spike is scheduled early (Phase 4) rather than assumed away, specifically so
  a bad outcome is discovered with runway left to react; JSONLogic is already documented as the
  fallback compilation target if CEL proves unworkable for hand-authored rules; as a last resort if
  neither proves sufficient for the five example rules in `policy-engine.md` within the timeline, a
  narrowly-scoped, hand-rolled evaluator over the specific YAML grammar already documented (not a
  general expression language) can satisfy the Hackathon Cut demo scope while the general-purpose
  engine question is revisited post-hackathon — this would be a scope reduction, not silent, and
  would need its own ADR update if taken.

## 4. Blockchain integration risk

- **Update (2026-10-07)**: played out exactly as anticipated below, and the mitigation already
  written here is the reason it did not become a schedule problem. `ADR-007`'s spike built and
  tested a real Constellation DED adapter (low engineering effort, confirmed) but hit a real
  provisioning blocker (credentials are not self-service, tracked as Plane #198) — not an SDK or
  integration-effort failure. The fallback below is accordingly the project's **active default
  today**, not a hypothetical. See `ADR-007` and `docs/06-blockchain/anchoring-providers.md` §3 for
  the full findings.
- **Update (2026-10-15)**: both gaps this risk's mitigation left open are now closed. (1) The
  Constellation DED credentials (live-verified 2026-10-12) were switched in as the active
  `ANCHORING_PROVIDER` — the fallback below is no longer the default; verified live with a real
  anchor submitted to the actual Constellation DED API. (2) The fallback's own "publicly,
  independently verifiable" claim is now true end to end, not just locally honest: its git
  history was pushed, with explicit user authorization, to `https://github.com/Astreus-J/
  jurisense-transparency-log` (public, anonymously clonable, verified live) — see the full
  account in `app/evidence/infrastructure/anchoring/transparency_log_provider.py`'s own
  docstring. Re-pushing as new fallback anchors accumulate is a manual operational step, not
  automated.
- **Original description**: `ADR-007` is "Proposed — pending technical spike (Phase 8)." All three
  candidate `AnchoringProvider` adapters — Constellation Network, a generic EVM L2 testnet,
  ICP/Caffeine AI — are unvalidated against this codebase today, and Phase 8 is the last phase
  before the Hackathon Cut line, meaning there is minimal schedule slack left to absorb a spike
  that goes badly.
- **Likelihood**: medium-high, precisely because this risk was already anticipated when `ADR-007`
  was written (the ADR itself frames Constellation as "current preferred," not "confirmed working").
- **Impact**: critical for the blockchain-track narrative specifically, but **not** critical for the
  product's core value proposition — `docs/00-project/overview.md` is explicit that "blockchain is
  NOT the product." A missed anchor still leaves a fully functional Supplier → Contract → Policy →
  Compliance → Approval → Decision → Evidence pipeline.
- **Mitigation**: the `AnchoringProvider` interface (`submit_hash`/`get_proof`/`verify`) is designed
  so the concrete provider is swappable without touching anything above it in the stack — this is
  what makes the following fallback viable on short notice. **If no real chain integration lands in
  time, the last-resort fallback is a trivial "hash + timestamp signed by JuriSense's own key,
  published to a public, git-backed transparency log."** This fallback must be **clearly labeled in
  the product and the hackathon submission as a fallback verification mechanism, not a blockchain
  anchor** — it preserves the "publicly, independently verifiable" property the Trust Layer promises
  without misrepresenting what technology backs it. This labeling requirement is non-negotiable: an
  audit/compliance product overstating its own verifiability claim would undermine the exact trust
  property it exists to provide.

## 5. Scope-creep risk

- **Description**: with 12 defined phases and a long-term vision (`docs/00-project/overview.md`
  "Long-term vision" section: JuriSense Monitor, Contracts, Policies, Privacy, Risk, Audit, API),
  there is a real temptation to pull post-hackathon features (Integrations, Enterprise billing, SSO,
  International packs) forward "since we're already in the code," at the direct expense of Hackathon
  Cut schedule risk (risk 1).
- **Likelihood**: medium — this is a people/process risk, not a technical one, and it tends to
  increase precisely when a phase (e.g., Phase 4's spike) is going well and momentum invites
  "just one more thing."
- **Impact**: medium-high — every hour spent on Phase 9–11 scope before Phase 8 ships is an hour not
  spent de-risking the two open spikes (`ADR-004`, `ADR-007`) that actually threaten the deadline.
- **Mitigation**: the explicit Hackathon Cut line after Phase 8 in `roadmap.md` and `backlog.md` is
  the primary control — Phases 9–11 are deliberately specified at EPIC/FEATURE level only, not
  broken into sprint-ready stories, so there is nothing "shovel-ready" to accidentally start early.
  Any request to pull Phase 9+ work forward before Phase 8's exit criteria are met should be treated
  as a scope decision requiring explicit sign-off, not a default.

## 6. Legacy-code migration risk

- **Description**: Phase 0 renames roughly 2,100 lines of already-implemented, tested, and
  security-audited Portuguese/legal-domain code (`backend/app/accounts/`) into English,
  compliance-domain vocabulary — `Organizacao`→`Organization`, `Usuario`→`User`,
  `Perfil`→`Role` (with entirely new enum values per `ADR-003`), `organizacao_id`→`organization_id`,
  and removal of `oab`/`uf_oab` and their associated `OabInvalidaError`/`OabJaCadastradaError`
  exceptions (full inventory in `pivot-migration.md`). This code has ~700 lines of passing tests and
  two prior security audits (`docs/auditorias/sprint-01.md`, `sprint-02.md`) — value that a careless
  rename could silently destroy.
- **Likelihood**: medium. This is mechanical, well-understood refactoring work in principle, but the
  volume (identifiers, table names, enum values, error messages, test fixtures, Alembic migration
  history) creates real surface area for a partial rename that breaks a test silently or, worse,
  reintroduces a tenant-isolation bug that the original audits specifically caught.
- **Impact**: high if it goes wrong. `ADR-016` treats a tenant-isolation defect as "the
  highest-severity class of defect possible in this system"; a rename-introduced regression here
  would be exactly that class of bug, in code the team otherwise trusts precisely because it was
  already audited.
- **Mitigation**: Phase 0's exit criteria explicitly require every existing Accounts test to keep
  passing under the renamed schema **and** a fresh cross-tenant-access test to pass — the rename is
  not considered done on "it compiles." `ADR-016`'s sprint-end security-audit gate applies to Phase 0
  like any other sprint, with the tenant-isolation test as a mandatory checklist item, not an
  optional one. Renaming should be done as a single, reviewable, mechanical pass (not interleaved
  with new feature logic) so any regression is attributable to the rename itself, not a mixed diff.
