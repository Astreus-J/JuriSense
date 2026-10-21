# Deployment runbook

Practical, step-by-step companion to `docs/04-architecture/deployment.md` (the target
architecture) — this document is how to actually stand up `docker-compose.prod.yml` on a
VPS. `docs/07-engineering/ci-cd.md` §11 describes this as "`docker compose pull && docker
compose up -d` against the production compose file, or an equivalent SSH-based deploy
step" — this is that compose file and that step, spelled out.

## 1. VPS prerequisites

- A Linux VPS with Docker Engine and the Compose plugin installed (`docker compose
  version` should print v2.x). Any mainstream distro works; nothing here is
  distro-specific.
- A non-root user in the `docker` group (don't run this as root day to day).
- Outbound HTTPS open (AI provider APIs, SMTP, the anchoring network). Inbound: only 80
  (and 443 if this container terminates TLS itself — see `nginx/README.md`) need to be
  reachable from the internet. Postgres/Redis/MinIO are never published to the host in
  `docker-compose.prod.yml`, so there is nothing else to open.
- DNS for your domain pointed at the VPS (an `A`/`AAAA` record, or a Cloudflare proxied
  record if you're fronting with Cloudflare per `deployment.md`'s diagram).

## 2. First deploy

```sh
# on the VPS
git clone <this repo's URL> jurisense && cd jurisense
git checkout develop   # or whichever branch/tag you're deploying

cp .env.production.example .env.production
cp backend/.env.production.example backend/.env
# edit both -- see the comments in each file for what's required and how to generate
# each secret. docker-compose.prod.yml's own header comment lists the exact two files.

docker compose -p jurisense-prod -f docker-compose.prod.yml --env-file .env.production up -d --build
```

What happens on `up`: Postgres and MinIO start and become healthy, `minio-init` creates
the storage bucket, the `backend` container runs `alembic upgrade head` before starting
`uvicorn` (so the database schema is always current for the image you just built), the
Celery worker/beat start, and `nginx` comes up last, routing `/api/*` to `backend` and
everything else to `frontend`.

Verify:

```sh
docker compose -p jurisense-prod -f docker-compose.prod.yml --env-file .env.production ps
curl -s http://localhost/api/health          # process is up
curl -s http://localhost/api/health/ready    # process is up AND can reach Postgres
# or https://your-domain.example/api/health(/ready) once DNS/TLS are live
```

## 3. Seeding the first organization

There is no seed step wired into `up` on purpose — the first organization and admin user
are created through the product's own signup/invite flow, not injected directly into the
database. If you need a demo/seed tenant on this deploy the way `backend/scripts/
seed_demo.py` does for local dev, run it against the production containers explicitly and
deliberately:

```sh
docker compose -p jurisense-prod -f docker-compose.prod.yml --env-file .env.production exec backend \
  python scripts/seed_demo.py
```

Only do this against a tenant you intend to be throwaway/demo data — it is not an
idempotent "ensure the real first customer exists" step.

## 4. Redeploying (code changes)

```sh
cd jurisense && git pull
docker compose -p jurisense-prod -f docker-compose.prod.yml --env-file .env.production up -d --build
```

This rebuilds only the images whose build context changed, runs the (idempotent)
migration again as part of the `backend` container's startup command, and recreates only
the containers whose image or config changed — `postgres`/`redis`/`minio`'s named volumes
are untouched. There is no separate "migrate" step to remember: it's baked into the
backend command on every start, by design (`docker-compose.prod.yml`'s own comment).

## 5. Logs and basic troubleshooting

```sh
docker compose -p jurisense-prod -f docker-compose.prod.yml --env-file .env.production logs -f backend
docker compose -p jurisense-prod -f docker-compose.prod.yml --env-file .env.production logs -f celery-worker
```

- **Backend container exits immediately on a fresh deploy**: almost always a missing/
  placeholder required production secret — `app/core/config.py`'s
  `_require_production_secrets` validator raises a specific, named error for each one
  (JWT_SECRET_KEY, STORAGE_ACCESS_KEY/SECRET_KEY, INTEGRATION_CREDENTIALS_ENCRYPTION_KEY,
  SMTP_HOST, OPENROUTER_API_KEY) and refuses to boot rather than run half-configured — the
  log line names exactly which one.
- **First contract upload fails**: confirm `OPENROUTER_API_KEY` (or, if
  `AI_GATEWAY_PROVIDER=gemini`, also `GEMINI_API_KEY`) is a real key, not a placeholder —
  note `backend/.env.production.example`'s comment that the startup check currently
  requires `OPENROUTER_API_KEY` regardless of which provider is actually selected.
- **Password reset / invite emails never arrive**: check `SMTP_HOST`/`SMTP_USER`/
  `SMTP_PASSWORD` — without a working SMTP config those links are otherwise written to the
  backend's log instead of emailed (see the validator's own comment in `config.py`), which
  is also why production refuses to boot with `SMTP_HOST` unset at all.
- **A decision's blockchain anchor never resolves**: check which `ANCHORING_PROVIDER` is
  selected; `transparency_log` (the default) needs no external credentials, but
  `constellation_digital_evidence` needs all four `CONSTELLATION_DED_*` variables set, or
  the backend refuses to boot naming the missing ones.

## 6. Backups

- **Postgres**: `docker compose -p jurisense-prod -f docker-compose.prod.yml --env-file .env.production
  exec postgres pg_dump -U $POSTGRES_USER $POSTGRES_DB > backup.sql` (wire this into a
  cron job on the VPS; this repo doesn't ship an automated backup schedule yet — track
  that as a follow-up before relying on this deploy for real customer data).
  `postgres_data` is a named Docker volume either way, so it survives `docker compose
  down` (without `-v`) and container recreation on its own.
- **MinIO**: `minio_data` is also a named volume with the same survive-recreation
  property; for off-VPS backup, use `mc mirror` (the same `mc` binary already built into
  `./minio/Dockerfile`) to copy the bucket to another location on a schedule.

## 7. What's deliberately not automated yet

- No CI/CD pipeline triggers this deploy automatically — `docs/07-engineering/ci-cd.md`
  §11 explicitly treats deploy as manually-triggered until the team decides continuous
  deployment is appropriate. Running the commands in §2/§4 above over SSH is the current
  "pipeline."
- No zero-downtime/blue-green deploy — `up -d --build` recreates the `backend`/`frontend`
  containers in place, which means a brief gap while the new container starts. Acceptable
  at current scale/traffic; revisit if that stops being true.
- No automated TLS certificate renewal unless you set up certbot's own cron/systemd timer
  per `nginx/README.md` — Cloudflare-fronted deploys don't need this at all (Cloudflare
  manages the edge certificate).
