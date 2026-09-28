# ADR-008 — Document & Evidence Storage

## Status
Proposed (production backend decision unchanged; dev-environment tool corrected by the 2026-09-28
addendum below)

## Context
The old architecture (`docs/_legacy/`) assumed per-company VPS filesystem storage
(`/dados/empresas/{organizacao_id}/`) with encrypted off-VPS backups. JuriSense Gate's Evidence
Packages and Contract documents need durability, versioning (a `ContractVersion` must keep its
original file forever, even after re-analysis), and eventually multi-region backup — properties a
raw VPS filesystem provides only with extra scripting.

## Decision
Use **S3-compatible object storage** with per-organization key prefixes and bucket versioning
enabled: **Cloudflare R2** in production, an S3-compatible dev server in local development (added to
`docker-compose.yml`, see the addendum below for which one). All document/evidence writes go through
a single storage abstraction (`app/core/storage.py`'s `StoragePort`) in the `Contracts & Documents`
and `Evidence & Audit` contexts so the concrete backend stays swappable.

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

## Addendum (2026-09-28) — dev-environment S3-compatible server changed from MinIO to adobe/s3mock

The original implementation (EPIC-0/EPIC-1, `STORY-1.3.1`) used **MinIO** for local dev, as this ADR
originally specified. During implementation, three consecutive free-distribution paths for a local
S3-compatible dev server were tried and failed, verified live against the real registries on
2026-09-27/28:

1. **MinIO** (`minio/minio`): Docker Hub, Quay.io, and MinIO's own direct binary release download
   all now return `401`/`410` without an authenticated/paid account — MinIO discontinued free
   anonymous distribution of its server image and binary entirely.
2. **LocalStack** (`localstack/localstack`): the `latest` tag now refuses to start any service,
   including S3, without a `LOCALSTACK_AUTH_TOKEN` (paid license); its previous free-standing,
   S3-only community tag (`s3-latest`) was discontinued in the LocalStack `2026.03` release.
3. **`adobe/s3mock`** (Apache-2.0): pulls and runs with no license/token gate. Verified end-to-end
   against this project's actual `S3CompatibleStorage` (`app/core/storage.py`) client: bucket
   creation, `put_object`, `get_object`, and `generate_presigned_url` all work unmodified. **This is
   the dev server actually wired into `docker-compose.yml`.**

**This changes nothing about the production decision** (Cloudflare R2) or the application-level
abstraction (`StoragePort`) — only which container image `docker-compose.yml`'s dev-only storage
service runs. If `adobe/s3mock` also becomes unavailable in the future, re-run the same verification
(pull the candidate image, run it, exercise it with the real `S3CompatibleStorage` client, confirm no
license/auth gate) before switching `docker-compose.yml` again, and update this addendum.
