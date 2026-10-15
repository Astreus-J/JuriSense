# ADR-008 — Document & Evidence Storage

## Status
Proposed (production backend decision changed 2026-10-15 — self-hosted MinIO, not Cloudflare R2;
see that addendum for the one open question this leaves; dev-environment tool corrected by the
2026-09-28 addendum)

## Context
The old architecture (`docs/_legacy/`) assumed per-company VPS filesystem storage
(`/dados/empresas/{organizacao_id}/`) with encrypted off-VPS backups. JuriSense Gate's Evidence
Packages and Contract documents need durability, versioning (a `ContractVersion` must keep its
original file forever, even after re-analysis), and eventually multi-region backup — properties a
raw VPS filesystem provides only with extra scripting.

## Decision
Use **S3-compatible object storage** with per-organization key prefixes and bucket versioning
enabled: **self-hosted MinIO** in production (see the 2026-10-15 addendum — originally Cloudflare
R2, changed below), an S3-compatible dev server in local development (added to `docker-compose.yml`,
see the 2026-09-28 addendum for which one). All document/evidence writes go through a single storage
abstraction (`app/core/storage.py`'s `StoragePort`) in the `Contracts & Documents` and `Evidence &
Audit` contexts so the concrete backend stays swappable.

## Alternatives Considered
- **Keep raw VPS filesystem** (`/dados/empresas/...`, the pre-pivot decision): rejected — versioning
  and durability would need to be hand-rolled; object storage gets this for free and is a similarly
  low-ops choice given the single-VPS hosting model still holds.
- **Cloudflare R2 in production** (this ADR's original decision): superseded 2026-10-15 — see that
  addendum. Kept as a documented fallback, not the default: R2's zero-egress-fee, fully-managed
  model is still the lower-ops choice if self-hosted MinIO's image-sourcing question (same
  addendum) turns out not to have a clean answer.

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

**This changed nothing about the production decision at the time** (still Cloudflare R2 as of this
writing — see the 2026-10-15 addendum below for the later change) or the application-level
abstraction (`StoragePort`) — only which container image `docker-compose.yml`'s dev-only storage
service runs. If `adobe/s3mock` also becomes unavailable in the future, re-run the same verification
(pull the candidate image, run it, exercise it with the real `S3CompatibleStorage` client, confirm no
license/auth gate) before switching `docker-compose.yml` again, and update this addendum.

## Addendum (2026-10-15) — production backend changed from Cloudflare R2 to self-hosted MinIO

Decision (explicit instruction): production object storage is **self-hosted MinIO**, not Cloudflare
R2 — consistent with how this project's own Plane instance (project management, `project-management/
plane/`) is already deployed. Rationale: the single-VPS hosting model already runs other self-hosted
services; adding R2 means one more external SaaS dependency (billing, API surface, data-residency
question) when a self-hosted option that's already proven to run this project's other tooling is
available instead. `StoragePort` (`app/core/storage.py`) needs no interface change — MinIO is
S3-compatible, same as R2; only the production `STORAGE_ENDPOINT_URL`/credentials/bucket config
differs, same shape of change the dev environment already went through (`adobe/s3mock`, 2026-09-28
addendum above).

This directly intersects the 2026-09-28 addendum's finding: MinIO's own server image/binary stopped
being freely distributable (Docker Hub/Quay.io/direct download all return `401`/`410` without a
paid account) as of that verification. Documenting the decision now, before resolving exactly how
the production image will be sourced:

Status: TBD / Current preferred option: self-hosted MinIO in production, exact image-sourcing path
undecided (candidates, not yet evaluated: (a) the same source/account/mirror already used to run
this project's own Plane deployment's MinIO instance — the most direct read of "assim como o Plane
usa"; (b) building MinIO from its still-source-available AGPLv3 repository; (c) a paid MinIO
AGPLv3/Subnet account) / Why undecided: this was recorded as a documentation-only decision per
explicit instruction, not yet implemented / Resolution: before `#161`/`#162` (re-scoped in Plane
to self-hosted MinIO, formerly Cloudflare R2 cutover) are implemented, confirm which image-sourcing
path applies, the same way the 2026-09-28 addendum verified `adobe/s3mock` end-to-end before wiring
it into `docker-compose.yml` / Decision artifact: this addendum; update it once the sourcing path
is confirmed, rather than adding a third addendum for the same open question.

Not yet done as part of this addendum (deliberately, per explicit instruction to record the
decision only): no code, `docker-compose.yml`, or production `.env.production.example` change; no
`StoragePort` config wiring; `docs/04-architecture/deployment.md` and the other documents that still
describe R2 as the production backend have not been swept for consistency yet — this ADR is the
authoritative record of the change, those are a follow-up once the image-sourcing TBD above is
resolved and real implementation starts.
