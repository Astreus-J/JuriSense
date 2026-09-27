# Plane configuration as code

This directory is the editable source for the JuriSense Plane project's configuration. Edit these
files, not the Plane UI directly, then run the bootstrap script to apply the change — this keeps the
repository and the live Plane workspace from drifting apart. See
`docs/07-engineering/project-management.md` for the workflow this configuration supports.

## Files

- `project.md` — the Plane project's description (pushed verbatim, minus this file's own preamble).
- `states.yaml` — the 7-state workflow (Backlog/Ready/In Progress/In Review/Blocked/Done/Cancelled).
- `labels.yaml` — the `category:value` label taxonomy.
- `modules.yaml` — one module per roadmap phase plus 4 cross-cutting modules.
- `cycles.yaml` — 1-week cycles through the hackathon push (Cycle 0–5).

The issue backlog itself (EPIC/FEATURE/STORY, transcribed from `docs/09-planning/backlog.md`) lives
in `scripts/plane/issues_data.py`, not here, because it needs Python logic (parent-linking) rather
than being purely declarative — but it is the same "edit here, then run bootstrap" model.

## Running the bootstrap

```bash
pip install pyyaml
export PLANE_API_KEY=...                    # never commit this
export PLANE_BASE_URL=http://localhost:80   # no trailing slash, no /api/v1 suffix
export PLANE_WORKSPACE_SLUG=astreus-develop
export PLANE_PROJECT_IDENTIFIER=JURI
python3 scripts/plane/bootstrap.py
```

The script is **idempotent**: it looks up every state/label/module/cycle/issue by name/title before
creating anything, and updates in place if found. Re-running it after editing one file only changes
what that file affects. If the Plane API rate-limits you mid-run (HTTP 429), the script retries with
backoff automatically; if it still fails, just re-run it — nothing gets duplicated.

To slow down the request rate further (e.g., on a heavily rate-limited instance), set
`PLANE_REQUEST_DELAY` (seconds between requests, default `0.6`).

## What this script does NOT do

- It does not create or modify issue **relations** (blocking/blocked-by) — this Plane instance's
  public API does not expose a relations endpoint. Dependencies between issues are documented as
  text within each issue's description and, authoritatively, in `docs/09-planning/dependencies.md`.
- It does not assign issues to people. Leave issues unassigned rather than inventing ownership; the
  team assigns work as capacity is known (see `docs/07-engineering/project-management.md`).
- It does not delete issues that are removed from `issues_data.py`. If a story is genuinely dropped,
  move it to the **Cancelled** state in Plane (or add a small cleanup step here if this becomes a
  recurring need) rather than silently deleting history.
