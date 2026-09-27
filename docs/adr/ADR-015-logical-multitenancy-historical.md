# ADR-015 — Logical Multi-Tenancy by organization_id (historical)

## Status
Accepted (historical) — consolidated and extended by ADR-003

## Context
Formalizes TR-004 from `docs/_legacy/tradeoffs.md`: every tenant-owned table carries
`organizacao_id` (renamed `organization_id`), isolation enforced in repositories, mandatory
cross-tenant-access test in every audit.

## Decision
This decision is unchanged in substance and is restated, extended, and made authoritative in
**ADR-003** (which also redefines the RBAC vocabulary for the new domain). This ADR is kept for
historical traceability back to the original TR-004 record; refer to ADR-003 for the current,
complete statement.

## Alternatives Considered
See ADR-003.

## Consequences
See ADR-003. No independent consequences beyond what ADR-003 states.
