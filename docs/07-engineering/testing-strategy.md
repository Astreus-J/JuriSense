# Testing Strategy

The test pyramid for JuriSense Gate, extending the existing `Accounts` testing pattern
(pytest + httpx `ASGITransport`, in-memory SQLite + fakeredis, ~700 lines of passing tests per
ADR-001) across all 8 bounded contexts, plus the test categories specific to a compliance-decision
product: policy fixtures, AI evaluation, and blockchain anchoring.

## The pyramid

```
                    ▲
                   /  \        Security tests (cross-tenant, auth, rate limiting)
                  /    \       — mandatory per sprint, ADR-003/ADR-016
                 /------\
                /        \     AI evaluation tests (extraction accuracy, guardrails)
               /  smaller \    — scheduled, not per-commit (docs/05-ai/evaluation.md)
              /   number,  \
             /  higher cost \  Contract tests (external sources, AI providers, anchoring)
            /----------------\ — recorded fixtures, no live calls in CI
           /                  \
          /   Integration      \  pytest + httpx ASGITransport, one FastAPI app,
         /    tests             \ real routing/dependency-injection, fake I/O
        /------------------------\
       /                          \
      /       Unit tests           \  domain + application layer, per bounded context,
     /                              \ no I/O, fastest, most numerous
    /--------------------------------\
```

## Unit tests (per bounded context)

- Target the `domain/` and `application/` layers in isolation — no database, no Redis, no network.
  A domain entity's invariant (e.g. `PolicyVersion` immutability, `ADR-010`'s aggregation function)
  is tested as a pure function/object test, not through an HTTP round-trip.
- Live under `backend/tests/<context>/test_<unit>.py`, mirroring `backend/tests/accounts/` today.
- The `ADR-010` aggregation algorithm (`any BLOCK → BLOCK`, else `any REVIEW → REVIEW`, else
  `APPROVE`) is a prime unit-test target precisely because it is "the single most important
  behavioral specification in the product" (ADR-010's own words) — it is tested directly against
  lists of `RuleEvaluation` outcomes, independent of how those evaluations were produced.
- Application-layer services are tested against **fake ports** (an in-memory repository
  implementation, a fake email sender — exactly the `CapturingEmailSender` pattern already in
  `backend/tests/conftest.py`), not real infrastructure — that's what integration tests are for.

## Integration tests (pytest + httpx ASGITransport)

- The existing, proven pattern: `httpx.AsyncClient(transport=httpx.ASGITransport(app=app))` drives
  the real FastAPI app in-process, with `app.dependency_overrides` swapping in an in-memory SQLite
  engine (`aiosqlite`, `StaticPool`) and `FakeAsyncRedis`, exactly as `backend/tests/conftest.py`
  already does. Every new bounded context reuses this same `client` fixture — do not build a
  parallel test-client setup per context.
- These tests exercise real routing, real dependency injection (`Depends`), real Pydantic
  validation, and real (SQLite-backed) repository queries — the layer where the four-layer
  architecture's seams (`api` → `application` → `infrastructure`) are most likely to have a bug a
  pure unit test would miss.
- One integration-test module per major endpoint group, matching the existing
  `test_auth.py`/`test_users_crud.py`/`test_invites.py`/`test_password_reset.py` split — e.g.
  `test_suppliers_crud.py`, `test_supplier_checks.py`, `test_compliance_check.py`,
  `test_decisions.py`.
- SQLite is an accepted stand-in for Postgres in these tests because the ORM layer is what's under
  test, not Postgres-specific behavior (JSON columns, `pgvector` operators, the `REVOKE UPDATE`
  grants from `docs/07-engineering/database-standards.md`). Anything that depends on genuinely
  Postgres-specific behavior needs a **separate** test tier (below), not a workaround inside the
  SQLite-backed integration suite.

## Postgres-specific / DB-permission tests

- The append-only enforcement described in `docs/07-engineering/database-standards.md` (no `UPDATE`/
  `DELETE` grant on versioned and audit tables) cannot be exercised against SQLite — it needs a real
  Postgres connection with the actual restricted application role.
- These run against a disposable Postgres instance (a CI service container, or a dedicated Neon
  branch/dev database — not the shared external dev database), and assert that an `UPDATE` against
  `policy_versions`, `rule_evaluations`, `decisions`, `evidence`, or `audit_events` using the
  application's own restricted role raises a Postgres permission error.
- Runs less frequently than the SQLite integration suite (e.g. on PRs touching `alembic/` or
  `database-standards.md`-relevant tables, and nightly) rather than on every commit, given the extra
  infrastructure it requires — see `docs/07-engineering/ci-cd.md`.

## Contract tests for external integrations

External dependencies — Brazilian company/sanctions sources (CEIS/CNEP/CEPIM), AI providers
(OpenAI, Anthropic), and the `AnchoringProvider` — are never called live in CI:

- **CNPJ/sanctions sources**: recorded HTTP fixtures (request/response pairs captured once against
  the real source, replayed thereafter) per adapter in `app/suppliers/infrastructure/`. A contract
  test asserts the adapter correctly parses a known-good recorded response and correctly raises the
  adapter's own error type on a known-bad one (source down, malformed response, rate-limited). Fixture
  refresh is a scheduled, deliberate action (not automatic), since these sources can change shape
  without notice — a stale fixture silently passing while production breaks is the failure mode this
  guards against, so fixture staleness itself is periodically reviewed.
- **AI providers**: the `AI Services` context's contract tests replay recorded OpenAI/Anthropic
  responses against fixed input, verifying the adapter enforces structured-output parsing and
  provenance attachment correctly (ADR-005) — they do not evaluate extraction *quality*, that is the
  AI evaluation tier below. Never make a live LLM API call from the default CI test run: it is
  slow, costs money, and is non-deterministic — exactly the failure mode fixture-replay avoids.
- **Blockchain anchoring**: see the dedicated section below.

## Policy Engine fixture-based tests

Every `Policy` ships with fixture cases — a normalized evaluation context plus an expected
`RuleEvaluation` outcome — exactly as specified in `docs/03-domain/policy-engine.md`'s "Policy
testing" section (a Phase 4/5 backlog item, not optional hardening). Concretely:

- Fixtures live alongside each seeded/example policy (e.g.
  `backend/tests/policies/fixtures/lgpd_dpa_policy.yaml` + a matching
  `lgpd_dpa_policy.cases.json` of `{context, expected_outcome}` pairs) and run in CI as an ordinary
  pytest parametrized test — this is functionally "unit tests for business rules," run on every
  commit that touches the Policy Engine or its rule DSL.
- A `PolicyVersion` draft cannot be published (in the target implementation) until its fixture suite
  passes — mirroring the "critical/high findings block the next sprint" discipline (ADR-016) applied
  to policy authoring itself.
- Rule-priority and conflict-handling behavior (`docs/03-domain/policy-engine.md`: BLOCK always
  wins, highest-severity role wins among REVIEW rules) has its own dedicated fixture cases —
  specifically constructed multi-rule-trigger scenarios, not just single-rule cases — because that
  logic is where an off-by-one or wrong-comparison bug is most likely and least visible in normal
  testing.
- Simulation/dry-run mode (`docs/03-domain/policy-engine.md`) is tested by asserting it produces the
  same `RuleEvaluation` outcomes as a real run against the same input, while asserting it emits **no**
  domain events and creates **no** `ComplianceReview`/`Decision` rows — both properties matter and are
  tested explicitly, not just "it runs without error."

## AI evaluation tests

Extraction accuracy and guardrail behavior are evaluated separately from the contract tests above,
per the methodology in `docs/05-ai/evaluation.md`:

- A held-out set of labeled contracts/supplier documents with known-correct extracted fields is
  scored for accuracy (precision/recall per field type: liability terms, DPA presence, contract
  value, etc.) — this is model-output-quality evaluation, not adapter-correctness testing.
- Guardrail tests (prompt-injection resistance, refusal to let retrieved document content be treated
  as an instruction — cross-referenced in `docs/07-engineering/security.md` and
  `docs/05-ai/guardrails.md`) are part of this suite, using adversarial fixture documents crafted to
  attempt instruction injection via clause text.
- This suite is **not** run on every commit — it is comparatively slow and costs real API spend even
  against recorded/replayed cases where full end-to-end model calls are intentionally exercised. It
  runs on a schedule (e.g. nightly) and as a gated, explicitly-triggered check before a change to
  prompts, extraction schemas, or model/provider selection ships — see `docs/07-engineering/ci-cd.md`'s
  AI eval stage.

## Smart-contract / anchoring-provider tests

- The `AnchoringProvider` interface (`submit_hash`, `get_proof`, `verify` — ADR-007) is tested
  against a **local mock implementation** for the default test run (fast, free, deterministic), and
  against the real chosen provider's **testnet** (Constellation testnet, or an EVM L2 testnet such as
  Base Sepolia/Polygon Amoy, per the ADR-007 spike outcome) in a slower, less-frequent tier — not
  every commit, since testnet calls are slow and occasionally flaky for reasons outside this
  codebase's control.
- The core property under test either way: `verify(evidence_hash, get_proof(submit_hash(evidence_hash)))
  == True`, and — just as important — `verify` returns `False` for a hash that was never submitted or
  that doesn't match the anchored proof (a false-positive `verify` result would be a critical defect
  given what the public `/verify/{hash}` endpoint promises).
- `EvidencePackage.merkle_root` recomputation (`BR-EVD-001`) is tested independent of any specific
  `AnchoringProvider` — it's a pure function over the `Evidence` set and belongs in the unit tier, not
  the anchoring-provider tier.

## Security tests (mandatory, every sprint)

- **The cross-tenant-access test is mandatory for every new bounded context**, per ADR-003 and
  ADR-016, continuing the practice already established for `Accounts`
  (`docs/auditorias/sprint-02.md`: "listing/detail/edit/deactivate always filtered by the admin's
  organization; a user from another org returns 404"). Concretely: for every tenant-owned resource,
  a test creates the resource under Organization A, authenticates as a user in Organization B, and
  asserts the read/write attempt returns `404` (never `403`, never the resource's data) — matching
  the no-enumeration convention in `docs/07-engineering/coding-standards.md` and
  `docs/07-engineering/security.md`.
- Authorization tests verify the role/module/action grid (`ADR-003`, `ADR-012`) for every new
  endpoint — at minimum, one test asserting a role *without* the needed grant gets `403`, and one
  asserting the correct role succeeds, matching the existing `CurrentAdmin` test pattern.
- Enumeration-resistance tests (identical response shape/status regardless of whether a resource
  exists, per the `sprint-01.md`/`sprint-02.md` MED-001/MED-002 findings) are written for every new
  "does X exist" surface, not only auth endpoints.
- These security tests are part of the ordinary test suite (they run every commit) — the *audit* is
  the separate, periodic, broader review (`docs/07-engineering/security.md`'s
  security-audit-as-sprint-gate section); the tests are what make regressions in already-audited
  behavior impossible to merge silently.

## What runs where (summary)

| Tier | Runs on every commit? | Needs external services? |
|---|---|---|
| Unit | Yes | No |
| Integration (SQLite/fakeredis) | Yes | No |
| Security (cross-tenant, authz, enumeration) | Yes | No |
| Postgres-permission tests | On DB/migration-touching PRs + nightly | Disposable Postgres |
| Contract tests (external sources, AI providers) | Yes, against recorded fixtures | No (fixtures only) |
| Policy Engine fixtures | Yes | No |
| AI evaluation suite | Scheduled / gated on prompt-relevant changes | Yes (real API calls) |
| Anchoring-provider mock | Yes | No |
| Anchoring-provider testnet | Scheduled / gated | Yes (testnet) |

Full CI wiring for each row is specified in `docs/07-engineering/ci-cd.md`.
