# Security

JuriSense Gate's entire value proposition is trustworthiness — a product whose job is to tell a
company "you can trust this vendor/contract" must itself be trustworthy. This document is the
complete security requirement set for engineering, not a placeholder; every section below is a
concrete, actionable rule, not a category to fill in later.

## Authentication

- Short-lived **JWT access tokens (15 minutes)** plus a **rotating refresh token (7 days)**, with a
  Redis-backed revocation blocklist for refresh token `jti`s — ADR-011. This is domain-agnostic and
  already implemented (`app/core/security.py`, `app/accounts/application/auth_service.py`).
- Access-token revocation is **not instantaneous** within the 15-minute window (an accepted,
  documented trade-off in ADR-011) — anything requiring stronger guarantees (e.g. immediately killing
  a compromised admin session) uses the refresh-token revocation blocklist plus accepts the residual
  access-token window, not a redesign of the token model.
- Password hashing is **Argon2id** (argon2-cffi, OWASP-recommended parameters) — never store or log a
  plaintext password, and use a dummy hash comparison on login for nonexistent emails to keep timing
  uniform (already implemented and verified in `docs/auditorias/sprint-01.md`).
- Login lockout after repeated failures (5 attempts / 15 minutes, `login_max_attempts`/
  `login_lockout_minutes` in `app/core/config.py`) is a known, accepted DoS-against-a-single-account
  trade-off (`sprint-01.md` LOW-002); progressive lockout/CAPTCHA and IP-based rate limiting are the
  planned mitigation (see Rate limiting below), not a reason to remove the lockout.
- All new bounded contexts reuse the existing `Accounts` authentication mechanism via
  `CurrentUser`/`CurrentAdmin`-style dependencies (`app/accounts/api/deps.py`) — no context
  reimplements its own auth.

## Authorization & tenant isolation

- **Every tenant-owned resource is isolated by `organization_id`, enforced at the repository layer**
  (ADR-003) — see `docs/07-engineering/database-standards.md` for the concrete column/index/repository
  rules. This is the single highest-severity class of defect possible in this system (ADR-003's own
  words) because a cross-tenant leak in a B2B compliance product is both a security incident and an
  immediate, irrecoverable trust failure with every affected customer.
- **RBAC as data**: role × module × action grid (`ADR-003`, `ADR-012`), roles
  (`Admin, Procurement, Legal, Compliance, Privacy, Security, Finance, Approver, Auditor, Viewer`)
  and modules (`suppliers, contracts, policies, compliance_reviews, approvals, evidence,
  integrations, organization_settings`) as defined in ADR-003. Every new endpoint declares which
  module × action it requires and is denied with `403` when the caller's grant doesn't cover it.
- **The mandatory cross-tenant-access test**: every new bounded context's audit checklist (ADR-016)
  and its ordinary test suite (`docs/07-engineering/testing-strategy.md`) both include an explicit
  test that a user in Organization B cannot read, write, or infer the existence of a resource owned
  by Organization A. The correct response for a cross-tenant lookup is **`404`, never `403`** — a
  `403` confirms the resource exists in another tenant, which is itself an information leak
  (established pattern, `docs/auditorias/sprint-02.md`: "usuário de outra org retorna 404 (sem
  vazar existência)").
- Postgres Row-Level Security (RLS) is a deferred v1.x hardening layer (ADR-003) — until implemented,
  the repository-layer filter is the **only** enforcement and must be present on every single query
  against a tenant-owned table, with no exceptions for "internal" or "admin" code paths.

## Secure file upload validation and malware scanning

Contract and supporting-document uploads (`Contracts & Documents` context) are the highest-risk input
surface in the product — arbitrary files from suppliers/counterparties, uploaded by customers who may
themselves have received a malicious file:

- **Validate before storing, not after**: enforce an allowlist of accepted mime types (PDF, DOCX,
  TXT — matching the product's stated ingestion formats) and a maximum file size, rejecting anything
  else at the API boundary before it reaches storage or a worker.
- **Verify the actual file content matches its declared type** (magic-byte/content sniffing), not
  just the filename extension or the client-supplied `Content-Type` header — a renamed executable
  with a `.pdf` extension must not pass validation.
- **Malware-scan every upload** before it is made available for processing or download — a scanning
  step (e.g. ClamAV or an equivalent) runs as part of the async ingestion pipeline (Celery, ADR-006)
  before a `Document` transitions from `uploaded` to `processed`; a positive scan result rejects the
  upload and emits an `AuditEvent`, it does not silently quarantine-and-continue.
- Never pass an uploaded file directly to a shell command or a PDF/DOCX parsing library without going
  through a hardened, sandboxed parsing path — document parsers are a known class of exploitable
  attack surface (malformed PDF triggering a parser vulnerability); prefer well-maintained libraries
  with a security-patch track record and keep them current (see Dependency scanning below).
- Uploaded content hashing (`content_hash`, SHA-256, per `docs/03-domain/domain-model.md`'s `Document`
  entity) is computed **after** validation/scanning passes, and is itself never treated as a security
  control — it is a provenance/integrity property, not an anti-malware measure.

## Encryption at rest and in transit

- **In transit**: TLS everywhere — the VPS's public surface is TLS-terminated (Cloudflare in front,
  per the hosting model in `docs/00-project/overview.md`), and the Neon PostgreSQL connection uses
  `sslmode`/`ssl` (already handled by `_normalizar_database_url` in `app/core/config.py`, which
  converts libpq `sslmode` to asyncpg's `ssl` parameter). Internal Docker Compose network traffic
  (backend ↔ Redis, backend ↔ s3mock in dev) is not additionally TLS-wrapped in development, which is
  an accepted trade-off for the local dev environment only — production inter-service traffic on the
  VPS should stay on a private network segment, not exposed beyond the host.
- **At rest — database**: relies on Neon's own encryption-at-rest for the managed PostgreSQL instance
  (a managed-provider guarantee, not something this codebase implements) — verify Neon's current
  encryption posture as part of vendor due diligence, not assumed silently.
- **At rest — object storage**: Cloudflare R2 (prod) and s3mock (dev) — both are S3-compatible and
  support server-side encryption; enable it at the bucket level for R2 in production (ADR-008). Never
  rely on application-level encryption of file contents as a substitute for verifying the storage
  backend's own encryption-at-rest is actually enabled.
- **Evidence Package privacy**: only hashes/commitments of evidence are ever written on-chain — never
  raw contract text or personal data (`ADR-007`, `BR-EVD-002`, `docs/06-blockchain/privacy.md`). This
  is as much a security property as a product one: on-chain data is permanent and public, so this
  rule has zero tolerance for exceptions.

## Secrets management

- All secrets (JWT signing key, database URL, SMTP credentials, AI provider API keys, object storage
  credentials, `AnchoringProvider` credentials) are environment-variable-based, loaded via
  pydantic-settings from `.env` (`backend/.env`, gitignored) — **never committed to git**, matching
  the already-verified pattern (`docs/auditorias/sprint-02.md`: "`backend/.env`... está no
  `.gitignore` e fora do índice do git; `.env.example` voltou ao placeholder").
- `Settings._exige_segredo_em_producao` in `app/core/config.py` already refuses to boot in
  `production` with the default dev JWT secret or a secret under 32 characters — this pattern (a
  startup-time guard against insecure defaults in production) extends to every other
  secret-shaped setting added by new contexts (AI provider keys, anchoring provider keys): fail fast
  at startup, don't silently run insecurely.
- `.env.example` is kept in sync with every new secret-shaped setting, using an obvious placeholder
  value, never a real-looking one.
- CI never has access to production secrets; contract tests against external providers use recorded
  fixtures specifically so CI never needs a live API key for OpenAI/Anthropic/CNPJ sources/anchoring
  providers (`docs/07-engineering/testing-strategy.md`).

## Dependency scanning

- `uv lock --check` (already run as part of the audit ritual, `sprint-02.md`) verifies the lockfile
  is consistent with `pyproject.toml` — run in CI on every PR, not only during manual audits.
- A dependency vulnerability scan (e.g. `pip-audit` or GitHub's native Dependabot alerts for the
  `backend/` and `frontend/` dependency manifests) runs in CI (`docs/07-engineering/ci-cd.md`'s
  security-checks stage) and on a recurring schedule, since new CVEs are disclosed against
  already-pinned versions constantly, not only when a manifest changes.
- A critical/high-severity dependency vulnerability is treated the same as a critical/high finding
  from a manual audit (ADR-016): it blocks starting new feature work until patched or explicitly
  risk-accepted with a written justification.

## Rate limiting on public endpoints

- **The public verification page (`GET /verify/{hash}`, `docs/06-blockchain/verification.md`) is
  unauthenticated by design** and is therefore the single most important rate-limiting target in the
  system — anyone can hit it without an account. It gets IP-based rate limiting (Redis token-bucket
  or fixed-window counter, mirroring the existing lockout-counter infrastructure pattern in
  `app/accounts/infrastructure/lockout.py`) tuned to allow legitimate verification traffic (a human
  checking one hash) while blocking enumeration/scraping attempts against the anchor space.
- Public/pre-authentication endpoints that send email (`/auth/register`, `/auth/password/forgot`) get
  the same IP-based rate limiting — already an identified, tracked gap (`sprint-01.md` LOW-005,
  scheduled for Sprint 5) rather than a new finding; this document makes the general rule explicit so
  every future public endpoint is rate-limited from creation, not retrofitted after an audit finds
  the gap again.
- Authenticated endpoints get a coarser, per-organization or per-user rate limit as a general
  abuse/cost-control backstop (particularly endpoints that trigger billable AI usage, like
  `POST /compliance/check`), separate from and in addition to plan-limit enforcement
  (`ADR-014`, `BR-ORG-003`), which governs business-limit exceedance, not abuse.

## CSRF, CSP, and SSRF

- **CSRF**: the API is a stateless, `Authorization: Bearer` JWT API (not cookie-session-based), which
  is inherently not vulnerable to classic CSRF — if any endpoint ever adopts cookie-based auth
  (e.g. for a specific frontend flow), it must add CSRF tokens at that point; until then, do not
  introduce cookie-based session auth without revisiting this section.
- **CSP**: the Next.js frontend serves a Content-Security-Policy header restricting script/style/
  connect sources to the app's own origin and explicitly allowlisted third parties (no
  `unsafe-inline`/`unsafe-eval` by default) — set via Next.js middleware or `next.config.ts` headers,
  particularly important for the public `/verify/{hash}` page, which is the frontend surface most
  likely to be linked from outside the product (shared on a signed contract, indexed by search
  engines) and therefore the one most worth hardening against injected content.
- **SSRF**: any server-side fetch to an external target driven even partially by user/organization
  input — company-registry lookups, sanctions-list sources, a future Integration webhook target, a
  document fetched from a URL instead of uploaded — validates the target against an **explicit
  allowlist of known-good hosts** (the specific CNPJ/CEIS/CNEP/CEPIM/sanctions API hosts, the
  configured AI provider hosts, the configured anchoring provider's RPC endpoint), never a
  user-suppliable arbitrary URL fetched as-is. This specifically guards against an
  Integrations-context webhook or a future "verify supplier by URL" feature being used to make the
  backend issue requests to internal network addresses (cloud metadata endpoints, the Redis/Postgres
  hosts themselves) — a classic SSRF-to-internal-network-access chain that a plausible-looking
  compliance-workflow feature could otherwise open up.

## Prompt injection and indirect prompt injection defense

The AI-adjacent surface has a specific injection risk this product must design against, because its
core input is **untrusted third-party documents** (a supplier's contract, a supplier's submitted
data) fed into an LLM:

- **AI Services never decides a compliance outcome** (ADR-005) — this is itself the primary defense:
  even a fully successful prompt injection inside a contract's text can, at worst, corrupt the
  *extraction* output, not directly flip an APPROVE/BLOCK decision, because that decision is made by
  the deterministic Policy Engine evaluating structured, schema-validated fields, not by asking the
  LLM "should we approve this."
- Extraction calls always require **structured output** (JSON schema / tool-calling, per ADR-005),
  never freeform text parsing — a structured-output constraint is itself a meaningful injection
  defense, since the model is constrained to populate typed fields rather than execute free-text
  instructions found in the document.
- **Indirect prompt injection** specifically: content retrieved via RAG (the policy playbook, prior
  decisions, `pgvector`-retrieved clauses — ADR-009) or extracted from an uploaded document is always
  treated as **data**, never as instructions, when constructing a prompt. System/instruction prompts
  are structurally separated from retrieved/extracted content (e.g. clearly delimited context blocks,
  explicit instructions to the model that content inside those blocks is data to analyze, not commands
  to follow) — the concrete prompt-construction guardrails are specified in `docs/05-ai/guardrails.md`;
  this document states the non-negotiable requirement they implement.
- **RAG poisoning**: malicious content in a retrieved document or policy playbook entry must never be
  treated as an instruction by the retrieval-augmented generation pipeline — this is the same
  principle as indirect prompt injection, applied specifically to the retrieval corpus. Because the
  policy playbook is itself organization-authored content, a compromised or careless
  policy-author account is a realistic route for this — RBAC on who can author policy content
  (`policies:write` module grant) is therefore also an AI-security control, not just a data-integrity
  one.
- Guardrail behavior is tested with adversarial fixture documents as part of the AI evaluation suite
  (`docs/07-engineering/testing-strategy.md`), not assumed correct because "the model usually behaves."

## CI security

- Dependency scanning and secret scanning (e.g. gitleaks or GitHub's native secret scanning) run as
  CI gates on every PR (`docs/07-engineering/ci-cd.md`'s security-checks stage), not only during
  manual sprint audits — CI catches an accidentally-committed key the same day it happens, an audit
  catches it up to two weeks later.
- A secret-scanning true positive (a real credential committed, even briefly) is treated as an
  incident: the credential is rotated immediately, not just removed from the diff — git history
  retains it until a history rewrite, which is itself a disruptive, carefully-coordinated action, so
  rotation is the fast, always-correct first response.

## Security audit as a sprint gate

- **Every sprint ends with a security audit** (ADR-016): skills `security-review` + `insecure-defaults`
  plus a manual checklist that always includes the explicit tenant-isolation/cross-tenant-access test.
  **Critical/high findings block the start of the next sprint** — this gate is non-negotiable for this
  product specifically because it handles supplier/contract compliance decisions for other companies
  (ADR-016's own stated reasoning), not treated as a scope-cut candidate under hackathon time
  pressure.
- This practice already has two real precedents to follow as the template for every future context's
  audit: `docs/auditorias/sprint-01.md` (Accounts foundation/auth — 2 medium, 4 low findings, both
  mediums fixed and test-verified the following sprint) and `docs/auditorias/sprint-02.md`
  (Accounts user management/password recovery — 0 critical, 0 high, 3 low, both prior mediums
  verified fixed by name-matched tests). New contexts' audits follow the same report shape: scope,
  method, findings by severity with location/impact/fix, verifications-with-no-findings (documenting
  what was checked and passed, not only what failed), and a routing table for where each finding's
  fix lands.
- A "low" finding is not automatically deferred — `sprint-01.md`/`sprint-02.md` show low findings
  being explicitly routed to a named future sprint or accepted as a documented, reasoned risk, never
  silently dropped. New audits follow the same discipline: every finding gets an explicit
  disposition.
