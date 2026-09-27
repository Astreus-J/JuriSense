# ADR-012 — RBAC as Data, Not Hardcoded Enums

## Status
Accepted (carried over from pre-pivot decision, formalized here; vocabulary redefined in ADR-003)

## Context
Formalizes TR-002 from `docs/_legacy/tradeoffs.md`: role→module→action permissions are persisted as
data (a grid), not hardcoded in application logic, because organizations need to customize who can
do what without a code deployment.

## Decision
Keep permissions as a persisted role/module/action grid, seeded with sensible defaults per role,
customizable per user by an organization admin. See `ADR-003` for the new (compliance-domain) role
and module vocabulary that replaces the old legal-domain one.

## Alternatives Considered
- **Hardcoded fixed roles**: simpler, but does not support per-organization customization, which
  compliance/approval workflows explicitly require (different companies gate approvals differently).
- **Full ABAC/policy-engine-based authorization (Casbin/OPA)**: more powerful than needed for
  who-can-access-what; the product's actual policy-engine need (business rule evaluation, `ADR-004`)
  is a separate concern from resource authorization.

## Consequences
- Permission checks are a data lookup (cached), not a code branch — consistent with the existing,
  already-implemented and audited `PermissaoModulo` pattern.
- Migrating the seed data from legal roles to compliance roles is tracked as implementation work in
  `docs/09-planning/pivot-migration.md`.
