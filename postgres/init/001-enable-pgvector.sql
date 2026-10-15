-- ADR-009: pgvector backs embeddings storage/similarity search for RAG retrieval.
-- Runs once, automatically, on first container initialization (official postgres
-- image convention: any .sql/.sh file under /docker-entrypoint-initdb.d/ runs exactly
-- once, against the fresh database, and never again on subsequent container starts).
-- Not yet used by any application code as of 2026-10-15 (RAG/AI Services is future
-- work) -- enabled now so the extension is already present when that work starts,
-- consistent with the pgvector/pgvector:pg17 base image already bundling the library.
CREATE EXTENSION IF NOT EXISTS vector;
