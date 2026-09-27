# Observability

How JuriSense Gate answers "what is the system doing right now, and what did it do at decision
time T" — logging, metrics, and tracing, across all 8 bounded contexts, plus what makes this
product's observability different from a generic CRUD app: the `AuditEvent` log is a business
signal, not just an ops one, and AI calls need their own dedicated observability.

## Structured logging

- All logs are **structured JSON**, one object per line, never freeform `print`/string-formatted log
  messages — this is a hard requirement, not a preference, because logs are the primary debugging
  surface for a single-VPS deployment with no dedicated APM budget yet (`docs/00-project/overview.md`
  hosting model).
- Every log line carries a minimum common envelope: `timestamp`, `level`, `logger` (module path),
  `message`, `request_id` (see below), `organization_id` (when known — nullable for system-level
  logs), and `bounded_context` (`accounts`, `suppliers`, `contracts`, `policies`, `approvals`,
  `evidence`, `ai_services`, `integrations`).
- **Never log secrets or sensitive payloads**: no password (hashed or not), no full JWT, no raw
  contract text, no supplier PII beyond what's needed to identify the record (an `id` and
  `organization_id`, not a CPF/CNPJ in plaintext in a log line). This mirrors the discipline already
  verified for `Accounts` in `docs/auditorias/sprint-01.md` ("senha nunca aparece em logs ou
  respostas" — extended here as a project-wide, English-stated rule: passwords, tokens, and personal
  data never appear in logs or error responses).
- All new logging code writes English messages, per the project-wide English-only rule
  (`docs/07-engineering/coding-standards.md`) — this includes log messages emitted by the still-Portuguese
  `Accounts` context going forward for any *new* log line added to it; existing Portuguese log
  strings are tracked debt like everything else in that context.

## Correlation / request IDs

- Every HTTP request gets a `request_id` (generated or propagated from `X-Request-ID`, per
  `docs/07-engineering/api-standards.md`), attached to every log line emitted while handling it via a
  context-local variable (Python `contextvars`), not passed explicitly through every function
  signature.
- The `request_id` is propagated into any Celery task enqueued as part of handling that request
  (passed as a task argument or task header), so a background AI-extraction job's logs can be joined
  back to the originating HTTP request — critical for debugging "why did this contract's analysis
  fail" days after the request that triggered it.
- Celery tasks that are **not** triggered by a specific HTTP request (scheduled jobs, retries) get
  their own generated `task_id`-based correlation id instead, so every log line always has *some*
  correlation identifier, HTTP-triggered or not.

## What to log per bounded context

- **Accounts (Identity & Organizations)**: authentication events (login success/failure — without
  the password, obviously), token issuance/revocation, permission-check denials (who was denied what,
  useful for both debugging and detecting probing behavior).
- **Suppliers**: every `SupplierCheck` run (which sources were queried, latency per source, whether
  a sanctions hit occurred — the hit itself, not the full raw response body).
- **Contracts & Documents**: document upload (size, mime type, hash — never content), extraction job
  start/completion/failure with confidence scores.
- **Policy & Compliance**: every `ComplianceReview` run (which `PolicyVersion`, which rules fired,
  final aggregated status) — this overlaps heavily with the `AuditEvent` log by design (see below);
  application logs here are for *debugging the engine*, the `AuditEvent` is the durable business
  record.
- **Approvals & Decisions**: every state transition (`ApprovalRequest` status changes, `Decision`
  creation/override) logged with actor id.
- **Evidence & Audit**: `EvidencePackage` creation, `BlockchainAnchor` submission/confirmation
  latency and provider used — anchoring failures are logged at a level that pages/alerts, not just
  `info`, given they threaten the product's core auditability promise.
- **AI Services**: see the dedicated section below.
- **Integrations**: every inbound webhook received (source, event type, processing outcome) and
  every outbound call to a third-party system.

## AI-specific observability

AI calls need more than a log line because cost, latency, and quality all matter and are not visible
from a generic request log — the detailed methodology (what fields, what dashboards, what alerting
thresholds) is specified in `docs/05-ai/observability.md`; this document states the cross-cutting
requirement that ties it into the rest of the system:

- Every AI Gateway call (`extract()`, `classify()`, `summarize()` — ADR-005) is logged with:
  provider used, model, task type, input token count, output token count, latency, whether fallback
  to the secondary provider was triggered, and — critically — the **provenance metadata** attached to
  the output (source document id, page, span, confidence), because that provenance is itself a
  correctness property worth being able to audit independent of the extracted content.
- AI Gateway logs use the same `request_id` correlation as everything else, so an AI call can be
  traced back to the `ComplianceReview` or `ContractVersion` that triggered it.
- Cost is tracked per organization (token counts convert to a cost estimate), both because it's an
  operational input to the AI-provider cost-threshold question (`ADR-005`'s open TBD on when
  self-hosting becomes worth it) and because plan limits on "AI executions" (`ADR-014`,
  `docs/02-business/pricing-strategy.md`) need real usage data to enforce and to price correctly.

## Audit-event-as-observability

The `AuditEvent` log (`Evidence & Audit` context, `docs/03-domain/domain-model.md`,
`docs/03-domain/audit.md`) is **append-only, immutable, and already a durable business record** by
domain design (`docs/07-engineering/database-standards.md`'s append-only enforcement). It also
functions as a first-class **observability signal**, and this document deliberately does not
duplicate a second business-event pipeline to get that:

- Anything an operator or a customer's Compliance/Audit team would want to know "did this happen,
  and when" — a decision made, an override applied, a policy published, an approval granted — is
  already captured as an `AuditEvent` by domain requirement, independent of observability concerns.
  Treat that log as a queryable data source for building operational dashboards (e.g. "decisions per
  day per organization," "override rate," "average time-to-decision") rather than re-deriving the
  same facts from application logs.
- The distinction that matters: **application logs** (this document, mostly) are for *engineers*
  debugging the system's behavior and are allowed to be verbose, ephemeral, and imperfect.
  **`AuditEvent`s** are for *the business* (and potentially a regulator or auditor) answering "what
  happened," are held to the append-only/never-edited standard, and are far more sparse and
  deliberate about what gets recorded. Do not log something as an `AuditEvent` just because it would
  be a convenient dashboard metric — that's what application logs plus a metrics pipeline are for.

## Metrics and tracing

**Status: TBD** — the exact tracing/metrics/error-tracking vendor.
**Current preferred option:** **OpenTelemetry** (vendor-neutral instrumentation — SDK + auto-instrumentation
for FastAPI, SQLAlchemy, httpx, and Celery) for traces and metrics, exported to a lightweight
self-hosted or low-cost backend appropriate for the single-VPS hosting model (a self-hosted Grafana
stack — Tempo/Loki/Prometheus — or a hosted low-cost tier of a service like Sentry or Grafana Cloud),
plus **Sentry** (or a comparable lightweight error-tracking tool) specifically for exception capture
and alerting, since structured logs alone are a poor interface for "tell me immediately when
something new breaks."
**Why undecided:** no production traffic exists yet to size cost/retention needs against, and the
single-VPS hosting model constrains how much can run locally (a full Grafana stack is real memory/CPU
budget on a VPS that also runs the app, Celery workers, and Redis) versus how much should be an
external low-cost SaaS tier — this needs a short, dedicated evaluation weighing self-hosted cost
(ops burden, VPS resources) against a hosted tier's dollar cost at expected early-stage volume.
**Resolution:** a lightweight vendor evaluation (half a day, not a research project) before Phase 6–7
of the roadmap when real users start generating meaningful traffic; OpenTelemetry instrumentation is
added incrementally regardless of backend choice, since it is what makes the backend swappable
without re-instrumenting the code later.
**Decision artifact:** a future ADR once the evaluation concludes.

In the meantime, structured logs (above) plus the existing FastAPI/Celery/Redis stack's own basic
health signals (the `/api/health` endpoint, Redis's healthcheck already in `docker-compose.yml`) are
the baseline — sufficient for the hackathon cut, not sufficient once paying customers depend on the
product's uptime.
