# ADR-003 — Multi-Tenancy & RBAC Model

## Status
Accepted

## Context
JuriSense Gate is B2B SaaS: every organization's suppliers, contracts, policies, and decisions must
be strictly isolated from every other organization's. The existing `Accounts` context already
implements logical multi-tenancy (every tenant-owned table carries `organizacao_id`) and a granular
per-user RBAC grid (`PermissaoModulo`: user × module × action). This is a solid, already-tested
pattern (see `docs/_legacy/tradeoffs.md` TR-002/TR-004, formalized as ADR-012/ADR-015), but its
role and module vocabulary is tied to the old legal-ERP domain (`Perfil.advogado_senior`, `Modulo.processos`, etc.).

## Decision
Keep **logical multi-tenancy by `organization_id`** (renamed from `organizacao_id`) on every
tenant-owned table, enforced at the repository layer, with a **mandatory cross-tenant-access test**
in the audit checklist for every new context (continuing the practice from `docs/auditorias/`).
Keep **RBAC as data** (role/module/action grid), but redefine the vocabulary for the compliance
domain:

- **Roles**: `Admin`, `Procurement`, `Legal`, `Compliance`, `Privacy`, `Security`, `Finance`,
  `Approver`, `Auditor`, `Viewer`.
- **Modules**: `suppliers`, `contracts`, `policies`, `compliance_reviews`, `approvals`, `evidence`,
  `integrations`, `organization_settings`.
- Each role has a default module×action grid (seeded), and admins may customize per-user grants
  exactly as the existing `Accounts` code already supports.

## Alternatives Considered
- **Schema-per-tenant**: stronger isolation, but heavy migration/connection-pooling overhead for a
  SaaS with many small-to-mid organizations; rejected for v1 (same reasoning as the original
  TR-004 decision).
- **Postgres Row-Level Security (RLS)**: valuable defense-in-depth, deferred as a v1.x hardening
  item (tracked in `docs/09-planning/backlog.md`), not a blocker for the hackathon cut.
- **Fixed/hardcoded roles**: simpler, but the compliance domain explicitly requires per-organization
  customization of who approves what (e.g., a company may require Director approval above a
  contract-value threshold while another only requires Legal) — data-driven RBAC is required.

## Consequences
- The existing `Accounts` schema shape (`Organizacao`, `Usuario`, `PermissaoModulo`) is reused
  structurally; only enum values, field names, and seed data change — this is migration work
  tracked in `pivot-migration.md`, not a rewrite.
- A tenant-isolation bug remains the highest-severity class of defect possible in this system;
  every sprint audit must explicitly test cross-tenant access (continuing TR-005/ADR-016).
