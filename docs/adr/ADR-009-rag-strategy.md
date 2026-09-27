# ADR-009 — Retrieval Strategy (RAG)

## Status
Accepted

## Context
Several features benefit from retrieval over a corpus: matching contract clauses against a
company's policy playbook, searching prior compliance decisions for precedent, and (later)
retrieving relevant legislation/regulatory text. The database is already PostgreSQL (external,
Neon-hosted).

## Decision
Use **PostgreSQL + `pgvector`** for embeddings storage and similarity search; no standalone vector
database (Pinecone, Weaviate, Qdrant) for v1. Combine vector search with plain full-text search
(Postgres `tsvector`) and metadata filters (organization, document type, policy version) for hybrid
retrieval, per `docs/05-ai/rag.md`.

## Alternatives Considered
- **Standalone vector DB**: better at very large scale / advanced ANN indexing, but adds an
  operational dependency the current data volume (hundreds to low thousands of documents per
  organization, at least through the hackathon and early customer stage) does not justify.

## Consequences
- One fewer service to run/pay for/operate.
- Revisit only if query latency or index size data (once real usage exists) shows `pgvector`
  becoming a bottleneck — tracked as a future ADR trigger, not a current TBD.
