# ADR-004 — Policy Engine Expression Language

## Status
Proposed — pending prototype/benchmark (see Resolution below)

## Context
The Policy Engine is a core competitive component: organizations must be able to express rules like
"if the contract processes personal data and has no DPA, BLOCK" as data, not code, versioned, and
safely evaluated against untrusted-ish structured input (AI-extracted contract/supplier data).
Research (2026-09-27) compared four candidate technologies:

- **OPA (Rego)**: the most mature general-purpose policy engine (CNCF), dominant for
  infrastructure/API/Kubernetes authorization. Requires running Rego as a language most business
  users cannot read or author directly, and typically runs as a sidecar/service — operational
  overhead not justified for evaluating business rules over a few hundred contracts/suppliers.
- **AWS Cedar**: fast, schema-validated, purpose-built for **application authorization**
  (who-can-do-what-to-which-resource), not for expressing arbitrary business conditionals over
  extracted document data. AWS-specific tooling, thin ecosystem outside that use case.
- **CEL (Common Expression Language)**: a small, sandboxed, fast expression language designed
  exactly for "evaluate a boolean/typed expression against a data context inside your own process,"
  with official Python bindings (`cel-python`). No external service required.
- **JSONLogic**: even lighter, JSON-native rule expressions, trivial to store/version/diff, less
  expressive for complex boolean logic than CEL, but easier for a future no-code rule builder UI to
  generate safely.

## Decision
Adopt a **YAML rule authoring format** (`id`, `name`, `when`, `result`, `severity`, `approver_role`)
as the durable, versioned storage format for policies (see `docs/03-domain/policy-engine.md` for the
full schema and examples). The `when` clause compiles to a **CEL expression** evaluated in-process
against a normalized evidence context (supplier + contract + AI-extraction output). JSONLogic is
kept as the fallback/alternative compilation target specifically for rules authored through a future
visual/no-code rule builder, where JSONLogic's tree structure is easier to generate safely than raw
CEL text.

## Resolution (why this is "Proposed," not "Accepted")
This decision needs a short technical spike (Phase 4 of the roadmap) to validate: (1) `cel-python`
performance and packaging maturity for our use case, (2) how cleanly the YAML `when` clause maps to
CEL syntax without leaking CEL's raw syntax to non-technical policy authors, (3) whether rule
conflict/priority handling (documented in `policy-engine.md`) is easier in CEL or JSONLogic in
practice. The spike output updates this ADR's status to Accepted or reverses the CEL/JSONLogic
priority.

## Alternatives Considered
See Context above (OPA, Cedar) — both rejected as wrong-fit, not "worse at everything."

## Consequences
- No new service to operate for v1 (CEL runs in-process); simpler ops story for the VPS deployment.
- Policy authors interact with YAML + a constrained `when` grammar, not raw CEL/JSONLogic — the
  authoring UI is responsible for hiding the compilation target.
- If OPA/Cedar-style fine-grained resource authorization is later needed (e.g., "who can view which
  specific supplier record"), that is a **separate** concern from this business-rule engine and
  should reuse the existing RBAC model (ADR-003), not this Policy Engine.
