# MinIO server + the `mc` client, built from their official AGPLv3 source -- never the
# pre-built image/binary, whose free distribution MinIO gated behind a paid account
# (found 2026-09-28, `docs/adr/ADR-008-document-evidence-storage.md`'s addendum). This
# build clones the exact tagged release and compiles it unmodified: no patches, no forks.
# That is the entire basis for this being free/obligation-free under AGPLv3 (see that
# ADR's 2026-10-15 addendum for the full license analysis) -- if anyone ever patches
# MinIO's own source for a production need, re-read that addendum before shipping it.
#
# `mc` ships in the same image only to run the one-shot bucket-creation step
# (docker-compose's `minio-init` service) -- the OSS server has no env-var equivalent of
# s3mock's old `COM_ADOBE_TESTING_S3MOCK_STORE_INITIAL_BUCKETS` auto-create-bucket
# behavior, so `mc mb` against the already-running server is the standard way to do it.
#
# Pin versions by re-running:
#   curl -s https://api.github.com/repos/minio/minio/tags?per_page=1
#   curl -s https://api.github.com/repos/minio/mc/tags?per_page=1
# before bumping MINIO_VERSION/MC_VERSION below -- verified against the real GitHub API
# on 2026-10-15, the two latest tags at that time.

FROM golang:1.24.13-bookworm AS builder
WORKDIR /build

ARG MINIO_VERSION=RELEASE.2025-10-15T17-29-55Z
ARG MC_VERSION=RELEASE.2025-08-13T08-35-41Z

RUN git clone --depth 1 --branch "${MINIO_VERSION}" https://github.com/minio/minio.git minio-src \
    && CGO_ENABLED=0 go -C minio-src build -trimpath -ldflags "-s -w" -o /out/minio .

RUN git clone --depth 1 --branch "${MC_VERSION}" https://github.com/minio/mc.git mc-src \
    && CGO_ENABLED=0 go -C mc-src build -trimpath -ldflags "-s -w" -o /out/mc .

FROM debian:bookworm-slim AS runtime
# curl: used by docker-compose's healthcheck against /minio/health/live -- nothing in the
# application itself needs it.
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 1001 miniogroup \
    && useradd --system --uid 1001 --gid miniogroup minio \
    && mkdir -p /data && chown minio:miniogroup /data

COPY --from=builder /out/minio /usr/local/bin/minio
COPY --from=builder /out/mc /usr/local/bin/mc

USER minio
EXPOSE 9000 9001
ENTRYPOINT ["minio"]
CMD ["server", "/data", "--console-address", ":9001"]
