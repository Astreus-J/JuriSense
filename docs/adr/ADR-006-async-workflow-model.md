# ADR-006 — Async Processing & Approval Workflow Model

## Status
Accepted

## Context
Two different "asynchronous" needs exist and must not be conflated: (1) short-lived background
**tasks** (AI extraction, OCR, sending notification emails, calling external verification APIs),
and (2) long-lived **approval workflows** that span days or weeks and involve human decisions
(Legal review, Director sign-off). Redis is already provisioned in `docker-compose.yml`; no task
queue or workflow engine exists yet in the codebase.

## Decision
- **Async tasks**: Celery + Redis (broker/result backend), consistent with the architecture
  described in the product's original planning docs and the already-provisioned Redis service.
  Used for AI extraction jobs, document OCR, external verification calls, and notification
  dispatch.
- **Approval workflows**: modeled as an explicit **database-backed state machine**
  (`ApprovalWorkflow` → `ApprovalRequest` with a `status` column, allowed transitions enforced in
  the application layer, and an `AuditEvent` emitted on every transition) — **not** a dedicated
  workflow engine (Temporal, Inngest, AWS Step Functions). Celery tasks are used only to trigger
  time-based transitions (e.g., approval reminders/timeouts), not to hold workflow state.

## Alternatives Considered
- **Temporal / Inngest / Hatchet**: purpose-built for durable, long-running workflows with retries
  and complex branching; rejected for v1 because it adds a new piece of infrastructure to operate
  and learn, for a workflow shape (linear approval chains with a handful of states) that a state
  machine models adequately. Revisit if approval logic grows materially more complex (e.g., dynamic
  parallel multi-approver graphs with SLA escalation across many organizations).
- **Celery alone for workflow state**: rejected — Celery tasks are not designed to hold long-lived
  state reliably across days/weeks; using it that way invites lost-task and duplicate-execution
  bugs.

## Consequences
- One new piece of infrastructure to operate (Celery worker + Redis, already provisioned) rather
  than two.
- Approval state is queryable directly via SQL for audit/reporting, which matters for the Decision
  Passport (`docs/03-domain/evidence.md`).
- If a workflow engine becomes necessary later, the state-machine's transition/audit-event model
  translates directly into that engine's activity log — this is not a dead end, just a smaller
  first step.
