# ADR-008 — Document & Evidence Storage

## Status
Proposed (production backend decision changed 2026-10-15 — self-hosted MinIO, built from source,
not Cloudflare R2; see that addendum, now resolved; the #138 bucket-versioning gap also resolved
2026-10-15, see that addendum; dev-environment tool corrected by the 2026-09-28 addendum)

## Context
The old architecture (`docs/_legacy/`) assumed per-company VPS filesystem storage
(`/dados/empresas/{organizacao_id}/`) with encrypted off-VPS backups. JuriSense Gate's Evidence
Packages and Contract documents need durability, versioning (a `ContractVersion` must keep its
original file forever, even after re-analysis), and eventually multi-region backup — properties a
raw VPS filesystem provides only with extra scripting.

## Decision
Use **S3-compatible object storage** with per-organization key prefixes: **self-hosted MinIO** in
production (see the 2026-10-15 addendum — originally Cloudflare R2, changed below), an
S3-compatible dev server in local development (added to `docker-compose.yml`, see the 2026-09-28
addendum for which one). All document/evidence writes go through a single storage abstraction
(`app/core/storage.py`'s `StoragePort`) in the `Contracts & Documents` and `Evidence & Audit`
contexts so the concrete backend stays swappable.

Versioning (#138, resolved 2026-10-15 — see that addendum below) is **application-modeled, not
S3-native**: every `Document` gets a fresh, content-addressed key keyed by a new `document_id`
(`app/contracts/application/document_service.py`), never overwritten — a new `ContractVersion`
always creates a new `Document` row pointing at a new key, matching `docs/03-domain/domain-
model.md`'s "Document" entity, which already documented this correctly. Bucket versioning IS also
enabled (`docker-compose.yml`'s `minio-init`, `mc version enable`) but only as a free defense-in-
depth backstop against a hypothetical future bug that reuses a key — the application's actual
versioning guarantee never depends on it.

## Alternatives Considered
- **Keep raw VPS filesystem** (`/dados/empresas/...`, the pre-pivot decision): rejected — versioning
  and durability would need to be hand-rolled; object storage gets this for free and is a similarly
  low-ops choice given the single-VPS hosting model still holds.
- **Cloudflare R2 in production** (this ADR's original decision): superseded 2026-10-15 — see that
  addendum. Kept as a documented fallback, not the default: R2's zero-egress-fee, fully-managed
  model is still the lower-ops choice if self-hosted MinIO's image-sourcing question (same
  addendum) turns out not to have a clean answer.

## Consequences
- Originally one more external dependency (object storage provider) alongside the then-external
  Postgres (Neon) and AI provider APIs; both PostgreSQL and object storage became self-hosted
  (2026-10-15 addenda, this ADR and `ADR-001`) — the AI provider APIs remain the external
  dependency the "VPS + external DB + external AI APIs" philosophy originally described.
- Evidence Package immutability (required for the Decision Passport) is guaranteed by the
  application-modeled versioning above (never-overwritten, content-addressed keys), with bucket
  versioning as an additional, redundant backstop — not by object lock, which isn't configured.

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

This directly intersected the 2026-09-28 addendum's finding: MinIO's own server image/binary
stopped being freely distributable (Docker Hub/Quay.io/direct download all return `401`/`410`
without a paid account) as of that verification — which is what left the image-sourcing path open
below, now resolved.

**Image-sourcing path (resolved, explicit instruction): build MinIO from its official AGPLv3
source**, unmodified — not the gated pre-built binary/image, not a paid Subnet account. A build
stage compiles the published `github.com/minio/minio` source (Go) into a binary, copied into the
production image's runtime stage; the pre-built image's distribution gate doesn't apply since
nothing is pulled from Docker Hub/Quay.io for this.

**License compliance criteria this path commits to following (AGPLv3, binding going forward, not
just at adoption time)** — the explicit condition under which this decision was made:
1. **Never modify MinIO's own source.** AGPLv3 §13 (the clause distinguishing it from plain GPL)
   only triggers an obligation to offer corresponding source to remote users when the *running
   program itself has been modified*. Building the unmodified, official source is not
   modification — this is the entire basis for "free, no obligations" holding here. If anyone
   ever patches/forks MinIO's own code for a production need, this analysis no longer applies and
   must be revisited before shipping that change.
2. **Never redistribute MinIO's binaries/image to third parties.** Running it as this project's
   own internal backend infrastructure is "use," not "conveying" (GPLv3 §0, inherited by AGPLv3) —
   the license's restrictions attach to distribution, not to mere use, even commercial use behind
   a closed-source SaaS. JuriSense Gate's own source is never required to be disclosed under this
   model; nor is any obligation created toward JuriSense's own end customers (they interact with
   JuriSense's API, not with MinIO's network interface directly).

This is the standard legal reading of the license text and MinIO's own public position, not a
substitute for formal legal counsel before general availability of a commercial product — noted
here as an honest caveat, not as a blocker to proceeding now.

Status: Resolved (2026-10-15) / Decision: self-hosted MinIO in production, built from official
AGPLv3 source, unmodified, never redistributed / Decision artifact: this addendum.

Not yet done as part of THIS addendum, at the time it was written (deliberately, per explicit
instruction to record the decision only): no code, `docker-compose.yml`, `Dockerfile` build stage,
or production `.env.production.example` change; no `StoragePort` config wiring; `docs/04-
architecture/deployment.md` and the other documents that still describe R2 as the production
backend have not been swept for consistency yet. **All of this was implemented later the same day**
(`minio/Dockerfile`, `docker-compose.yml`/`docker-compose.prod.yml`, `containers.md`/
`deployment.md` corrected, `#161`/`#162` updated in Plane) — see the #138 addendum below, which
covers the one piece (versioning) this addendum didn't.

## Addendum (2026-10-15) — #138: bucket-versioning gap resolved

Found in the 2026-09-28 security/pentest QA round: this ADR's original `Decision` text said
"bucket versioning enabled" without that ever actually being enabled, and without checking whether
the application even needs it. Investigation (reading `app/contracts/application/document_
service.py` and `contract_service.py`): every `Document` is created with a fresh `uuid.uuid4()`
and a storage key derived from it (`contracts/{organization_id}/{document_id}/{filename}`); no
code path updates an existing `Document` row or overwrites an existing key — a new `ContractVersion`
(re-upload, re-negotiation round) always creates a brand-new `Document` with a brand-new key. This
matches `docs/03-domain/domain-model.md`'s "Document" entity, which already correctly documented
"a `Document` is itself an immutable version; re-upload creates a new `Document`" — that document
was already right; this ADR's `Decision` text was the one that drifted from reality.

Decision: the `Document`/`ContractVersion` immutable-row, content-addressed-key model above **is**
this project's versioning mechanism (Option B from the original gap's framing) — it already fully
satisfies "per-organization document versioning" with no further application code needed. S3-
native bucket versioning (Option A) is **additionally** enabled (`docker-compose.yml`'s
`minio-init`, `mc version enable local/$STORAGE_BUCKET`, inherited by production unchanged) purely
as a zero-cost defense-in-depth backstop against a hypothetical future bug that reuses a key — the
same "storage/DB-level backstop under already-correct application logic" pattern this codebase
already uses for append-only triggers (`app/core/append_only.py`) and unique-constraint races. The
application's real versioning guarantee never depends on this backstop actually being exercised.

Status: Resolved (2026-10-15) / Decision: application-modeled versioning (already implemented,
confirmed correct) is primary; MinIO bucket versioning is an additional backstop, now enabled /
Verified live: two writes to the same key under the now-versioned bucket both survive and are
individually retrievable (`mc ls --versions`), confirming the backstop actually works, not just
that the command ran / Decision artifact: this addendum, `docs/adr/ADR-008-document-evidence-
storage.md`'s `Decision`/`Consequences` sections (corrected above), `docker-compose.yml`.
