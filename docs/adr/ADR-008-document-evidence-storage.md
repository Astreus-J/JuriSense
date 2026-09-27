# ADR-008 — Document & Evidence Storage

## Status
Proposed

## Context
The old architecture (`docs/_legacy/`) assumed per-company VPS filesystem storage
(`/dados/empresas/{organizacao_id}/`) with encrypted off-VPS backups. JuriSense Gate's Evidence
Packages and Contract documents need durability, versioning (a `ContractVersion` must keep its
original file forever, even after re-analysis), and eventually multi-region backup — properties a
raw VPS filesystem provides only with extra scripting.

## Decision
Use **S3-compatible object storage** with per-organization key prefixes and bucket versioning
enabled: **Cloudflare R2** in production, **MinIO** in local development (added to
`docker-compose.yml`). All document/evidence writes go through a single storage abstraction in the
`Contracts & Documents` and `Evidence & Audit` contexts so the concrete backend stays swappable.

## Alternatives Considered
- **Keep raw VPS filesystem** (`/dados/empresas/...`, the pre-pivot decision): rejected — versioning
  and durability would need to be hand-rolled; object storage gets this for free and is a similarly
  low-ops choice given the single-VPS hosting model still holds (R2 is external but billed
  per-use, not a new server to manage).
- **Self-hosted MinIO in production too**: viable cost-saving alternative if R2 pricing becomes a
  concern at scale — kept as a documented fallback, not the default, because R2's zero-egress-fee
  model fits a document-heavy product better initially.

## Consequences
- One more external dependency (object storage provider) alongside the existing external Postgres
  (Neon) and AI provider APIs — consistent with the "VPS + external DB + external AI APIs" hosting
  philosophy already established for this project.
- Evidence Package immutability (required for the Decision Passport) is easier to guarantee with
  object lock / versioning than with plain filesystem writes.
