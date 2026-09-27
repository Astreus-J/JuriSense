# Pivot Migration Inventory

**This document is an inventory for future implementation work (Phase 0–1 of `roadmap.md`,
concretely steps 1–2 of `implementation-plan.md`). It does not itself execute any migration — no
code under `backend/` or `frontend/` is changed by this documentation pass.**

On 2026-09-27, JuriSense pivoted from a generic legal-tech ERP for Brazilian law firms ("SchemaJud")
to **JuriSense Gate**, a B2B supplier/contract compliance platform. This document has two parts:
(a) what happened to the **documentation** during the pivot, restated here in planning context, and
(b) a concrete disposition — REUSABLE / ADAPTABLE / REMOVE / REWRITE — for the **code** the pivot
inherits, based on reading the actual existing implementation in `backend/app/accounts/` and
`frontend/src/lib/landing-data.ts`.

## (a) Documentation disposition

The full archival record lives in `docs/_legacy/README.md`; restated here for planning continuity:

| Archived to `docs/_legacy/` | What it was | Why archived |
|---|---|---|
| `README-schemajud-legacy.md` | Original root `README.md`: full spec of the legal-ERP product, 125 functional requirements across 15 modules, business rules, use cases, market analysis, pricing. | Describes a different product entirely (process/deadline/jurimetria/billing management for law firms), superseded by `docs/00-project/overview.md` and the new `docs/01-product/functional-requirements.md`. |
| `CLAUDE-legacy.md` | Original root `CLAUDE.md` describing the legal-ERP repository. | Same — described the pre-pivot product and repo framing. |
| `PLANO_EVOLUCAO_JURISENSE.md` | Strategic roadmap for the legal-ERP vision (MVP Previdenciário → V1–V4 practice-area verticals). | Roadmap for a product line (practice-area verticals) that no longer exists; superseded by this document's own `roadmap.md`. |
| `IMPLEMENTACAO_ARQUITETURA/` (5 files) | Architecture docs for the legal-ERP product: GCP infrastructure, AI strategy, backend DDD (5 bounded contexts: Accounts/Processes/Documents/Deadlines/IA_Services), AI specialist briefing, GCP hosting plan. | Modeled the wrong domain (Processos/Prazos/Jurimetria) end to end; GCP hosting plan was also already stale pre-pivot (actual hosting decision was a single VPS). Superseded by `docs/adr/` (ADR-001, ADR-002, ADR-008) and the new `docs/03-domain/domain-model.md` (8 bounded contexts: Identity & Organizations, Suppliers, Contracts & Documents, Policy & Compliance, Approvals & Decisions, Evidence & Audit, AI Services, Integrations). |
| `diagramas/` | PlantUML/Mermaid diagrams (ER model, UML classes, domain relationships, sequence diagrams, use-case diagram, microservices diagram) — all modeling Processo/Prazo/Jurimetria/Timesheet, etc. | Diagrams model entities that don't exist in the new domain model at all. |
| `tradeoffs.md` | 6 informal architecture decisions made during the Accounts bounded-context build (JWT strategy, RBAC-as-data, multi-tenancy, payment gateway deferral, security-audit-as-gate, schema alignment to a Django prototype). | Formalized as ADR-011 through ADR-016 — the *decisions* (not the domain) carried forward unchanged, so the informal notes were superseded by formal ADRs, not discarded as wrong. |
| `implementation-plan.md` (legacy) | Sprint plan for building the Accounts bounded context — already executed (see git log). | Historical record of completed work, not a forward-looking plan; this document's own `implementation-plan.md` is the current one. |

**Not archived** (still active, not legacy): `docs/auditorias/sprint-01.md` and `sprint-02.md` —
these audit the `Accounts` code that continues to be reused (as `Identity & Organizations`) in the
new product, so they remain technically relevant.

**A note on dangling references**: legacy documents and prior project memory referred to a
`JuriSense_frontend/` Vite+React prototype and a `JuriSense_backend` Django prototype as if they
existed in or alongside this repository. A full repository audit (2026-09-27) confirmed **neither
exists** anywhere in this repo or its git history — `JuriSense_frontend/` in the current repo is
real but is explicitly documented in the root `CLAUDE.md` as "a legacy Vite + React prototype,
superseded by `frontend/`," which is a different (real, present) thing from the dangling
`JuriSense_backend` reference. Any future document repeating the Django-prototype reference should
be corrected, not propagated — see `ADR-013`'s "Important correction" section, which already made
this fix once.

## (b) Code disposition

Based on reading `backend/app/accounts/` in full (`domain/`, `application/`, `infrastructure/`,
`api/` — roughly 1,800 non-test lines across `models.py`, `constants.py`, `errors.py`, `rules.py`,
`password.py`, `ports.py`, `auth_service.py`, `user_service.py`, `invite_service.py`,
`password_service.py`, `email.py`, `lockout.py`, `token_store.py`, `repositories.py`, `routes.py`,
`users.py`, `schemas.py`, `deps.py`).

### REUSABLE — as-is, no domain-specific content

- **JWT + Argon2id + Redis auth flow** (`application/auth_service.py`, `core/security`): short-lived
  (15 min) access tokens, rotating 7-day refresh tokens, Redis-backed revocation blocklist for
  refresh-token `jti`s (`ADR-011`). Entirely domain-agnostic — nothing here references legal-ERP
  concepts.
- **Login lockout** (`infrastructure/lockout.py`, `LoginLockout`): Redis-backed max-attempts/
  lockout-window pattern, configurable via `get_settings()`. Domain-agnostic.
- **Invite system** (`application/invite_service.py`, the `Convite` model): token-hash-based
  invitation flow with expiry and accept/cancel states. The *shape* (email, target role, token hash,
  expiry, accepted/cancelled/expired) is fully reusable; only the `perfil` field's value type
  changes (see ADAPTABLE below) — the invite mechanism itself needs zero logic changes.
- **Password recovery** (`application/password_service.py`, the `TokenRecuperacao` model):
  SHA-256 token-hash pattern, single-use, expiring. Domain-agnostic.
- **Admin dependency pattern** (`api/deps.py`): `get_current_user` → `get_current_admin` FastAPI
  dependency chain, `AccessPayload`/`CurrentUser`/`CurrentAdmin` typed-Annotated aliases, the
  `EmailDep` provider switching between console/SMTP senders by config. The *pattern* (bearer-token
  decode → blocklist check → user lookup → active-status check → optional role gate) is fully
  reusable; only the specific role check (`usuario.perfil != Perfil.ADMINISTRADOR.value`) needs its
  enum reference updated once `Perfil`→`Role` (see ADAPTABLE below) — the dependency-chaining
  approach itself does not change.
- **FastAPI app shell** (`app/main.py`'s `create_app` + lifespan, `app/core/config.py`,
  `app/api/router.py`): async app factory, pydantic-settings config, `.env`-driven libpq→asyncpg URL
  normalization for the external Neon Postgres, `/api` router aggregation. None of this is
  domain-specific.
- **Test patterns**: the existing ~700 lines of Accounts tests (httpx `ASGITransport`, pytest
  fixtures for session/redis) establish a reusable testing scaffold for every new bounded context —
  new contexts should follow the same fixture/assertion style, not invent a new one.
- **Audit-log table pattern** (`infrastructure/models.py`'s `Acesso` — login-attempt history):
  the *pattern* of an append-only, timestamped, actor-linked event table is exactly the shape the
  new `AuditEvent` entity (`docs/03-domain/domain-model.md`) generalizes — `Acesso` itself is
  Identity-specific (login attempts only) and stays as-is inside `Identity & Organizations`, but it
  is the direct ancestor of the cross-cutting `AuditEvent` design, not something being replaced by it.

### ADAPTABLE / RENAME — same shape, new vocabulary

- **`Organizacao` → `Organization`**: rename table, class, and every field
  (`nome`→`name`, `cnpj`→`tax_id` — noting `tax_id` must become jurisdiction-generic, not
  CNPJ-specific, per the Jurisdiction Pack design in `docs/00-project/overview.md`
  "Internationalization" — `email_contato`→`contact_email`, `endereco`→`address`, etc.).
- **`Usuario` → `User`**: rename table, class, and fields (`nome_completo`→`full_name`,
  `senha_hash`→`password_hash`, `telefone`→`phone`, `email_verificado`→`email_verified`,
  `ultimo_acesso`→`last_access`, `criado_em`/`atualizado_em`→`created_at`/`updated_at`). The `cpf`
  field's fate is a product decision, not purely technical: a Brazil-jurisdiction individual
  identifier may still be useful for an individual user record (distinct from the organization's
  `tax_id`) — default to keeping it renamed to a jurisdiction-generic `national_id` unless product
  scoping says otherwise.
- **`Perfil` enum → `Role`** (`ADR-003`): replace
  `administrador/advogado_senior/advogado_junior/estagiario/cliente` with
  `Admin/Procurement/Legal/Compliance/Privacy/Security/Finance/Approver/Auditor/Viewer`. Every
  reference site needs updating, not just the enum definition — confirmed reference sites from the
  code read include `models.py` (`Usuario.perfil` default), `auth_service.py` (imports `Perfil`),
  `user_service.py` (`criar_usuario`'s `perfil: Perfil` parameter), and `api/deps.py`
  (`get_current_admin`'s `usuario.perfil != Perfil.ADMINISTRADOR.value` check, which becomes
  `user.role != Role.ADMIN.value`).
- **`Modulo` enum → new module vocabulary** (`ADR-003`): replace
  `processos/documentos/ia/jurimetria/prazos/financeiro/clientes/relatorios/portal_cliente` with
  `suppliers/contracts/policies/compliance_reviews/approvals/evidence/integrations/
  organization_settings`. `PermissaoModulo` (the per-user × module × action grid) keeps its exact
  shape (`pode_criar`/`pode_ler`/`pode_atualizar`/`pode_excluir` → `can_create`/`can_read`/
  `can_update`/`can_delete`) — only the `modulo` value set changes, per `ADR-012`.
- **`Plano`/`LIMITES_POR_PLANO` → new plan limits**: replace
  `autonomo/escritorio/escritorio_plus/enterprise` and their associated
  `usuarios/processos_ativos/armazenamento_gb/geracoes_ia_mes` limits with plan tiers and limit
  dimensions matching the new product (suppliers analyzed, contracts reviewed, AI executions per
  period, per `BR-ORG-003`) as defined in `docs/02-business/pricing-strategy.md`. The
  `LimitesPlano` dataclass shape and the `LimiteUsuariosAtingidoError` 402-style enforcement pattern
  (`BR-ORG-003`'s "enforced at creation, not retroactively" rule mirrors this existing behavior
  exactly) both carry over unchanged — only the enum values and numeric limits change.
- **`organizacao_id` → `organization_id`, and every other Portuguese identifier → English**: this
  is the single largest mechanical change by line count. Confirmed occurrences from the code read
  include table/column names (`organizacoes`, `usuarios`, `permissoes_modulo`, `tokens_recuperacao`,
  `convites`, `acessos` and their columns), Python identifiers throughout all `application/*.py`
  files (`criar_usuario`, `listar_usuarios`, `obter_usuario`, `atualizar_usuario`,
  `desativar_usuario`, and their parameters), and every docstring/error message currently in
  Portuguese (e.g., `AccountsError` subclasses' human-readable messages in `domain/errors.py`).
  Per the project-wide language rule (this document is written in English per instruction; the
  product's user-facing copy remains pt-BR per the root `CLAUDE.md` for the *legacy* product, but
  JuriSense Gate's new user-facing copy and all new documentation are English-first per this
  planning effort) — code identifiers, error messages, and docstrings should move to English as part
  of this rename, while any future pt-BR *localization* of user-facing strings (if the Brazil go-to-
  market requires it) is a separate, later concern from the identifier rename itself.

### REMOVE — no longer relevant to a compliance-platform user

- **`oab`/`uf_oab` fields** on `Usuario`/`User` (a Brazilian bar-association registration number and
  state) — meaningless for a Procurement/Legal/Compliance/Finance user in a B2B compliance product;
  not every `Legal`-role user is a licensed attorney with an OAB number, and the product does not
  need to know this even for those who are.
- **`OabInvalidaError`** and **`OabJaCadastradaError`** (`domain/errors.py`) — remove entirely along
  with their call sites: `domain/rules.py`'s `validar_formato_oab()` function, and every call to it
  in `user_service.py`'s `criar_usuario()` and `atualizar_usuario()` (confirmed in the code read:
  both functions currently validate/uniqueness-check `oab`/`uf_oab` inline).
- **`UsuarioRepository.get_by_oab()`** and any other OAB-specific repository method
  (`infrastructure/repositories.py`) — remove once the field is gone.
- **OAB-related test fixtures and test cases** in the existing Accounts test suite — these tests
  currently exercise `OabInvalidaError`/`OabJaCadastradaError` paths that will no longer exist; they
  should be deleted, not adapted, since there is no equivalent compliance-domain concept to redirect
  them at.

### REWRITE — not a rename, a full content replacement

- **`frontend/src/lib/landing-data.ts`** — confirmed by direct read to be **100% old-product
  marketing copy** with no reusable logic beyond the TypeScript type shapes themselves
  (`Feature`, `Plan`, `Step`, `Faq`). Specifically: the `features` array describes case management,
  client management, "IA para Petições" (AI for legal filings), jurimetria, deadline alerts,
  automated billing, reports, and LGPD security — none of which describe JuriSense Gate. The `plans`
  array (`Autônomo`/`Escritório`/`Escritório Plus`/`Enterprise`, priced R$189–R$1,490/month) is
  scoped around "processos ativos" (active legal cases) and law-firm user counts, not suppliers/
  contracts/AI-executions. The `steps` "how it works" copy ("Configure seu escritório," "Adicione
  seus clientes," "Configure seus casos") is law-firm-onboarding-specific. The `faqs` array answers
  law-firm-specific questions (court synchronization, petição drafting, WhatsApp notifications for
  procedural deadlines). Only the `contact` object (email, phone, location, social links) and the
  four exported TypeScript `type` declarations are genuinely reusable as-is. This is tracked as
  `roadmap.md` Phase 8 / `implementation-plan.md` step 16 — a full rewrite against
  `docs/02-business/pricing-strategy.md` and the actual JuriSense Gate feature set, not a migration
  of existing content.

## Summary table

| Item | Disposition | Where it lands |
|---|---|---|
| JWT/Argon2/Redis auth, lockout, invite, password-recovery flows, FastAPI app shell, test patterns, `Acesso` audit-log pattern | REUSABLE | `app/identity/` (renamed from `app/accounts/`), unchanged behavior |
| `Organizacao`→`Organization`, `Usuario`→`User`, `PermissaoModulo` shape, `Perfil`→`Role`, `Modulo`→ new modules, `Plano`/`LIMITES_POR_PLANO`→ new plan limits, `organizacao_id`→`organization_id`, all Portuguese identifiers | ADAPTABLE / RENAME | `app/identity/`, mechanical rename per `ADR-003`/`ADR-012`/`ADR-013` |
| `oab`/`uf_oab` fields, `OabInvalidaError`, `OabJaCadastradaError`, `validar_formato_oab()`, `get_by_oab()`, OAB test cases | REMOVE | deleted, no replacement |
| `frontend/src/lib/landing-data.ts` (all content) | REWRITE | new JuriSense Gate copy, `roadmap.md` Phase 8 |
| All legal-ERP documentation (README, architecture docs, diagrams, old roadmap) | Archived to `docs/_legacy/` | historical reference only, per `docs/_legacy/README.md` |

This inventory is the authoritative input for `implementation-plan.md` steps 1–2 (Phase 0 of
`roadmap.md`); it is not itself an implementation task.
