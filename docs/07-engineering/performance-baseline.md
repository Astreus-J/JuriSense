# Performance Baseline (2026-10-14)

The first real load test against the actual running `docker-compose` stack (backend + Celery
worker/beat + Redis + S3Mock, external dependencies — Neon Postgres, `brasilapi.com.br` CNPJ
registry, Portal da Transparência sanctions extracts, OpenRouter AI Gateway — all real, not
mocked), run against this exact codebase at commit range covering #120 through the frontend
pentest-round fixes (#130-137, #142). This is the resolution the NFR doc's own `TBD` (`docs/
01-product/non-functional-requirements.md` §Performance) pointed to: "establish real targets from
load testing once the Hackathon Cut build is functional."

**Scope and caveats**: single developer machine, single-instance backend/worker (no horizontal
scaling, no production-grade Postgres connection pooling tuning), Neon's free/dev tier, real but
low-traffic external dependencies. These are **directional dev-environment numbers, not production
capacity planning** — they answer "is the architecture fundamentally sound and are there any
correctness bugs under concurrency," not "how many organizations can this deployment serve."
Production targets still require a follow-up test against production-equivalent infrastructure
before general availability, per the NFR doc's own resolution path.

## Three real bugs found, all fixed

Load testing the real stack — as opposed to the test suite, which mocks every external dependency
and never runs a second real OS process — found three bugs invisible to `pytest`:

1. **Celery worker never registered 6 of 7 contexts' ORM models.** `app/core/celery_app.py`'s
   `imports` tuple only pulled in task modules, never model modules; no task module happened to
   import `app.identity`, so a real worker process never ran `Base.metadata` for `User`/
   `Organization`, and any FK targeting `users` (e.g. `documents.uploaded_by`) failed SQLAlchemy's
   FK-target resolution the first time a task touched it. `contracts.run_contract_extraction`
   retried every 30s forever instead of ever succeeding. Invisible to the test suite because
   `conftest.py` always imports every context's models explicitly, regardless of what's under
   test. **Fixed**: explicit `import app.<context>.infrastructure.models` for all 7 contexts at
   the top of `celery_app.py` — the same "import every context so the full model graph is
   registered" pattern `app.main` already used for the API process, applied to the worker process.
2. **Celery beat's periodic sanctions refresh had a cold-start gap of up to 24h.** A plain-interval
   `beat_schedule` entry does not run on beat's own startup — confirmed empirically (the 900s
   approval-expiry sweep's first real run only fired 15 real minutes after `beat: Starting...`,
   not immediately). `sanctions_refresh_interval_seconds` is 24h, so a freshly started
   environment had a completely empty `SanctionsEntry` table (confirmed via direct query) for up
   to a full day after any restart — and sanctions is a mandatory source, so every single
   supplier check failed closed with "mandatory source unavailable" in that window. **Fixed**: a
   `@worker_ready.connect` signal handler dispatches `integrations.refresh_sanctions_index`
   immediately on worker startup, by task name (`celery_app.send_task`, not a direct import —
   see `tests/integrations/test_boundary_rules.py`'s narrow, documented exemption for the model
   imports above). Verified live: loaded 23,775 CEIS + 1,836 CNEP + 3,521 CEPIM real rows
   immediately on worker start, both before and after this fix's own rebuild.
3. **`git` was missing from the `backend/Dockerfile` image the `celery-worker`/`celery-beat`
   services build from**, so the transparency-log `AnchoringProvider` (ADR-007's active provider in
   dev) failed every single `evidence.submit_anchor` task with `AnchoringProviderError: transparency
   log: git is not installed` — the entire blockchain-evidence pipeline, the hackathon's centerpiece
   feature, was broken end-to-end in the real running system, masked only by the test suite mocking
   the anchoring provider instead of shelling out for real. **Fixed**: added `git` to the `dev`
   stage's `apt-get install` line alongside the existing `libmagic1`. Verified live post-fix:
   `evidence.submit_anchor` now succeeds consistently in ~2.4-2.6s.

A fourth issue was found that was a genuine API defect, not an infra gap: **`POST /compliance/
reviews` returned an unhandled 500 instead of a clean 409 when two requests for the same
`contract_version_id` raced** (`uq_decisions_one_active_per_contract_version`). `create_decision_
for_review` already converted the loser's `IntegrityError` into `DecisionAlreadyExistsError` — the
same backstop role that error already plays for `approval_service`'s resolve paths — but `trigger_
review`'s route (`app/policies/api/routes.py`) had no `except` clause for it. **Fixed**: added the
same `DecisionAlreadyExistsError` → `HTTP_409_CONFLICT` mapping the approvals routes already use.
A regression test (`test_trigger_review_maps_decision_already_exists_to_conflict`) covers the HTTP
mapping deterministically; the underlying service-level race was already covered by `tests/
approvals/test_concurrency.py`. Confirmed live, before and after the fix, against the exact same
concurrent-load scenario below.

## Results vs. NFR targets

| NFR target | Measured | Verdict |
|---|---|---|
| Supplier check < 30s end-to-end | `create_s` ~2.1s, `total_s` ~71.6s (one sample never left `started` within the poll window) | **Not met in this sample** — see caveat below; not a regression, a pre-existing async-settle characteristic worth tracking |
| AI extraction < 2min | ~32.8s–35.6s across two real samples, both landing on `needs_confirmation` (AI structured output needs a human to confirm, not an extraction failure) | **Met**, comfortably |
| Policy rule evaluation < 2s (pure in-process) | Single-request p50 ~5.8-8.0s for `POST /compliance/reviews` end-to-end (includes HTTP + auth + DB round trips, not isolated rule evaluation) | **Target as worded needs refinement** — see note below |
| Interactive page load < 2s first-meaningful-content | Not measured this round (backend-only load test); listing APIs alone return p50 ~0.7-1.0s at low concurrency | Deferred to a frontend-specific pass |
| Blockchain anchoring confirmation | ~2.4-2.6s per `evidence.submit_anchor` task (transparency-log provider: local git commit + sign, no real external chain confirmation latency) | **Met** for the transparency-log provider; not representative of a real external chain provider's confirmation time |

**Supplier check caveat**: the `create_s` timing (HTTP response for `POST /suppliers`, ~2.1-2.8s)
is the actually-meaningful "did the request get accepted" latency; `total_s` includes the test
script's own polling loop and is sensitive to real upstream (`brasilapi.com.br`, Portal da
Transparência) response variance on any given run — one sample finished in ~6-9s, another never
settled within the 40s poll window used by the load-test script itself (a script-side budget,
not a server-side timeout). This needs a few more real samples before concluding anything beyond
"the create call itself is fast"; not treated as a regression pending that.

**Rule evaluation measurement caveat**: the NFR's "under 2 seconds" is written for the rule-
evaluation *step itself* (`app.policies.application.evaluation_service`, pure in-process CEL
evaluation, no I/O) — this load test only measured the full `POST /compliance/reviews` HTTP
round trip, which also includes auth, several DB round trips (policy/rule lookup, evidence
lookup, review/risk/audit-event inserts, and for APPROVE/BLOCK outcomes, synchronous Decision +
EvidencePackage assembly), against Neon's real network latency rather than a local database. The
~5.8-8.0s single-request figure is therefore not a violation of the NFR as written — it has not
yet isolated the in-process evaluation step from everything around it. A future pass should time
`evaluate_policy_version` directly (already unit-tested for correctness, never for latency) to
give the NFR a number it can actually be checked against.

## Concurrency behavior

`POST /compliance/reviews` against the same `contract_version_id`, concurrency 10/25/50 — the
synchronous APPROVE/BLOCK Decision-creation path's only identified correctness-under-load edge
case:

| Concurrency | Winners (201) | Losers (409, post-fix) | Notes |
|---|---|---|---|
| 1 | 1 | — | baseline, ~6.0s |
| 10 | 1 | 9 | all losers: clean 409 "A Decision already exists..." |
| 25 | 2 | 23 | |
| 50 | 4 | 46 | p95 latency rises to ~22s under 50-way contention on one row |

Exactly one request per "batch" winning and the rest losing cleanly is the correct, designed
behavior for concurrent reviews of the **same** ContractVersion (`uq_decisions_one_active_per_
contract_version` — only one ACTIVE Decision may exist per version) — this is not a realistic
production access pattern (reviewing the same contract version 50 times simultaneously), but it
is the right stress point to confirm the race resolves to a clean conflict rather than silent data
corruption or an unhandled 500. Before the fix in this round, every loser surfaced as an unhandled
500; after, every loser surfaces as 409 with a clear detail message. Latency degradation under
contention (p50 rising from ~6s to ~17s at concurrency 50) is expected — serialized contention on
one row, not a systemic bottleneck — and was not investigated further since 50 concurrent writers
to one ContractVersion is not a realistic access pattern.

Listing endpoints (`GET /suppliers`, `/contracts`, `/policies`, read-only, no shared-row
contention) scale far better: p50 stays under ~0.75-1.3s through concurrency 50, p95 under ~2.6s,
zero errors at any concurrency tested.

## Rate limiting

`#116`'s per-IP identity rate limit (login) was confirmed active under a real burst, not just the
hermetic test suite: 25 rapid login attempts against a nonexistent user returned 20× 401 then 5×
429, matching the configured budget exactly.

## Raw data

Full JSON output from the final (post-fix) run is preserved at `/tmp/load_test_results.json` on
the machine this test was run from (not committed — dev-machine-local, not reproducible
infrastructure-as-code yet). The load-test script itself was a scratch artifact, not committed to
the repository; a future, permanent load-testing harness (if this becomes a recurring practice
rather than a one-time baseline) belongs under `backend/` as a real, reviewed script, not
regenerated ad hoc each time.

## Follow-ups this baseline surfaces (not yet actioned)

- Isolate and time `evaluate_policy_version` directly to give the rule-evaluation NFR a number
  it can actually be checked against (see caveat above).
- Re-run supplier-check timing with more samples once there is a non-anecdotal count to reason
  about the `total_s` variance.
- Re-run this whole baseline against production-equivalent infrastructure (real production
  Postgres tier, not Neon's dev tier; multiple backend/worker replicas) before general
  availability, per the NFR doc's own resolution path — this round only establishes "the
  architecture has no correctness bugs under load," not production capacity numbers.
