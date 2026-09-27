# ADR-016 — Security Audit as End-of-Sprint Gate

## Status
Accepted (carried over from pre-pivot decision, formalized here)

## Context
Formalizes TR-005 from `docs/_legacy/tradeoffs.md`. The practice already produced two real audit
reports (`docs/auditorias/sprint-01.md`, `sprint-02.md`) for the `Accounts` context and is
domain-agnostic — it applies equally to every new bounded context built for JuriSense Gate.

## Decision
Every sprint ends with a security audit (skills `security-review` + `insecure-defaults` + a manual
checklist that always includes an explicit tenant-isolation/cross-tenant-access test, per ADR-003).
Critical/high findings block the start of the next sprint.

## Alternatives Considered
- **Single audit at project end**: cheaper up front, findings arrive too late and too expensive to
  fix, especially for a compliance product whose entire value proposition is trustworthiness.
- **CI-only static analysis**: does not catch business-logic issues like privilege escalation across
  tenants or policy-engine bypass, which matter more here than generic code-quality issues.

## Consequences
- Roughly 3 capacity-points per sprint are spent on audit instead of features (as originally
  estimated) — carried forward as a planning assumption into `docs/09-planning/roadmap.md` and
  `backlog.md`.
- Given this product handles supplier/contract compliance decisions for other companies, this gate
  is treated as non-negotiable, not a scope-cut candidate under hackathon time pressure.
