# Project Management (Plane Workflow)

Repository documentation (`docs/`) is the source of truth for architecture, product concepts,
technical decisions, business rules, and ADRs. **Plane is the source of truth for work planning,
execution, issues, priorities, progress, milestones, dependencies, and releases.** When a
requirement changes, the flow is always: architecture/product decision → repository documentation →
Plane execution work. Never let the Plane backlog become an alternative specification disconnected
from the repository (see `docs/09-planning/backlog.md`, which Plane's issue tree is derived from).

Plane workspace: `astreus-develop`. Project: **JuriSense** (identifier `JURI`). The project's Plane
configuration (states, labels, modules, cycles, description) is defined as code in
`project-management/plane/` and applied by `scripts/plane/bootstrap.py` — see
`project-management/plane/README.md` for how to run it. Edit the YAML/Markdown there, not the Plane
UI directly, so the two never drift.

## Issue hierarchy

EPIC (one per roadmap phase, `docs/09-planning/roadmap.md`) → FEATURE → STORY, using Plane's
`parent`/sub-issue relationship. Phases 0–8 (the Hackathon Cut) are broken down to STORY level with
full acceptance criteria; Phases 9–11 (post-hackathon) exist as EPIC/FEATURE-level issues only,
refined into stories closer to when that work starts. A handful of cross-cutting Security/DevOps
seed issues and one hackathon-submission tracking issue exist outside this per-phase hierarchy — see
`scripts/plane/issues_data.py`.

## Modules

One module per roadmap phase, plus four cross-cutting modules (Frontend, Security, DevOps &
Infrastructure, Hackathon). Modules answer **what** part of the system a piece of work belongs to;
labels answer **what kind** of work it is — they complement each other, they don't duplicate.
Full list and descriptions: `project-management/plane/modules.yaml`.

## States

| State | Meaning |
|---|---|
| Backlog | Unplanned, or not yet ready for implementation. |
| Ready | Specification and acceptance criteria complete; available to start (Definition of Ready met). |
| In Progress | Actively being implemented. |
| In Review | Code review, validation, or QA. |
| Blocked | Cannot proceed due to an unresolved dependency or problem. |
| Done | Acceptance criteria satisfied and merged (Definition of Done met). |
| Cancelled | Intentionally removed from scope. |

## Priorities

| Priority | Meaning |
|---|---|
| Urgent | Critical blocker: security incident, release blocker, hackathon-critical-path item (spikes on the ADR-004/ADR-007 timeline, the core aggregation engine). |
| High | Important for the current milestone, or a foundational dependency later work needs. |
| Medium | Normal planned work. |
| Low | Improvements, polish, optional enhancements. |
| None | Ideas or items awaiting prioritization. |

## Label taxonomy

`category:value`, never bare words (`backend`, `Backend`, `backend-task` are all wrong — use
`area:backend`). Categories: `type:*` (kind of work), `area:*` (stack layer), `product:*`,
`scope:*` (hackathon/commercial/foundation/enterprise/international), `risk:*` (mirrors
`docs/09-planning/risks.md`), `tech:*` (kept minimal), `mvp:required` (the fallback-MVP filter, per
`docs/08-hackathon/fallback-mvp.md`). Full list: `project-management/plane/labels.yaml`.

To answer "show me everything required to freeze a working hackathon MVP today": filter by
`mvp:required`. To see the hackathon scope broadly: filter by `scope:hackathon` (everything through
Phase 8) or the corresponding modules.

## Cycles

1-week cycles through the hackathon push (Cycle 0, this week, through Cycle 5, the week judging
opens), matching `docs/09-planning/milestones.md`'s week numbering. Post-hackathon cycles are
intentionally not pre-created — create them after Milestone M4 lands, using real velocity instead of
a pre-hackathon guess. Full list: `project-management/plane/cycles.yaml`.

## Definition of Ready

An issue is Ready when: the goal is understood; acceptance criteria exist; dependencies are known
(not necessarily already resolved); the relevant architecture/domain documentation exists; no
blocking product decision remains. Readiness does not require every upstream ticket to already be
merged — sequencing within a milestone is a cycle-planning concern, not a Ready/Backlog gate.

## Definition of Done

A code issue is Done only when: implementation is complete; tests pass; lint/typecheck pass;
security implications have been reviewed (see `docs/adr/ADR-016-security-audit-as-sprint-gate.md`);
relevant observability was added; documentation was updated where the change affects it; acceptance
criteria are satisfied; code was reviewed; CI passed. For AI features, the relevant evaluation
(`docs/05-ai/evaluation.md`) has run. For anchoring/smart-contract work, the corresponding tests
(`docs/07-engineering/testing-strategy.md`) have passed.

## Branch naming

`feature/<slug>`, `fix/<slug>`, `refactor/<slug>`, `docs/<slug>`, `chore/<slug>`,
`spike/<slug>`. Example: `feature/supplier-onboarding`, `spike/chainlink-cre` (or, given ADR-007's
actual direction, `spike/anchoring-provider`). All lowercase, hyphenated, in English.

## Commit convention

[Conventional Commits](https://www.conventionalcommits.org/): `type(scope): summary`, e.g.
`feat(suppliers): add supplier onboarding`, `fix(auth): enforce tenant isolation`,
`test(contracts): add extraction regression cases`, `docs(architecture): document evidence
pipeline`. Everything in English (see the project-wide language rule in `coding-standards.md`).

## Pull request workflow

Every PR should include: Summary, Related Issue (link the Plane issue), Changes, Testing, Security
Impact, Architecture Impact (if any), Checklist. PR titles are in English and start with a verb,
matching the linked issue's intent.

## Release process

No formal "release" object exists in this Plane instance's public API surface — releases are
represented as **cycles** reaching their target date plus the **Hackathon** module/tracking issue
for the Legal Hack 2026 submission specifically. Post-hackathon, define a lightweight versioning
scheme (`v0.1.0` Foundation → ... → `v1.0.0` Commercial Beta, per the roadmap phases) once real
deployment cadence exists — not invented here ahead of need.

## Change management

New work is always classified before an issue is created: Bug, Feature, Research/Spike, Technical
Debt, Security, Documentation, or Infrastructure — matching a `type:*` label. Don't create
unclassified, vague issues ("fix stuff", "improve AI").

## Keeping Plane in sync with the repository

If `docs/09-planning/roadmap.md` or `backlog.md` changes materially (a phase is re-scoped, a story is
added or dropped), update `scripts/plane/issues_data.py` to match and re-run
`scripts/plane/bootstrap.py` — it is idempotent and safe to re-run at any time; it will update
existing issues by title rather than duplicating them.
