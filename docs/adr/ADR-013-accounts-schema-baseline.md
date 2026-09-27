# ADR-013 — Accounts Schema Baseline (historical context)

## Status
Accepted (historical) — superseded in vocabulary by ADR-003; schema *shape* still reused

## Context
Formalizes TR-006 from `docs/_legacy/tradeoffs.md`: the original `Accounts` schema (organization
with tax-id/contact/address; user with national-id, professional-license fields, phone, `status`
enum, 2FA fields, `last_access`; per-user×module×action permissions) was designed to mirror a
Django prototype referred to as "JuriSense_backend."

**Important correction (2026-09-27 repository audit):** that Django prototype does **not exist**
anywhere in this repository or its git history, and no such path was found on the filesystem
referenced by prior project memory. The mirroring decision is retained here purely as historical
context for why the schema looks the way it does; it should not be treated as a pointer to a real,
recoverable artifact.

## Decision
Reuse the **shape** of the existing schema (organization/user/permission-grid with per-user
granularity, status enum, audit-relevant fields) as the baseline for the new `Identity &
Organizations` context. Do **not** reuse legal-domain-specific fields/values (`oab`, `uf_oab`,
`Perfil.advogado_*`) — these are migration/removal work per `pivot-migration.md`.

## Alternatives Considered
- **Redesign the schema from scratch**: rejected — the existing shape (per-user permission grid,
  status lifecycle, audit log table `Acesso`) is sound and already tested; redesigning would discard
  working, audited code for no functional benefit.

## Consequences
- Two conscious divergences from the (nonexistent, historical-reference-only) Django prototype
  remain valid as-is: login lockout lives in Redis, not DB columns; `ativo`/`active` is a derived
  property of `status`, not a separate field.
- Invite, password-recovery, and audit-log features already built in Sprints 2 and later remain in
  place unchanged by this ADR.
