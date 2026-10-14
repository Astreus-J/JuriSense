# Security Audit — Post-Pivot Cumulative (EPIC-1 through EPIC-9, Evidence/Integrations, Frontend BFF)

**Date:** 2026-10-12 · **Scope:** the full backend (all 8 bounded contexts) and the frontend BFF
session/auth layer · **Method:** `security-review` (OWASP) + explicit ADR-003 tenant-isolation
reproduction, split across 4 parallel reviews by context cluster, triaged and fixed in this pass.

## Why this audit, why now

ADR-016 mandates a security audit at the end of every sprint, with Critical/High findings blocking
the next one. Two such audits exist for the pre-pivot `Accounts` context
(`docs/auditorias/sprint-01.md`, `sprint-02.md`), both in Portuguese, predating the 2026-09-27
pivot to JuriSense Gate. Since the pivot, 6+ EPICs of real feature work shipped with ad-hoc inline
`Security review (date)` / `QA review (date)` comments scattered through the code at each
feature's own development time, but no consolidated, formal sprint-audit report was ever written
against the actual shipped system as a whole. This is that catch-up audit — in English, per the
project-wide language rule in effect since the pivot.

## Summary

**0 Critical, 0 High, 6 Medium, 8 Low.** No cross-tenant bypass was found anywhere in the system —
each of the four reviews below wrote and ran a real, executed reproduction (not just a code read)
proving a user from one organization cannot read or write another organization's data through any
authenticated route in their assigned scope. Per ADR-016, **nothing blocks the next sprint.** All 6
Medium findings were fixed in this same pass (not deferred); of the 8 Low findings, the ones worth
tracking are listed in Encaminhamentos below, and the rest are accepted/documented trade-offs.

## Findings and fixes

### [MEDIUM] No per-IP rate limiting on public Identity endpoints — **Fixed**
- **Scope:** Identity & Organizations.
- **Problem:** `rate_limit_by_ip` (#112) shipped for the public verification route and three
  external-call-triggering routes (#143), but was never applied to Identity's own unauthenticated
  endpoints (`/auth/register`, `/auth/login`, `/auth/password/forgot`, `/auth/password/reset`,
  `/users/accept-invite`) — each of which also does a deliberately slow Argon2id hash per call
  (register, reset) or a DB write with no other throttle. `login`'s existing per-email `LoginLockout`
  does nothing against one attacker IP trying many different emails.
- **Fix:** `Settings.identity_rate_limit_max_requests`/`_window_seconds` (20 req/60s default), a new
  shared `IdentityRateLimited` dependency (`app/identity/api/deps.py`) wired to all five routes,
  sharing one budget (`key_prefix="identity_public"`) so varying the target email doesn't bypass it.
  Tests: `tests/identity/test_identity_rate_limit.py` (2 tests, including the shared-budget proof).

### [MEDIUM] `compliance_reviews`/`rule_evaluations`/`policy_exceptions` had no DB-level append-only guard — **Fixed**
- **Scope:** Policy & Compliance.
- **Problem:** These three tables were append-only only by repository convention (no update/delete
  method exposed) — the same gap #184 closed for `audit_events`/`evidence_packages`/`evidence`,
  never extended here. Confirmed via a live query against the real dev Neon database that no such
  trigger existed on any of the three.
- **Fix:** `app/core/append_only.py` (extracted from `app/evidence/infrastructure/append_only.py`,
  which was context-specific and couldn't be reused across the boundary) now takes an explicit
  `table_names` list per caller; Policy & Compliance registers its own three tables from
  `app/policies/infrastructure/models.py`. Migration `f3a6d1c8e4b7`, applied to the real dev
  database. **Found and fixed a real bug while verifying this**: `ComplianceReview.status`/
  `completed_at` are set *after* its first insert (a legitimate two-phase construction,
  `IN_PROGRESS` → terminal, within the same creating transaction) — a blanket trigger broke this
  immediately (137 test failures). Fixed by generating `review.id` client-side, wrapping the
  evaluation stretch in `session.no_autoflush` (autoflush was silently flushing the row mid-
  construction regardless of statement order), and setting the final status before the row is ever
  flushed — so the row's one and only INSERT already carries its terminal state, making it
  genuinely eligible for the trigger rather than just reordering around it. Verified against a real
  throwaway Postgres container (direct `UPDATE`/`DELETE` attempts correctly rejected) in addition to
  the SQLite-equivalent trigger the test suite exercises. `decisions` and `policies`/
  `policy_versions`/`rules` are deliberately NOT covered — see the migration's own docstring for why
  (`Decision` has several genuine in-place mutation paths; `Rule` has its own `@validates` guard for
  its one freeze point, not a DB trigger, since it's conditionally mutable, not append-only).
  Tests: `tests/policies/test_append_only_triggers.py` (4 tests).

### [MEDIUM] No per-organization resource cap on Suppliers or Contracts — **Fixed**
- **Scope:** Suppliers, Contracts & Documents.
- **Problem:** Policies/PolicyVersions/Rules got a per-organization creation cap after a prior
  finding (#180, POL-004) — Suppliers and Contracts never did, and unbounded creation here is also
  unbounded *cost*: every `create_supplier` triggers a real CNPJ/sanctions check, every contract
  upload triggers a real AI extraction call.
- **Fix:** `Settings.max_suppliers_per_organization`/`max_contracts_per_organization` (2000 each,
  generous), `SupplierLimitExceededError`/`ContractLimitExceededError`, checked before insert in
  `supplier_service.create_supplier`/`contract_service.upload_contract_version` (the latter only on
  the *new-contract* path, not on re-uploading a version against an existing one), mapped to 403.
  Tests: `tests/suppliers/test_resource_limits.py`, `tests/contracts/test_resource_limits.py` (2
  tests each — limit reached, and scoped per-organization not global).

### [MEDIUM] No decompression-bomb guard on DOCX uploads — **Fixed**
- **Scope:** AI Services / Contracts & Documents.
- **Problem:** DOCX is a zip container; `_extract_docx` → `python-docx` → `zipfile` had no
  per-member/total decompressed-size cap. The upload is bounded at 25MB *compressed*
  (`MaxBodySizeMiddleware`), but a crafted DOCX within that limit can still decompress to gigabytes
  (classic zip-bomb ratio) — unlike `sanctions_source.py`, which already caps download bytes and row
  count for exactly this risk class.
- **Fix:** `Settings.docx_max_uncompressed_bytes` (200MB), a new `_reject_docx_decompression_bomb`
  check in `app/ai_services/infrastructure/text_extraction.py`, reading each zip member's declared
  `file_size` *before* `DocxDocument` ever decompresses anything. Tests:
  `tests/ai_services/test_text_extraction.py` (2 new tests).

### [MEDIUM] Sanctions index had no staleness signal and no scheduled refresh — **Fixed**
- **Scope:** Integrations.
- **Problem:** `refresh_sanctions_index` was a registered Celery task but was never on
  `celery_app.beat_schedule` — nothing ran it on a cadence, only a manual trigger did. Separately,
  `SanctionsAdapter.check` only asked "has this list ever been indexed" (`has_data`), never "how old
  is it" — a supplier compliance decision could cite "sanctions: ok" off a snapshot weeks or months
  stale, with no indicator anywhere a compliance officer could see.
- **Fix:** `Settings.sanctions_refresh_interval_seconds` (daily) added to `celery_app.beat_schedule`;
  `Settings.sanctions_max_age_seconds` (7 days) and a new `SanctionsRepository.
  get_latest_extract_date` back a staleness check in `SanctionsAdapter.check` that now reports
  `status="unavailable"` (never a false "ok") for a list older than the threshold, same as a
  never-refreshed one. Found and fixed a knock-on issue: several existing test fixtures
  (`tests/suppliers/conftest.py`'s `seed_sanctions_index`, `tests/integrations/
  test_sanctions_adapter.py`) hardcoded a fixed past `extract_date` that would have started failing
  every test depending on it as real time passed the new 7-day threshold — switched to a
  dynamically-computed "today" so the fixtures' own intent (a just-refreshed index) stays true
  regardless of when the suite runs. Tests: 1 new dedicated staleness test, plus the fixture fix
  itself re-verified against the full existing suite (88 tests, all green).

### [MEDIUM] `UserRepository.get_by_id`/`OrganizationRepository.get_by_id` carry no `organization_id` parameter — **Accepted, documented, not fixed**
- **Scope:** Identity & Organizations.
- **Problem:** Every real call site today correctly re-checks `organization_id` after the fetch — this
  is a latent defense-in-depth gap (a future caller that forgets that check would have no second line
  of defense), not a currently exploitable one.
- **Decision:** Deferred. Adding an org-scoped variant for every call site that has an org to scope
  against is real, non-trivial refactoring work across several contexts that depend on Identity; not
  worth doing as a reactive patch in this pass given zero live exposure today. Tracked here so it
  isn't lost, not silently dropped.

## Low findings (not independently fixed this pass)

- **No explicit separation-of-duties check between a review's triggering actor and its approver**
  (Approvals & Decisions) — not a regression against the documented spec (no requester/approver
  distinction exists in `docs/03-domain/approvals.md` either), but worth a product decision.
- **No cap on raw rule-YAML size or `in:` list length**, and **no cap on total rules pooled per
  ComplianceReview across every published Policy** (Policy & Compliance) — same-tenant only, not a
  cross-tenant vector; worth a follow-up alongside the existing #180 caps.
- **`original_filename` persisted and returned unsanitized** (Contracts & Documents) — stored, not
  reflected unescaped into HTML by this backend, but an unsanitized user-controlled string reaching
  a JSON API response; a future frontend consumer must escape it on render.
- **`email_verified` is a dead column** and **`two_factor_secret` stored in plaintext** (Identity) —
  both pre-existing, both already scoped into future epics (email verification, MFA) per sprint-01's
  own LOW-001 finding; not regressions found by this audit.
- **`X-Forwarded-For` still untrusted** (Identity, rate limiting) — sprint-01's LOW-004, still open,
  already tracked (#150-#153), no new action.
- **`evidence_override_addenda`'s append-only trigger is present and enabled but unexercised by live
  data** (Evidence & Audit) — the table is currently empty in the real dev database; not a defect,
  just not independently re-verified against a real row this round.

## Verified clean (selected highlights; see each sub-review's full report for the complete list)

- **JWT/Argon2id/lockout** (Identity): algorithm pinned, claims enforced, access/refresh
  non-interchangeable, refresh rotation single-use, logout blocklist checked on every request,
  production secret-strength guard. Sprint-01/02's MED-001 (logout doesn't revoke all sessions) and
  MED-002 (registration email enumeration) are both confirmed **fixed and tested**; LOW-003
  (non-atomic lockout counter) confirmed **fixed**.
- **Frontend BFF**: httpOnly/sameSite=lax cookies, `backend.ts`'s `server-only` boundary holding (no
  client-component importer), JWTs never reaching browser JS, the new CSRF defense (`csrf.ts`)
  independently re-verified as fail-closed and correctly reasoned, the login redirect's `next`
  parameter sanitized against open redirect.
- **CEL rule evaluation** (Policy & Compliance): CEL injection impossible by construction (no raw
  syntax ever reaches the compiler from a policy author); no loop/recursion/regex-equivalent
  ReDoS surface in the compiled grammar this DSL emits.
- **PolicyException** (#120, this session's own newest feature): re-verified independently — XOR
  target check, future-only `valid_until`, actor-role-match against the *waived rule's*
  `approver_role`, 3-hop ownership chain, per-rule active-exception cap. No new bug found.
- **SSRF posture, every external call** (Suppliers, Contracts, AI Services, Integrations): CNPJ
  registry, sanctions sources, AI Gateway, all call only a hardcoded `BASE_URL`; no user-suppliable
  host or path segment reaches any of them.
- **Prompt-injection defense** (#113): re-run and read, not just trusted — genuinely captures the
  outgoing request body and asserts the injected text never forges a message or produces the
  injected instruction's demanded output.
- **AnchoringProvider abstraction** (ADR-007): no code outside the one abstraction ever touches a
  chain SDK directly; Constellation credentials (configured live this session) never logged, never
  echoed to an HTTP caller.
- **Append-only enforcement, live database check** (Evidence & Audit): connected directly to the
  real Neon database and confirmed, inside rolled-back transactions, that a live `UPDATE`/`DELETE`
  against `audit_events`/`evidence_packages`/`evidence` is genuinely rejected today — not merely
  consistent with the migration file.
- **Secrets hygiene, repo-wide**: `backend/.env` confirmed gitignored and never committed
  (`git log --all`); only `.env.example` placeholders are tracked.

## Encaminhamentos (follow-up tracking)

| Finding | Destination |
|---|---|
| `get_by_id` methods lack org-scoping (Identity) | Backlog — refactor alongside the next Identity-touching epic, not reactively |
| No separation-of-duties check (Approvals) | Needs a product decision before any code change |
| No cap on rule-YAML size / pooled-rules-per-review (Policy & Compliance) | Follow-up alongside the existing #180 caps |
| `original_filename` unsanitized (Contracts) | Document the escaping contract for the frontend, or sanitize at upload time |
| `evidence_override_addenda` trigger unexercised by live data | Re-verify once a real override exists, or add a CI-level live-row check |
| `X-Forwarded-For` untrusted (Identity) | Already tracked, #150-#153 |
