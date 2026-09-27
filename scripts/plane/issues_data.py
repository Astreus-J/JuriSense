"""
Issue backlog for the JuriSense Plane bootstrap.

Transcribed from docs/09-planning/backlog.md (EPIC/FEATURE/STORY, Phases 0-8 at story depth,
Phases 9-11 at epic/feature depth) plus docs/09-planning/roadmap.md (epic-level objective/exit
criteria) and a small set of cross-cutting Security/DevOps/Hackathon seed issues not already
covered by a specific backlog story.

If the plan changes, update docs/09-planning/backlog.md first (it is the source of truth), then
mirror the change here. This file is data, read by scripts/plane/bootstrap.py.

Each issue is a dict:
  key         - stable internal id used for parent-linking (not shown in Plane)
  parent      - key of the parent issue, or None
  title       - Plane issue title (starts with a verb for stories/tasks, per convention)
  module      - module key from modules.yaml
  labels      - list of label names from labels.yaml
  priority    - one of urgent/high/medium/low/none
  state       - one of the state names from states.yaml
  cycle       - cycle key from cycles.yaml, or None
  description - HTML string (built with `desc()` below)
"""


def desc(context, acceptance=None, dependencies=None, tasks=None, refs=None):
    html = f"<p>{context}</p>"
    if acceptance:
        html += "<p><strong>Acceptance criteria:</strong></p><ul>" + "".join(f"<li>{a}</li>" for a in acceptance) + "</ul>"
    if dependencies:
        html += f"<p><strong>Dependencies:</strong> {dependencies}</p>"
    if tasks:
        html += "<p><strong>Tasks:</strong></p><ul>" + "".join(f"<li>{t}</li>" for t in tasks) + "</ul>"
    html += f"<p><strong>Documentation:</strong> {refs or 'docs/09-planning/backlog.md'}</p>"
    return html


HACKATHON_LABELS = ["scope:hackathon"]

ISSUES = [
    # ============================================================ EPIC-0 — Foundation ============
    {
        "key": "EPIC-0", "parent": None,
        "title": "EPIC: Foundation (Phase 0)",
        "module": "foundation", "labels": ["type:refactor", "scope:foundation", *HACKATHON_LABELS, "risk:medium"],
        "priority": "urgent", "state": "Ready", "cycle": "cycle-1",
        "description": desc(
            "Stabilize the repository into the 8-bounded-context modular-monolith layout (ADR-002), "
            "migrate the existing, tested, security-audited Accounts code into Identity & "
            "Organizations, and establish the AuditEvent foundation every later context depends on.",
            acceptance=[
                "Every existing Accounts test passes unmodified in behavior (only names changed) against the renamed schema.",
                "A cross-tenant-access test passes for Organization isolation (ADR-003, SEC-001).",
                "The AuditEvent table exists and receives at least one real event type in practice.",
                "The sprint's ADR-016 security-audit gate passes with no open critical/high findings.",
            ],
            dependencies="None — first phase. Starting point is the existing, audited Accounts code (docs/auditorias/).",
            refs="docs/09-planning/roadmap.md (Phase 0), docs/09-planning/pivot-migration.md",
        ),
    },
    {
        "key": "FEATURE-0.1", "parent": "EPIC-0",
        "title": "FEATURE: Repository restructure into 8 bounded contexts",
        "module": "foundation", "labels": ["type:refactor", "scope:foundation", *HACKATHON_LABELS],
        "priority": "high", "state": "Ready", "cycle": "cycle-1",
        "description": desc("Move the codebase into the 8-bounded-context package layout before any renaming or new domain code lands."),
    },
    {
        "key": "STORY-0.1.1", "parent": "FEATURE-0.1",
        "title": "Restructure app/ into 8 bounded-context packages",
        "module": "foundation", "labels": ["type:refactor", "area:backend", "scope:foundation", *HACKATHON_LABELS, "risk:low"],
        "priority": "high", "state": "Ready", "cycle": "cycle-1",
        "description": desc(
            "As a developer, I can find every bounded context's code under its own "
            "app/&lt;context&gt;/{domain,application,infrastructure,api} package, mirroring the "
            "existing layout, so new contexts have zero structural ambiguity.",
            acceptance=[
                "app/ contains identity/, suppliers/, contracts/, policy/, approvals/, evidence/, ai_services/, integrations/, each with the four standard subpackages (even if some are initially empty).",
                "app/api/router.py aggregates a router from each package that has one.",
                "uv run pytest and docker compose up -d both succeed with no behavior change from before the restructure.",
            ],
            dependencies="None.",
            tasks=[
                "Create package skeletons.",
                "Move app/accounts/ to app/identity/ as a pure file move (no renames yet).",
                "Update import paths and router.py.",
                "Run the full existing test suite to confirm zero behavior change.",
            ],
            refs="docs/07-engineering/repository-structure.md",
        ),
    },
    {
        "key": "FEATURE-0.2", "parent": "EPIC-0",
        "title": "FEATURE: Identity & Organizations migration",
        "module": "foundation", "labels": ["type:refactor", "area:backend", "scope:foundation", *HACKATHON_LABELS],
        "priority": "high", "state": "Ready", "cycle": "cycle-1",
        "description": desc("Rename the Portuguese, legal-domain-specific Accounts schema to the new English, compliance-domain vocabulary (ADR-003, ADR-013)."),
    },
    {
        "key": "STORY-0.2.1", "parent": "FEATURE-0.2",
        "title": "Rename Organizacao to Organization with English fields",
        "module": "foundation", "labels": ["type:refactor", "area:database", "scope:foundation", *HACKATHON_LABELS, "risk:medium"],
        "priority": "high", "state": "Ready", "cycle": "cycle-1",
        "description": desc(
            "As an Admin, I can create an Organization with a name, tax id, and initial plan, using "
            "English field names throughout [ORG-001].",
            acceptance=[
                "Organizacao/Organization table and model renamed per pivot-migration.md (nome->name, cnpj->tax_id, etc.).",
                "BR-ORG-002 (tax_id unique within jurisdiction) enforced by a DB constraint.",
                "All existing organization-creation tests pass under the new names.",
            ],
            dependencies="FEATURE-0.1.",
            tasks=["Rename Organizacao->Organization model/table/fields.", "Regenerate Alembic migration.", "Update all call sites in application/*.py.", "Update/rename tests."],
            refs="docs/09-planning/pivot-migration.md, ADR-013",
        ),
    },
    {
        "key": "STORY-0.2.2", "parent": "FEATURE-0.2",
        "title": "Replace Perfil enum with the ADR-003 Role value set",
        "module": "foundation", "labels": ["type:refactor", "area:backend", "scope:foundation", *HACKATHON_LABELS, "risk:medium"],
        "priority": "high", "state": "Ready", "cycle": "cycle-1",
        "description": desc(
            "As an Admin, I can invite a User into my Organization with one of the 10 compliance "
            "Roles (Admin/Procurement/Legal/Compliance/Privacy/Security/Finance/Approver/Auditor/"
            "Viewer), reusing the existing invite mechanism [ORG-002].",
            acceptance=[
                "Perfil enum replaced by Role with the exact ADR-003 value set.",
                "The existing Convite/invite token-hash flow works unchanged except for the role value type.",
                "An invite cannot be created with a role outside the new set (schema/enum-level rejection, not just application-layer).",
            ],
            dependencies="STORY-0.2.1.",
            tasks=["Replace Perfil enum values.", "Update invite_service.py and its schemas.", "Update api/deps.py's get_current_admin role check.", "Update invite tests."],
            refs="ADR-003",
        ),
    },
    {
        "key": "STORY-0.2.3", "parent": "FEATURE-0.2",
        "title": "Replace Plano plan-limit model with the new plan dimensions",
        "module": "foundation", "labels": ["type:refactor", "area:backend", "scope:foundation", *HACKATHON_LABELS, "risk:low"],
        "priority": "medium", "state": "Ready", "cycle": "cycle-1",
        "description": desc(
            "As the system, I enforce per-organization plan limits (suppliers, contracts, AI "
            "executions) at creation time, not retroactively, reusing the existing 402-style "
            "enforcement pattern [ORG-003].",
            acceptance=[
                "Plano/LIMITES_POR_PLANO replaced with new plan tiers and limit dimensions per docs/02-business/pricing-strategy.md (BR-ORG-003).",
                "Exceeding a limit blocks new creation but never deletes or disables existing data.",
                "The existing LimiteUsuariosAtingidoError-style error pattern is reused for the new limit dimensions.",
            ],
            dependencies="STORY-0.2.1.",
            tasks=["Rename Plano enum and LimitesPlano dataclass.", "Define new limit dimensions.", "Wire enforcement checks at each future creation use case's call site, added incrementally as contexts land."],
        ),
    },
    {
        "key": "STORY-0.2.4", "parent": "FEATURE-0.2",
        "title": "Rename PermissaoModulo/Modulo to the new RBAC vocabulary",
        "module": "foundation", "labels": ["type:refactor", "area:backend", "scope:foundation", *HACKATHON_LABELS, "risk:low"],
        "priority": "medium", "state": "Ready", "cycle": "cycle-1",
        "description": desc(
            "As an Admin, I can grant a specific User permissions beyond their Role's default grid, "
            "reusing the existing per-user permission-override mechanism [ORG-004].",
            acceptance=[
                "PermissaoModulo renamed to an English-named per-user x module x action grid (can_create/can_read/can_update/can_delete).",
                "Modulo enum replaced with the new module vocabulary (suppliers/contracts/policies/compliance_reviews/approvals/evidence/integrations/organization_settings).",
                "Existing override tests pass under new names.",
            ],
            dependencies="STORY-0.2.2.",
            tasks=["Rename PermissaoModulo and Modulo.", "Update seed-data generation for the new module set.", "Update override tests."],
        ),
    },
    {
        "key": "STORY-0.2.5", "parent": "FEATURE-0.2",
        "title": "Confirm multi-organization membership scoping",
        "module": "foundation", "labels": ["type:test", "area:backend", "scope:foundation", *HACKATHON_LABELS, "risk:low"],
        "priority": "low", "state": "Ready", "cycle": "cycle-1",
        "description": desc(
            "As a User, I can hold Membership in more than one Organization, with every permission "
            "check scoped to exactly one active membership at a time [ORG-005].",
            acceptance=[
                "BR-ORG-001 holds -- no code path assumes a User belongs to exactly one organization.",
                "The multi-tenant lookup pattern already used by UsuarioRepository is confirmed to scope correctly when a user has multiple memberships.",
            ],
            dependencies="STORY-0.2.1.",
            tasks=["Audit existing single-organization assumptions in user_service.py.", "Add a regression test with a user holding two organization memberships."],
        ),
    },
    {
        "key": "STORY-0.2.6", "parent": "FEATURE-0.2",
        "title": "Remove OAB fields and validation from the User model",
        "module": "foundation", "labels": ["type:refactor", "area:backend", "scope:foundation", *HACKATHON_LABELS, "risk:medium"],
        "priority": "high", "state": "Ready", "cycle": "cycle-1",
        "description": desc(
            "As the system, I no longer collect or validate OAB (Brazilian bar registration) data "
            "anywhere in the user model, since it has no meaning for a compliance-platform user.",
            acceptance=[
                "oab/uf_oab fields, OabInvalidaError, OabJaCadastradaError, validar_formato_oab(), and UsuarioRepository.get_by_oab() are all removed.",
                "No remaining reference to OAB anywhere in app/identity/.",
                "Associated OAB test cases deleted.",
            ],
            dependencies="STORY-0.2.1.",
            tasks=["Remove fields/migration column.", "Remove error classes and their raises.", "Remove and delete dependent tests.", "Confirm no remaining import references via a repo-wide grep."],
        ),
    },
    {
        "key": "FEATURE-0.3", "parent": "EPIC-0",
        "title": "FEATURE: Audit foundation",
        "module": "foundation", "labels": ["type:feature", "area:backend", "scope:foundation", *HACKATHON_LABELS],
        "priority": "high", "state": "Ready", "cycle": "cycle-1",
        "description": desc("Establish the append-only AuditEvent log every later bounded context depends on."),
    },
    {
        "key": "STORY-0.3.1", "parent": "FEATURE-0.3",
        "title": "Emit AuditEvent for every Identity state-changing action",
        "module": "foundation", "labels": ["type:feature", "area:backend", "scope:foundation", *HACKATHON_LABELS, "risk:low"],
        "priority": "high", "state": "Ready", "cycle": "cycle-1",
        "description": desc(
            "As the system, I emit an append-only AuditEvent for every state-changing Identity "
            "action (organization.created, user.registered, membership.invited, "
            "membership.accepted, membership.revoked) [AUD-001].",
            acceptance=[
                "AuditEvent entity created (id, event_type, actor_id, payload, occurred_at).",
                "An emit_audit_event() helper is called from at least the five listed Identity use cases.",
                "Each emitted event is queryable and contains enough payload to reconstruct what happened.",
            ],
            dependencies="FEATURE-0.2.",
            tasks=["Create AuditEvent model + repository in app/evidence/.", "Implement emit_audit_event().", "Wire into the five Identity use cases.", "Add a test asserting each action produces exactly one event."],
            refs="docs/03-domain/audit.md",
        ),
    },
    {
        "key": "STORY-0.3.2", "parent": "FEATURE-0.3",
        "title": "Enforce that AuditEvent has no update/delete path",
        "module": "foundation", "labels": ["type:security", "area:database", "scope:foundation", *HACKATHON_LABELS, "risk:low"],
        "priority": "high", "state": "Ready", "cycle": "cycle-1",
        "description": desc(
            "As an Auditor, I cannot update or delete any AuditEvent, including as an Admin [AUD-002].",
            acceptance=[
                "BR-EVD-003 holds -- no repository method, API route, or admin tool exposes an update/delete path for AuditEvent.",
                "A test attempting a direct update/delete at the repository layer fails/raises as expected.",
            ],
            dependencies="STORY-0.3.1.",
            tasks=["Confirm the repository class exposes only add/list/get.", "Add the negative test."],
        ),
    },
    {
        "key": "FEATURE-0.4", "parent": "EPIC-0",
        "title": "FEATURE: CI and migration baseline",
        "module": "foundation", "labels": ["type:infrastructure", "area:devops", "scope:foundation", *HACKATHON_LABELS],
        "priority": "high", "state": "Ready", "cycle": "cycle-1",
        "description": desc("Ensure the Phase 0 rename cannot silently regress."),
    },
    {
        "key": "STORY-0.4.1", "parent": "FEATURE-0.4",
        "title": "Add CI gate for lint and tests on the renamed codebase",
        "module": "foundation", "labels": ["type:infrastructure", "area:devops", "scope:foundation", *HACKATHON_LABELS, "risk:medium"],
        "priority": "high", "state": "Ready", "cycle": "cycle-1",
        "description": desc(
            "As a developer, I get a red build if ruff or pytest fails on the renamed codebase, so "
            "the Phase 0 rename can't silently regress.",
            acceptance=[
                "CI runs uv run ruff check . and uv run pytest on every push; both pass against the fully renamed schema.",
                "A fresh Alembic migration exists and applies cleanly against a scratch copy of the external Neon Postgres schema.",
            ],
            dependencies="FEATURE-0.2, FEATURE-0.3.",
            tasks=["Regenerate Alembic migration.", "Add/confirm CI workflow.", "Document the migration rollback path in case the Neon schema needs reverting."],
            refs="docs/07-engineering/ci-cd.md",
        ),
    },

    # ============================================================ EPIC-1 — Core Platform ==========
    {
        "key": "EPIC-1", "parent": None,
        "title": "EPIC: Core Platform (Phase 1)",
        "module": "core-platform", "labels": ["type:feature", "scope:foundation", *HACKATHON_LABELS, "risk:medium"],
        "priority": "urgent", "state": "Ready", "cycle": "cycle-1",
        "description": desc(
            "Build the minimum cross-cutting platform every business context needs: enforced RBAC, "
            "a working frontend app shell, and object-storage adapter groundwork -- before any "
            "business-domain feature work starts.",
            acceptance=[
                "An Admin can invite a user into an org with one of the 10 compliance roles, and that user sees a role-appropriate empty dashboard on login.",
                "A deny-by-default RBAC test (a Viewer cannot write, a Procurement user of Org A cannot read Org B's data) passes.",
                "The backend dev container can read/write to the local MinIO bucket.",
            ],
            dependencies="Phase 0 (Organization, User, Role, AuditEvent must exist first).",
            refs="docs/09-planning/roadmap.md (Phase 1)",
        ),
    },
    {
        "key": "FEATURE-1.1", "parent": "EPIC-1",
        "title": "FEATURE: RBAC enforcement across all future modules",
        "module": "core-platform", "labels": ["type:security", "area:backend", "scope:foundation", *HACKATHON_LABELS],
        "priority": "high", "state": "Ready", "cycle": "cycle-1",
        "description": desc("A generic, reusable permission-check mechanism every future bounded context's API layer uses."),
    },
    {
        "key": "STORY-1.1.1", "parent": "FEATURE-1.1",
        "title": "Seed default RBAC grid for all 10 roles across 8 modules",
        "module": "core-platform", "labels": ["type:feature", "area:backend", "scope:foundation", *HACKATHON_LABELS, "risk:low"],
        "priority": "high", "state": "Ready", "cycle": "cycle-1",
        "description": desc(
            "As an Admin, when I create an organization, all 10 roles get a sensible default "
            "permission grid across the 8 new modules without manual setup.",
            acceptance=[
                "Seed data exists for all 10 roles x 8 modules.",
                "A newly created organization's users inherit their role's default grid immediately.",
                "ADR-012 (RBAC as data) is honored -- grids are DB rows, not hardcoded branches.",
            ],
            dependencies="EPIC-0 (Role/Modulo rename complete).",
            tasks=["Author the default grid seed dataset.", "Write a seed-loading migration/fixture.", "Add a test asserting every role has a non-empty default grid."],
        ),
    },
    {
        "key": "STORY-1.1.2", "parent": "FEATURE-1.1",
        "title": "Implement a reusable require_permission FastAPI dependency",
        "module": "core-platform", "labels": ["type:security", "area:backend", "area:api", "scope:foundation", *HACKATHON_LABELS, "risk:medium"],
        "priority": "high", "state": "Ready", "cycle": "cycle-1",
        "description": desc(
            "As a developer building any future route, I can gate it with a single reusable "
            "permission-check dependency instead of hand-rolling role checks per route.",
            acceptance=[
                "A generic require_permission(module, action) FastAPI dependency exists, modeled on the existing get_current_admin pattern.",
                "A deny-by-default cross-tenant test (a Viewer in Org A cannot write, and no role in Org A can read Org B's data) passes.",
            ],
            dependencies="STORY-1.1.1.",
            tasks=["Implement the generic dependency.", "Write the cross-tenant/cross-role denial test suite.", "Document the pattern for reuse by every later context's api/ layer."],
        ),
    },
    {
        "key": "FEATURE-1.2", "parent": "EPIC-1",
        "title": "FEATURE: Frontend app shell",
        "module": "frontend", "labels": ["type:feature", "area:frontend", "scope:foundation", *HACKATHON_LABELS],
        "priority": "high", "state": "Ready", "cycle": "cycle-1",
        "description": desc("The authenticated application shell every later screen mounts into."),
    },
    {
        "key": "STORY-1.2.1", "parent": "FEATURE-1.2",
        "title": "Build authenticated app shell with org switcher and role dashboards",
        "module": "frontend", "labels": ["type:feature", "area:frontend", "area:ux", "scope:foundation", *HACKATHON_LABELS, "risk:medium"],
        "priority": "high", "state": "Ready", "cycle": "cycle-1",
        "description": desc(
            "As a User, I can log in and see a role-appropriate empty dashboard, and switch between "
            "organizations if I hold multiple memberships.",
            acceptance=[
                "Login/invite-accept screens work end to end against the renamed Identity API.",
                "An organization switcher is visible and functional when a user has more than one Membership (BR-ORG-001).",
                "The dashboard renders without error for each of the 10 roles.",
            ],
            dependencies="EPIC-0, FEATURE-1.1.",
            tasks=["Port the existing Accounts login/invite UI flow into frontend/.", "Build the organization switcher.", "Build a minimal per-role empty-state dashboard shell."],
        ),
    },
    {
        "key": "FEATURE-1.3", "parent": "EPIC-1",
        "title": "FEATURE: Object storage adapter",
        "module": "core-platform", "labels": ["type:infrastructure", "area:backend", "scope:foundation", *HACKATHON_LABELS],
        "priority": "high", "state": "Ready", "cycle": "cycle-1",
        "description": desc("The single storage abstraction every future document/evidence write goes through (ADR-008)."),
    },
    {
        "key": "STORY-1.3.1", "parent": "FEATURE-1.3",
        "title": "Implement storage port with MinIO dev adapter",
        "module": "core-platform", "labels": ["type:infrastructure", "area:backend", "area:devops", "scope:foundation", *HACKATHON_LABELS, "risk:low", "tech:docker"],
        "priority": "high", "state": "Ready", "cycle": "cycle-1",
        "description": desc(
            "As a developer, I have a single storage abstraction (put/get/generate_presigned_url) "
            "that any future context can use to read/write files, backed by MinIO in dev and "
            "swappable to Cloudflare R2 in production [ADR-008].",
            acceptance=[
                "MinIO added to docker-compose.yml.",
                "A storage port interface is defined once and has exactly one dev implementation.",
                "A smoke test writes and reads back a file through the abstraction.",
            ],
            dependencies="FEATURE-0.1.",
            tasks=["Add MinIO service + volume to compose.", "Implement the storage port + MinIO adapter.", "Write the smoke test."],
        ),
    },
    {
        "key": "FEATURE-1.4", "parent": "EPIC-1",
        "title": "FEATURE: Integration scaffold",
        "module": "integrations", "labels": ["type:feature", "area:backend", "scope:foundation", *HACKATHON_LABELS],
        "priority": "low", "state": "Ready", "cycle": "cycle-1",
        "description": desc("Establish the Integrations context as a real seam from day one, even before a real connector exists."),
    },
    {
        "key": "STORY-1.4.1", "parent": "FEATURE-1.4",
        "title": "Create Integration entity as a configuration-only scaffold",
        "module": "integrations", "labels": ["type:feature", "area:backend", "scope:foundation", *HACKATHON_LABELS, "risk:low"],
        "priority": "low", "state": "Ready", "cycle": "cycle-1",
        "description": desc(
            "As an Admin, I can see an Integration entity exists as a configuration record (no real "
            "connector yet), establishing the seam future connectors will use [INT-001].",
            acceptance=[
                "Integration entity created (organization_id, provider, config, status).",
                "No code path allows an Integration to write directly to a business-domain table (verified by a boundary-rule test/lint check).",
            ],
            dependencies="FEATURE-0.1.",
            tasks=["Create the Integration model + minimal CRUD.", "Add a boundary-rule check preventing direct cross-context ORM writes."],
            refs="docs/04-architecture/components.md",
        ),
    },

    # ============================================================ EPIC-2 — Supplier Intelligence ==
    {
        "key": "EPIC-2", "parent": None,
        "title": "EPIC: Supplier Intelligence (Phase 2)",
        "module": "supplier-intelligence", "labels": ["type:feature", *HACKATHON_LABELS, "risk:medium"],
        "priority": "urgent", "state": "Backlog", "cycle": "cycle-3",
        "description": desc(
            "Implement the Suppliers bounded context end to end: registration, external "
            "verification, and normalized profile state.",
            acceptance=[
                "A Procurement-role user registers a Supplier with a CNPJ, a SupplierCheck runs automatically on creation, and the resulting SupplierProfile reflects registry status and any sanctions hit.",
                "SupplierCheck history is immutable and fully queryable.",
                "supplier.created, supplier.updated, supplier.status_changed audit events are emitted.",
            ],
            dependencies="Phase 0 (Organization), Phase 1 (RBAC on the suppliers module). Does NOT depend on Phase 3 -- can run in parallel.",
            refs="docs/09-planning/roadmap.md (Phase 2)",
        ),
    },
    {
        "key": "FEATURE-2.1", "parent": "EPIC-2",
        "title": "FEATURE: Supplier registration and CRUD",
        "module": "supplier-intelligence", "labels": ["type:feature", "area:backend", *HACKATHON_LABELS],
        "priority": "high", "state": "Backlog", "cycle": "cycle-3",
        "description": desc("Core Supplier entity, registration, and browsing."),
    },
    {
        "key": "STORY-2.1.1", "parent": "FEATURE-2.1",
        "title": "Register a Supplier with a jurisdiction-specific identifier",
        "module": "supplier-intelligence", "labels": ["type:feature", "area:backend", "area:database", *HACKATHON_LABELS, "risk:low", "mvp:required"],
        "priority": "high", "state": "Backlog", "cycle": "cycle-3",
        "description": desc(
            "As a Procurement user, I can register a Supplier with a jurisdiction-specific "
            "identifier (CNPJ for Brazil) [SUP-001].",
            acceptance=[
                "Supplier entity created with legal_name, tax_id, jurisdiction, status (prospect/under_review/approved/blocked/inactive).",
                "BR-SUP-001 holds (belongs to exactly one Organization).",
                "BR-SUP-002 holds -- tax_id + organization_id unique, enforced by a DB constraint, and registering the same tax_id twice in one org returns a clear conflict error.",
            ],
            dependencies="EPIC-0 (Organization), EPIC-1 (RBAC on the suppliers module).",
            tasks=["Create Supplier model/migration.", "Implement the register-supplier use case.", "Add the uniqueness constraint and its conflict-handling test."],
        ),
    },
    {
        "key": "STORY-2.1.2", "parent": "FEATURE-2.1",
        "title": "Build supplier list and detail screens",
        "module": "supplier-intelligence", "labels": ["type:feature", "area:frontend", "area:api", *HACKATHON_LABELS, "risk:low"],
        "priority": "medium", "state": "Backlog", "cycle": "cycle-3",
        "description": desc(
            "As a Procurement user, I can view a list and detail page of my organization's "
            "suppliers, filtered by status.",
            acceptance=[
                "List/detail API and frontend screens exist, scoped to the caller's organization only (cross-tenant read denial test passes).",
                "Status filter works for all five lifecycle states.",
            ],
            dependencies="STORY-2.1.1.",
            tasks=["Build list/detail endpoints.", "Build frontend supplier list/detail screens."],
        ),
    },
    {
        "key": "FEATURE-2.2", "parent": "EPIC-2",
        "title": "FEATURE: Supplier verification adapters",
        "module": "supplier-intelligence", "labels": ["type:feature", "area:backend", *HACKATHON_LABELS],
        "priority": "high", "state": "Backlog", "cycle": "cycle-3",
        "description": desc("External verification against Brazilian registry and sanctions sources, isolated behind an Integrations adapter."),
    },
    {
        "key": "STORY-2.2.1", "parent": "FEATURE-2.2",
        "title": "Trigger SupplierCheck on creation and manual re-check",
        "module": "supplier-intelligence", "labels": ["type:feature", "area:backend", *HACKATHON_LABELS, "risk:medium"],
        "priority": "high", "state": "Backlog", "cycle": "cycle-3",
        "description": desc(
            "As the system, I trigger a SupplierCheck against configured external sources "
            "automatically on supplier creation and on manual re-check request [SUP-002].",
            acceptance=[
                "SupplierCheck entity created (sources_consulted, raw_results, started_at, completed_at, status).",
                "A check is queued (via Celery, per ADR-006) on both supplier creation and an explicit re-check API call.",
                "A SupplierCheck is immutable once completed.",
            ],
            dependencies="STORY-2.1.1.",
            tasks=["Create SupplierCheck model.", "Define the SupplierVerificationPort interface.", "Wire a Celery task to invoke it on both trigger paths."],
        ),
    },
    {
        "key": "STORY-2.2.2", "parent": "FEATURE-2.2",
        "title": "Integrate CNPJ registry and CEIS/CNEP/CEPIM sanctions adapters",
        "module": "supplier-intelligence", "labels": ["type:feature", "area:backend", *HACKATHON_LABELS, "risk:high", "mvp:required"],
        "priority": "urgent", "state": "Backlog", "cycle": "cycle-3",
        "description": desc(
            "As the system, I call the CNPJ registry and CEIS/CNEP/CEPIM sanctions sources through "
            "an adapter behind the Integrations context, so no other context depends on a specific "
            "external API shape.",
            acceptance=[
                "Concrete adapters live in app/integrations/infrastructure/, implementing SupplierVerificationPort.",
                "Suppliers code only imports the port, never the concrete HTTP client (verified by a boundary-rule check).",
                "Adapter failure/timeout does not crash the check -- it records a failed SupplierCheck status instead.",
            ],
            dependencies="STORY-2.2.1.",
            tasks=["Implement CNPJ-registry adapter.", "Implement CEIS/CNEP/CEPIM adapter(s).", "Add timeout/retry/failure handling.", "Add a boundary-rule test."],
            refs="docs/03-domain/supplier-compliance.md",
        ),
    },
    {
        "key": "FEATURE-2.3", "parent": "EPIC-2",
        "title": "FEATURE: Supplier profile normalization and history",
        "module": "supplier-intelligence", "labels": ["type:feature", "area:backend", *HACKATHON_LABELS],
        "priority": "high", "state": "Backlog", "cycle": "cycle-3",
        "description": desc("Keep a single normalized current-state profile plus an immutable check history."),
    },
    {
        "key": "STORY-2.3.1", "parent": "FEATURE-2.3",
        "title": "Replace SupplierProfile on every successful re-check",
        "module": "supplier-intelligence", "labels": ["type:feature", "area:backend", *HACKATHON_LABELS, "risk:low"],
        "priority": "medium", "state": "Backlog", "cycle": "cycle-3",
        "description": desc(
            "As a Compliance user, I see a SupplierProfile that always reflects the most recent "
            "successful SupplierCheck [SUP-003].",
            acceptance=["SupplierProfile is replaced (not mutated) on every successful re-check.", "Only one active profile exists per supplier at any time."],
            dependencies="STORY-2.2.1.",
            tasks=["Implement profile-replacement logic on check completion.", "Add a test covering two successive successful checks."],
        ),
    },
    {
        "key": "STORY-2.3.2", "parent": "FEATURE-2.3",
        "title": "Surface a sanctions hit as a non-silent blocking signal",
        "module": "supplier-intelligence", "labels": ["type:feature", "area:backend", "type:security", *HACKATHON_LABELS, "risk:medium", "mvp:required"],
        "priority": "high", "state": "Backlog", "cycle": "cycle-3",
        "description": desc(
            "As a Compliance user, a sanctions-list hit on any SupplierCheck is surfaced as a "
            "non-silent blocking signal on the Supplier, never quietly absorbed [SUP-004, BR-SUP-004].",
            acceptance=[
                "A positive sanctions hit sets a visible flag the future SANC-001 policy rule can consume.",
                "The flag cannot be cleared without an explicit, audited exception record (the exception mechanism itself is built in EPIC-4).",
            ],
            dependencies="STORY-2.2.2.",
            tasks=["Add the sanctions-hit signal field/derivation.", "Add a test asserting the flag persists across profile replacement until explicitly cleared."],
        ),
    },
    {
        "key": "STORY-2.3.3", "parent": "FEATURE-2.3",
        "title": "Expose immutable SupplierCheck history",
        "module": "supplier-intelligence", "labels": ["type:feature", "area:backend", *HACKATHON_LABELS, "risk:low"],
        "priority": "medium", "state": "Backlog", "cycle": "cycle-3",
        "description": desc(
            "As an Auditor, I can see the full, immutable SupplierCheck history for any supplier, "
            "timestamped and in order [SUP-005].",
            acceptance=[
                "BR-SUP-003 holds -- a Supplier cannot reach approved status without at least one completed check newer than any open sanctions flag.",
                "Check history is queryable and never edited after completion.",
            ],
            dependencies="STORY-2.2.1.",
            tasks=["Build the check-history query endpoint/view.", "Add the BR-SUP-003 status-transition guard."],
        ),
    },

    # ============================================================ EPIC-3 — Contract Intelligence ==
    {
        "key": "EPIC-3", "parent": None,
        "title": "EPIC: Contract Intelligence (Phase 3)",
        "module": "contract-intelligence", "labels": ["type:feature", *HACKATHON_LABELS, "risk:high"],
        "priority": "urgent", "state": "Backlog", "cycle": "cycle-3",
        "description": desc(
            "Implement the Contracts & Documents bounded context and the embedded AI Services "
            "extraction pipeline: ingestion, versioning, structured extraction, clause-level "
            "provenance.",
            acceptance=[
                "A Legal-role user uploads a contract PDF and gets back a new ContractVersion with structured extracted fields and page/span-cited Clause records.",
                "Low-confidence fields are visibly flagged rather than silently accepted.",
                "Re-uploading a revision creates a new ContractVersion without touching the previous one (BR-CON-002).",
            ],
            dependencies="Phase 0 (Organization), Phase 1 (storage abstraction). Does NOT depend on Phase 2 -- can run in parallel.",
            refs="docs/09-planning/roadmap.md (Phase 3)",
        ),
    },
    {
        "key": "FEATURE-3.1", "parent": "EPIC-3",
        "title": "FEATURE: Document ingestion and storage",
        "module": "contract-intelligence", "labels": ["type:feature", "area:backend", *HACKATHON_LABELS],
        "priority": "high", "state": "Backlog", "cycle": "cycle-3",
        "description": desc("Upload, hash, and validate contract documents before any AI processing."),
    },
    {
        "key": "STORY-3.1.1", "parent": "FEATURE-3.1",
        "title": "Upload a contract document (PDF/DOCX/TXT)",
        "module": "contract-intelligence", "labels": ["type:feature", "area:backend", *HACKATHON_LABELS, "risk:low", "mvp:required"],
        "priority": "high", "state": "Backlog", "cycle": "cycle-3",
        "description": desc(
            "As a Legal user, I can upload a contract document (PDF/DOCX/TXT) [CON-001].",
            acceptance=[
                "Document entity created (storage_key, content_hash, mime_type, uploaded_by).",
                "Upload goes through the FEATURE-1.3 storage abstraction.",
                "content_hash (SHA-256) is computed at upload time and never recomputed or mutated afterward.",
            ],
            dependencies="EPIC-0, FEATURE-1.3.",
            tasks=["Create Document model.", "Implement upload endpoint.", "Compute and persist content_hash."],
        ),
    },
    {
        "key": "STORY-3.1.2", "parent": "FEATURE-3.1",
        "title": "Validate and scan uploads for malware/type-spoofing",
        "module": "contract-intelligence", "labels": ["type:security", "area:security", "area:backend", *HACKATHON_LABELS, "risk:medium"],
        "priority": "high", "state": "Backlog", "cycle": "cycle-3",
        "description": desc(
            "As the system, I validate and scan every uploaded document for malware/type-spoofing "
            "before processing [SEC-003].",
            acceptance=[
                "An upload with a mismatched extension/content-type or a known-bad payload signature is rejected before it reaches storage.",
                "This check runs synchronously on upload, not deferred to a later async step.",
            ],
            dependencies="STORY-3.1.1.",
            tasks=["Integrate a file-type/signature validation library.", "Add rejection tests for spoofed extension and known-bad-signature cases."],
            refs="docs/07-engineering/security.md",
        ),
    },
    {
        "key": "FEATURE-3.2", "parent": "EPIC-3",
        "title": "FEATURE: Contract and ContractVersion versioning",
        "module": "contract-intelligence", "labels": ["type:feature", "area:backend", *HACKATHON_LABELS],
        "priority": "high", "state": "Backlog", "cycle": "cycle-3",
        "description": desc("Every negotiation round creates a new immutable ContractVersion."),
    },
    {
        "key": "STORY-3.2.1", "parent": "FEATURE-3.2",
        "title": "Create a new ContractVersion on every uploaded revision",
        "module": "contract-intelligence", "labels": ["type:feature", "area:backend", "area:database", *HACKATHON_LABELS, "risk:low"],
        "priority": "high", "state": "Backlog", "cycle": "cycle-3",
        "description": desc(
            "As a Legal user, every new negotiation round I upload creates a new ContractVersion, "
            "never overwriting a previous one [CON-002, BR-CON-002].",
            acceptance=[
                "Contract and ContractVersion entities created; a Contract belongs to exactly one Supplier (BR-CON-001).",
                "Uploading a revision against an existing Contract produces a new ContractVersion row and leaves the prior version's data untouched, verified by a test that re-uploads and asserts the old version is still readable unchanged.",
            ],
            dependencies="STORY-3.1.1, EPIC-2 (Supplier must exist for Contract.supplier_id).",
            tasks=["Create Contract/ContractVersion models.", "Implement version-creation-on-upload logic.", "Add the non-mutation regression test."],
        ),
    },
    {
        "key": "FEATURE-3.3", "parent": "EPIC-3",
        "title": "FEATURE: AI structured extraction",
        "module": "contract-intelligence", "labels": ["type:feature", "area:ai", *HACKATHON_LABELS],
        "priority": "high", "state": "Backlog", "cycle": "cycle-3",
        "description": desc("The AI Gateway abstraction and structured-output extraction pipeline (ADR-005)."),
    },
    {
        "key": "STORY-3.3.1", "parent": "FEATURE-3.3",
        "title": "Build the AI Gateway and run structured extraction on every ContractVersion",
        "module": "contract-intelligence", "labels": ["type:feature", "area:ai", *HACKATHON_LABELS, "risk:high", "tech:llm", "mvp:required"],
        "priority": "urgent", "state": "Backlog", "cycle": "cycle-3",
        "description": desc(
            "As the system, I run AI structured extraction on every new ContractVersion, producing "
            "the schema in docs/05-ai/structured-extraction.md [CON-003].",
            acceptance=[
                "The AI Gateway abstraction (ADR-005) is called with structured-output (JSON schema/tool-calling) only -- no freeform text parsing anywhere in the pipeline (AI-001).",
                "Extraction runs asynchronously via Celery on ContractVersion creation.",
            ],
            dependencies="STORY-3.2.1.",
            tasks=["Build the AI Gateway interface (extract/classify/summarize).", "Implement the OpenAI adapter.", "Implement the Anthropic adapter.", "Wire automatic fallback on error/timeout (AI-003).", "Wire extraction trigger on ContractVersion creation."],
            refs="docs/05-ai/structured-extraction.md, ADR-005",
        ),
    },
    {
        "key": "STORY-3.3.2", "parent": "FEATURE-3.3",
        "title": "Attach confidence and citation to every extracted field",
        "module": "contract-intelligence", "labels": ["type:feature", "area:ai", *HACKATHON_LABELS, "risk:medium", "tech:llm"],
        "priority": "high", "state": "Backlog", "cycle": "cycle-3",
        "description": desc(
            "As a Legal user, every extracted field carries a confidence score and a source "
            "citation back to the document [AI-002].",
            acceptance=[
                "Every field in extracted_data has an associated confidence value and a document/page/span reference.",
                "The confidence-and-citation shape matches docs/05-ai/document-intelligence.md.",
            ],
            dependencies="STORY-3.3.1.",
            tasks=["Extend the extraction schema with confidence/citation fields.", "Validate provider output against the schema before persisting."],
        ),
    },
    {
        "key": "STORY-3.3.3", "parent": "FEATURE-3.3",
        "title": "Enforce AI Services never sets a Decision status",
        "module": "contract-intelligence", "labels": ["type:security", "area:ai", *HACKATHON_LABELS, "risk:low"],
        "priority": "high", "state": "Backlog", "cycle": "cycle-3",
        "description": desc(
            "As the system, AI Services output never directly sets a Decision status -- only "
            "Policy & Compliance may do so [AI-004].",
            acceptance=["A boundary-rule test/lint confirms no code path in app/ai_services/ writes to any Decision-related table or calls any Policy/Compliance application function directly."],
            dependencies="STORY-3.3.1.",
            tasks=["Add the boundary-rule check to CI.", "Document the rule in 07-engineering/coding-standards.md."],
            refs="docs/04-architecture/components.md",
        ),
    },
    {
        "key": "FEATURE-3.4", "parent": "EPIC-3",
        "title": "FEATURE: Clause provenance and confidence gate",
        "module": "contract-intelligence", "labels": ["type:feature", "area:ai", *HACKATHON_LABELS],
        "priority": "high", "state": "Backlog", "cycle": "cycle-3",
        "description": desc("No clause without provenance, no low-confidence version without human confirmation."),
    },
    {
        "key": "STORY-3.4.1", "parent": "FEATURE-3.4",
        "title": "Require page/span citation on every extracted Clause",
        "module": "contract-intelligence", "labels": ["type:feature", "area:ai", "area:database", *HACKATHON_LABELS, "risk:medium"],
        "priority": "high", "state": "Backlog", "cycle": "cycle-3",
        "description": desc(
            "As a Legal user, every AI-identified Clause carries a page/span citation back to its "
            "source document, and a clause without provenance cannot be used as evidence [CON-004, BR-CON-004].",
            acceptance=[
                "Clause entity created (contract_version_id, clause_type, page, text_span, confidence).",
                "The domain layer rejects creating a Clause with a null/missing page/span at construction time, not just at review time.",
            ],
            dependencies="STORY-3.3.1.",
            tasks=["Create Clause model with a non-null provenance constraint.", "Add a construction-time validation test."],
        ),
    },
    {
        "key": "STORY-3.4.2", "parent": "FEATURE-3.4",
        "title": "Gate low-confidence ContractVersions on human confirmation",
        "module": "contract-intelligence", "labels": ["type:feature", "area:ai", "area:frontend", *HACKATHON_LABELS, "risk:high"],
        "priority": "high", "state": "Backlog", "cycle": "cycle-3",
        "description": desc(
            "As a Legal user, a ContractVersion below the minimum extraction confidence is flagged "
            "for mandatory human confirmation before compliance review can proceed [CON-005, BR-CON-003].",
            acceptance=[
                "A configurable confidence threshold exists.",
                "A ContractVersion below it is marked needs_confirmation and blocked from analyzed status until a human confirms.",
                "The frontend surfaces this state clearly on the contract detail screen.",
            ],
            dependencies="STORY-3.3.2.",
            tasks=["Implement the threshold check and needs_confirmation state.", "Build the human-confirmation UI and endpoint.", "Add a test that a low-confidence version cannot reach analyzed without it."],
        ),
    },

    # ============================================================ EPIC-4 — Policy Engine ===========
    {
        "key": "EPIC-4", "parent": None,
        "title": "EPIC: Policy Engine (Phase 4)",
        "module": "policy-engine", "labels": ["type:feature", *HACKATHON_LABELS, "risk:high"],
        "priority": "urgent", "state": "Backlog", "cycle": "cycle-4",
        "description": desc(
            "Implement the authoring/versioning half of Policy & Compliance: the YAML rule DSL, "
            "the ADR-004 CEL-compilation spike, and simulation.",
            acceptance=[
                "An organization can author the SANC-001/LGPD-001/FIN-003/FIN-004/LEGAL-008 example rules in YAML, publish them as an immutable PolicyVersion, and run a dry-run simulation against existing ContractVersions with no side effects.",
                "ADR-004's status is updated based on the spike's findings.",
            ],
            dependencies="Phase 2 AND Phase 3 (needs both supplier and contract evidence shapes). Phase 1 (RBAC, since approver_role references a Role).",
            refs="docs/09-planning/roadmap.md (Phase 4), docs/03-domain/policy-engine.md",
        ),
    },
    {
        "key": "FEATURE-4.1", "parent": "EPIC-4",
        "title": "FEATURE: ADR-004 expression-language spike",
        "module": "policy-engine", "labels": ["type:spike", "area:backend", *HACKATHON_LABELS],
        "priority": "urgent", "state": "Backlog", "cycle": "cycle-4",
        "description": desc("Resolve whether CEL cleanly compiles the DSL before writing production Policy Engine code."),
    },
    {
        "key": "STORY-4.1.1", "parent": "FEATURE-4.1",
        "title": "Spike: benchmark cel-python against the 5 example rules",
        "module": "policy-engine", "labels": ["type:spike", "area:backend", *HACKATHON_LABELS, "risk:high"],
        "priority": "urgent", "state": "Backlog", "cycle": "cycle-4",
        "description": desc(
            "As the engineering team, I know whether cel-python cleanly compiles the five worked "
            "example rules in docs/03-domain/policy-engine.md before writing production Policy "
            "Engine code.",
            acceptance=[
                "A timeboxed spike produces a written result (benchmark numbers, packaging notes, and a working proof-of-concept compiling SANC-001, LGPD-001, LEGAL-008, FIN-003, FIN-004 to CEL).",
                "ADR-004's status is updated to Accepted, or the CEL/JSONLogic priority is formally reversed in the ADR.",
            ],
            dependencies="EPIC-2, EPIC-3 (spike needs real evidence shapes to test against).",
            tasks=["Install and benchmark cel-python.", "Write the proof-of-concept YAML->CEL compiler for the five example rules.", "Document findings and update ADR-004."],
        ),
    },
    {
        "key": "FEATURE-4.2", "parent": "EPIC-4",
        "title": "FEATURE: Policy/PolicyVersion/Rule authoring",
        "module": "policy-engine", "labels": ["type:feature", "area:backend", *HACKATHON_LABELS],
        "priority": "high", "state": "Backlog", "cycle": "cycle-4",
        "description": desc("Author and immutably publish versioned rule sets."),
    },
    {
        "key": "STORY-4.2.1", "parent": "FEATURE-4.2",
        "title": "Author a Policy and its Rules using the YAML DSL",
        "module": "policy-engine", "labels": ["type:feature", "area:backend", *HACKATHON_LABELS, "risk:medium", "mvp:required"],
        "priority": "high", "state": "Backlog", "cycle": "cycle-4",
        "description": desc(
            "As a Compliance user, I can author a Policy and its Rules using the YAML DSL [POL-001].",
            acceptance=[
                "Policy, PolicyVersion, Rule entities created.",
                "Rule authoring API accepts the YAML shape (id, name, when, result, severity, approver_role) documented in policy-engine.md.",
                "A syntactically invalid rule is rejected with a clear error before it can be saved to a draft.",
            ],
            dependencies="STORY-4.1.1.",
            tasks=["Create the three entities/migrations.", "Implement the YAML parser + validator.", "Implement the draft-save endpoint."],
        ),
    },
    {
        "key": "STORY-4.2.2", "parent": "FEATURE-4.2",
        "title": "Make published PolicyVersion rules immutable",
        "module": "policy-engine", "labels": ["type:feature", "area:backend", "area:database", *HACKATHON_LABELS, "risk:medium", "mvp:required"],
        "priority": "high", "state": "Backlog", "cycle": "cycle-4",
        "description": desc(
            "As a Compliance user, once I publish a PolicyVersion, its rules become immutable "
            "forever -- editing always creates a new version [POL-002, BR-POL-001, BR-POL-002].",
            acceptance=[
                "Publishing freezes every Rule in the version; an attempted edit of a published rule is rejected at the domain layer.",
                "Only one PolicyVersion per Policy is current at a time, enforced by a DB constraint or equivalent guard.",
            ],
            dependencies="STORY-4.2.1.",
            tasks=["Implement the publish action (copy-modify into a new version).", "Add the immutability guard and its test.", "Add the single-current-version constraint."],
        ),
    },
    {
        "key": "FEATURE-4.3", "parent": "EPIC-4",
        "title": "FEATURE: Evaluation context normalizer",
        "module": "policy-engine", "labels": ["type:feature", "area:backend", *HACKATHON_LABELS],
        "priority": "high", "state": "Backlog", "cycle": "cycle-4",
        "description": desc("The single, flat, typed evidence context every rule evaluates against."),
    },
    {
        "key": "STORY-4.3.1", "parent": "FEATURE-4.3",
        "title": "Build the normalized evaluation-context builder",
        "module": "policy-engine", "labels": ["type:feature", "area:backend", *HACKATHON_LABELS, "risk:high"],
        "priority": "urgent", "state": "Backlog", "cycle": "cycle-4",
        "description": desc(
            "As the Policy Engine, I build one flat, typed evaluation context from Supplier+"
            "SupplierProfile+SupplierCheck and ContractVersion.extracted_data+Clause, so rules "
            "never touch raw AI output or raw documents directly.",
            acceptance=[
                "The normalizer produces the exact field shapes documented in policy-engine.md (supplier.sanctions_hit, contract.liability.type, contract.value.brl, contract.processes_personal_data, contract.dpa_present, etc.).",
                "Normalization logic lives in Policy & Compliance's application layer, not AI Services (BR-CMP-001).",
            ],
            dependencies="EPIC-2, EPIC-3, STORY-4.1.1.",
            tasks=["Define the normalized context schema.", "Implement the Supplier-side mapping.", "Implement the Contract-side mapping.", "Add a test asserting the context is a pure function of its inputs."],
        ),
    },
    {
        "key": "FEATURE-4.4", "parent": "EPIC-4",
        "title": "FEATURE: Simulation / dry-run",
        "module": "policy-engine", "labels": ["type:feature", "area:backend", *HACKATHON_LABELS],
        "priority": "medium", "state": "Backlog", "cycle": "cycle-4",
        "description": desc("Let a compliance team see the effect of a policy change before publishing it."),
    },
    {
        "key": "STORY-4.4.1", "parent": "FEATURE-4.4",
        "title": "Run a draft PolicyVersion as a zero-side-effect simulation",
        "module": "policy-engine", "labels": ["type:feature", "area:backend", "area:frontend", *HACKATHON_LABELS, "risk:medium"],
        "priority": "medium", "state": "Backlog", "cycle": "cycle-4",
        "description": desc(
            "As a Compliance user, I can run a draft PolicyVersion against existing contracts "
            "before publishing, with zero side effects [POL-003].",
            acceptance=[
                "A simulation run does not create real ComplianceReview/Decision records and does not emit domain events.",
                "The simulation result shows, per contract, what would change versus the currently published version.",
            ],
            dependencies="STORY-4.2.2, STORY-4.3.1.",
            tasks=["Implement the simulation execution path (reusing the real evaluator in a non-persisting mode).", "Build the simulation-results frontend view."],
        ),
    },
    {
        "key": "STORY-4.4.2", "parent": "FEATURE-4.4",
        "title": "Add time-boxed policy exceptions with mandatory sign-off",
        "module": "policy-engine", "labels": ["type:feature", "area:backend", *HACKATHON_LABELS, "risk:low"],
        "priority": "low", "state": "Backlog", "cycle": "cycle-4",
        "description": desc(
            "As a Compliance user, I can grant a time-boxed policy exception for a specific "
            "supplier/contract with mandatory justification and approver sign-off [POL-004].",
            acceptance=["An exception record is first-class and audited (not a silent rule edit).", "It requires the same approver_role the waived rule would have required."],
            dependencies="STORY-4.2.2.",
            tasks=["Create the exception entity.", "Wire it into the evaluation path as a documented override input, not a rule mutation.", "Add an audit event for exception grants."],
        ),
    },

    # ============================================================ EPIC-5 — Compliance ==============
    {
        "key": "EPIC-5", "parent": None,
        "title": "EPIC: Compliance (Phase 5)",
        "module": "compliance-engine", "labels": ["type:feature", *HACKATHON_LABELS, "risk:high"],
        "priority": "urgent", "state": "Backlog", "cycle": "cycle-4",
        "description": desc(
            "Implement the evaluation/aggregation half of Policy & Compliance: running rules and "
            "turning their outcomes into one explainable, deterministic status per ADR-010.",
            acceptance=[
                "Running a ComplianceReview against a real Supplier + ContractVersion + PolicyVersion combination produces a deterministic, explainable status with linked evidence for every triggered rule.",
                "A test that permutes rule-evaluation order and asserts an identical final outcome passes.",
                "A review with zero applicable rules correctly defaults to APPROVE rather than erroring.",
            ],
            dependencies="Phase 4 (needs a published PolicyVersion and the evaluation-context normalizer).",
            refs="docs/09-planning/roadmap.md (Phase 5), ADR-010",
        ),
    },
    {
        "key": "FEATURE-5.1", "parent": "EPIC-5",
        "title": "FEATURE: ComplianceReview execution",
        "module": "compliance-engine", "labels": ["type:feature", "area:backend", *HACKATHON_LABELS],
        "priority": "high", "state": "Backlog", "cycle": "cycle-4",
        "description": desc("Run every applicable rule against the normalized context."),
    },
    {
        "key": "STORY-5.1.1", "parent": "FEATURE-5.1",
        "title": "Trigger a ComplianceReview against the current PolicyVersion",
        "module": "compliance-engine", "labels": ["type:feature", "area:backend", *HACKATHON_LABELS, "risk:medium"],
        "priority": "high", "state": "Backlog", "cycle": "cycle-4",
        "description": desc(
            "As a Compliance user, I can trigger a ComplianceReview that evaluates every applicable "
            "Rule in the current PolicyVersion against normalized evidence [CMP-001, BR-CMP-001].",
            acceptance=[
                "ComplianceReview entity created (contract_version_id, policy_version_id, status, started_at, completed_at).",
                "The review always evaluates against the FEATURE-4.3 normalized context, never raw AI output.",
                "The review is immutable once completed.",
            ],
            dependencies="EPIC-4.",
            tasks=["Create ComplianceReview model.", "Implement the review-execution use case.", "Add the immutable-once-completed guard."],
        ),
    },
    {
        "key": "FEATURE-5.2", "parent": "EPIC-5",
        "title": "FEATURE: Aggregation engine (ADR-010)",
        "module": "compliance-engine", "labels": ["type:feature", "area:backend", *HACKATHON_LABELS],
        "priority": "urgent", "state": "Backlog", "cycle": "cycle-4",
        "description": desc("The deterministic BLOCK>REVIEW>APPROVE aggregation, the product's core value proposition."),
    },
    {
        "key": "STORY-5.2.1", "parent": "FEATURE-5.2",
        "title": "Implement the BLOCK/REVIEW/APPROVE aggregation function",
        "module": "compliance-engine", "labels": ["type:feature", "area:backend", *HACKATHON_LABELS, "risk:high", "mvp:required"],
        "priority": "urgent", "state": "Backlog", "cycle": "cycle-4",
        "description": desc(
            "As a Compliance user, I get a deterministic final status from a set of independent "
            "rule outcomes: any BLOCK wins, else any REVIEW wins, else APPROVE [CMP-002, BR-CMP-002].",
            acceptance=[
                "RuleEvaluation entity created with outcome in {PASS, REVIEW, BLOCK, NOT_APPLICABLE}.",
                "The aggregation function is pure and order-independent -- a test that permutes rule-evaluation order asserts an identical final outcome.",
                "A review with zero applicable rules correctly defaults to APPROVE.",
            ],
            dependencies="STORY-5.1.1.",
            tasks=["Create RuleEvaluation/Risk models.", "Implement the aggregation function as a pure function over an outcome set.", "Write the order-permutation test.", "Write the zero-applicable-rules test."],
            refs="ADR-010",
        ),
    },
    {
        "key": "STORY-5.2.2", "parent": "FEATURE-5.2",
        "title": "Persist RuleEvaluation as append-only and evidence-linked",
        "module": "compliance-engine", "labels": ["type:feature", "area:backend", "area:database", *HACKATHON_LABELS, "risk:low"],
        "priority": "high", "state": "Backlog", "cycle": "cycle-4",
        "description": desc(
            "As an Auditor, every RuleEvaluation is persisted as append-only and evidence-linked, "
            "never edited or deleted, including by a later override [CMP-003, BR-CMP-003].",
            acceptance=["The repository layer exposes no update/delete path for RuleEvaluation.", "Every RuleEvaluation references its supporting evidence (Clause/SupplierCheck) via evidence_refs."],
            dependencies="STORY-5.2.1.",
            tasks=["Confirm repository exposes only add/list/get.", "Add evidence-ref population logic and its test."],
        ),
    },
    {
        "key": "FEATURE-5.3", "parent": "EPIC-5",
        "title": "FEATURE: Compliance results UI",
        "module": "compliance-engine", "labels": ["type:feature", "area:frontend", *HACKATHON_LABELS],
        "priority": "high", "state": "Backlog", "cycle": "cycle-4",
        "description": desc("Make every decision explainable in the UI, not just correct in the backend."),
    },
    {
        "key": "STORY-5.3.1", "parent": "FEATURE-5.3",
        "title": "Build the compliance review results screen",
        "module": "compliance-engine", "labels": ["type:feature", "area:frontend", "area:ux", *HACKATHON_LABELS, "risk:low"],
        "priority": "high", "state": "Backlog", "cycle": "cycle-4",
        "description": desc(
            "As a Compliance user, I see WHY / EVIDENCE / POLICY / SOURCE for every triggered rule "
            "on the compliance review results screen, not a bare status.",
            acceptance=["The frontend screen renders the final status plus every triggered rule's evidence, policy version, and rationale, matching the product's explainability principle."],
            dependencies="STORY-5.2.1.",
            tasks=["Build the review-results API read-model.", "Build the frontend results screen."],
            refs="docs/00-project/overview.md",
        ),
    },

    # ============================================================ EPIC-6 — Approvals ===============
    {
        "key": "EPIC-6", "parent": None,
        "title": "EPIC: Approvals (Phase 6)",
        "module": "approvals-decisions", "labels": ["type:feature", *HACKATHON_LABELS, "risk:medium"],
        "priority": "urgent", "state": "Backlog", "cycle": "cycle-5",
        "description": desc(
            "Implement Approvals & Decisions' workflow half: the ADR-006 state machine and "
            "Decision assembly from a completed ComplianceReview.",
            acceptance=[
                "A REVIEW outcome correctly creates an ApprovalRequest routed to the triggering rule's approver_role.",
                "Only a user whose Membership role matches can resolve it (BR-APR-001).",
                "Rejecting a required step blocks APPROVE without an explicit override (BR-APR-002).",
                "The supersedes-chain on re-evaluation is correct.",
            ],
            dependencies="Phase 5 (needs a completed ComplianceReview to route).",
            refs="docs/09-planning/roadmap.md (Phase 6)",
        ),
    },
    {
        "key": "FEATURE-6.1", "parent": "EPIC-6",
        "title": "FEATURE: ApprovalWorkflow and routing",
        "module": "approvals-decisions", "labels": ["type:feature", "area:backend", *HACKATHON_LABELS],
        "priority": "high", "state": "Backlog", "cycle": "cycle-5",
        "description": desc("Route a REVIEW outcome to the correct human approver(s)."),
    },
    {
        "key": "STORY-6.1.1", "parent": "FEATURE-6.1",
        "title": "Route REVIEW outcomes to the correct approver_role",
        "module": "approvals-decisions", "labels": ["type:feature", "area:backend", *HACKATHON_LABELS, "risk:medium"],
        "priority": "high", "state": "Backlog", "cycle": "cycle-5",
        "description": desc(
            "As a Compliance user, a REVIEW outcome is routed to the correct approver_role based on "
            "the organization's configured ApprovalWorkflow [APR-001].",
            acceptance=[
                "ApprovalWorkflow entity created (trigger_condition, ordered steps).",
                "Routing correctly selects the highest-severity triggered rule's approver_role when multiple REVIEW rules fire.",
            ],
            dependencies="EPIC-5.",
            tasks=["Create ApprovalWorkflow model.", "Implement the routing selection logic.", "Add a multiple-REVIEW-rules test."],
        ),
    },
    {
        "key": "STORY-6.1.2", "parent": "FEATURE-6.1",
        "title": "Support multi-step approval chains",
        "module": "approvals-decisions", "labels": ["type:feature", "area:backend", *HACKATHON_LABELS, "risk:medium"],
        "priority": "medium", "state": "Backlog", "cycle": "cycle-5",
        "description": desc(
            "As a Compliance user, I can configure multi-step approval chains (e.g., Legal then "
            "Director) for high-severity cases [APR-003].",
            acceptance=["An ApprovalWorkflow can have more than one ordered step.", "A Decision cannot reach APPROVE until every required step in the chain resolves."],
            dependencies="STORY-6.1.1.",
            tasks=["Extend the workflow model to ordered multi-step chains.", "Add a multi-step resolution test."],
        ),
    },
    {
        "key": "FEATURE-6.2", "parent": "EPIC-6",
        "title": "FEATURE: ApprovalRequest state machine",
        "module": "approvals-decisions", "labels": ["type:feature", "area:backend", *HACKATHON_LABELS],
        "priority": "high", "state": "Backlog", "cycle": "cycle-5",
        "description": desc("The DB-backed state machine for individual approval requests (ADR-006)."),
    },
    {
        "key": "STORY-6.2.1", "parent": "FEATURE-6.2",
        "title": "Enforce role-matched resolution of an ApprovalRequest",
        "module": "approvals-decisions", "labels": ["type:feature", "area:backend", "type:security", *HACKATHON_LABELS, "risk:high", "mvp:required"],
        "priority": "urgent", "state": "Backlog", "cycle": "cycle-5",
        "description": desc(
            "As an Approver, I can resolve an ApprovalRequest only if my Membership role matches "
            "its required approver_role [APR-002, BR-APR-001].",
            acceptance=[
                "ApprovalRequest entity created with a DB-backed state machine (pending->approved/rejected/expired).",
                "A cross-role resolution attempt is rejected and covered by a test.",
                "Every transition emits an AuditEvent (ADR-006).",
            ],
            dependencies="STORY-6.1.1, EPIC-0 FEATURE-0.3 (audit helper).",
            tasks=["Create ApprovalRequest model + state machine.", "Implement the role-match guard.", "Wire the audit-event emission on every transition."],
        ),
    },
    {
        "key": "STORY-6.2.2", "parent": "FEATURE-6.2",
        "title": "Block APPROVE on a rejected required step",
        "module": "approvals-decisions", "labels": ["type:feature", "area:backend", *HACKATHON_LABELS, "risk:medium"],
        "priority": "high", "state": "Backlog", "cycle": "cycle-5",
        "description": desc(
            "As the system, rejecting any required ApprovalRequest in a workflow blocks the overall "
            "Decision from reaching APPROVE without an explicit override [BR-APR-002].",
            acceptance=["A rejected required step prevents automatic APPROVE.", "Only an explicit, justified override (FEATURE-6.3) can move past it."],
            dependencies="STORY-6.2.1.",
            tasks=["Implement the rejection-blocks-approval guard.", "Add its test."],
        ),
    },
    {
        "key": "STORY-6.2.3", "parent": "FEATURE-6.2",
        "title": "Expire an ApprovalRequest past its SLA and escalate",
        "module": "approvals-decisions", "labels": ["type:feature", "area:backend", *HACKATHON_LABELS, "risk:medium"],
        "priority": "medium", "state": "Backlog", "cycle": "cycle-5",
        "description": desc(
            "As the system, an ApprovalRequest that exceeds its configured SLA moves to expired and "
            "emits an escalation event [APR-003 partial, BR-APR-003].",
            acceptance=["A Celery task checks pending requests against a configurable SLA duration (exact default is a documented TBD per BR-APR-003) and transitions expired ones, emitting an escalation AuditEvent."],
            dependencies="STORY-6.2.1.",
            tasks=["Implement the Celery SLA-check task.", "Wire the expiration transition and escalation event."],
        ),
    },
    {
        "key": "FEATURE-6.3", "parent": "EPIC-6",
        "title": "FEATURE: Decision assembly and override",
        "module": "approvals-decisions", "labels": ["type:feature", "area:backend", *HACKATHON_LABELS],
        "priority": "high", "state": "Backlog", "cycle": "cycle-5",
        "description": desc("Every completed review becomes a Decision; overrides are explicit and audited."),
    },
    {
        "key": "STORY-6.3.1", "parent": "FEATURE-6.3",
        "title": "Create a Decision from every completed ComplianceReview",
        "module": "approvals-decisions", "labels": ["type:feature", "area:backend", *HACKATHON_LABELS, "risk:low"],
        "priority": "high", "state": "Backlog", "cycle": "cycle-5",
        "description": desc(
            "As the system, every completed ComplianceReview produces a Decision preserving the "
            "exact PolicyVersion used [DEC-001, BR-DEC-001].",
            acceptance=["Decision entity created (status, valid_until, supersedes_decision_id, overridden, override_justification).", "Created automatically on review completion, one-to-one with the ComplianceReview."],
            dependencies="STORY-6.2.1.",
            tasks=["Create Decision model.", "Implement automatic creation on review completion."],
        ),
    },
    {
        "key": "STORY-6.3.2", "parent": "FEATURE-6.3",
        "title": "Allow authorized manual override of a Decision",
        "module": "approvals-decisions", "labels": ["type:feature", "area:backend", *HACKATHON_LABELS, "risk:medium"],
        "priority": "high", "state": "Backlog", "cycle": "cycle-5",
        "description": desc(
            "As an authorized Approver, I can manually override a Decision with a mandatory "
            "justification, without deleting the original evaluation record [DEC-002, BR-DEC-003].",
            acceptance=[
                "Override requires a non-empty justification string; the original RuleEvaluation set is untouched.",
                "A decision.overridden audit event is recorded with original_outcome, justification, overridden_by.",
            ],
            dependencies="STORY-6.3.1.",
            tasks=["Implement the override endpoint with mandatory-justification validation.", "Wire the decision.overridden audit event."],
        ),
    },
    {
        "key": "FEATURE-6.4", "parent": "EPIC-6",
        "title": "FEATURE: Re-evaluation triggers",
        "module": "approvals-decisions", "labels": ["type:feature", "area:backend", *HACKATHON_LABELS],
        "priority": "high", "state": "Backlog", "cycle": "cycle-5",
        "description": desc("A Decision never changes in place; it is superseded by a new one."),
    },
    {
        "key": "STORY-6.4.1", "parent": "FEATURE-6.4",
        "title": "Trigger re-evaluation on expiry or underlying change",
        "module": "approvals-decisions", "labels": ["type:feature", "area:backend", *HACKATHON_LABELS, "risk:medium"],
        "priority": "high", "state": "Backlog", "cycle": "cycle-5",
        "description": desc(
            "As the system, I trigger re-evaluation when a Decision's validity expires or its "
            "underlying ContractVersion/PolicyVersion changes [DEC-003, BR-DEC-004].",
            acceptance=[
                "An expiring valid_until, a new ContractVersion, or a newly published PolicyVersion affecting previously-evaluated rules emits compliance.review_required.",
                "The resulting new Decision sets supersedes_decision_id to the prior one; the prior Decision is never edited in place (BR-DEC-002).",
            ],
            dependencies="STORY-6.3.1.",
            tasks=["Implement the three trigger conditions.", "Implement the supersedes-chain creation logic.", "Add a test covering all three trigger paths."],
        ),
    },

    # ============================================================ EPIC-7 — Evidence/Audit ==========
    {
        "key": "EPIC-7", "parent": None,
        "title": "EPIC: Evidence & Audit (Phase 7)",
        "module": "evidence-audit", "labels": ["type:feature", *HACKATHON_LABELS, "risk:medium"],
        "priority": "urgent", "state": "Backlog", "cycle": "cycle-5",
        "description": desc(
            "Implement Evidence & Audit's non-blockchain half: evidence packaging, the "
            "deterministic Merkle root, and full audit-catalog coverage across everything built so "
            "far.",
            acceptance=[
                "Every Decision produced in Phase 6 has a corresponding EvidencePackage whose merkle_root is recomputable and matches.",
                "The audit log demonstrably covers every state-changing action exercised by the Phase 0-6 test suites.",
                "The Decision Passport view renders a complete, human-readable 'why' narrative for a real decision end to end.",
            ],
            dependencies="Phase 6 (needs a real Decision to package).",
            refs="docs/09-planning/roadmap.md (Phase 7)",
        ),
    },
    {
        "key": "FEATURE-7.1", "parent": "EPIC-7",
        "title": "FEATURE: EvidencePackage assembly and Merkle root",
        "module": "evidence-audit", "labels": ["type:feature", "area:backend", *HACKATHON_LABELS],
        "priority": "high", "state": "Backlog", "cycle": "cycle-5",
        "description": desc("The tamper-evident bundle backing every Decision."),
    },
    {
        "key": "STORY-7.1.1", "parent": "FEATURE-7.1",
        "title": "Assemble a complete EvidencePackage for every Decision",
        "module": "evidence-audit", "labels": ["type:feature", "area:backend", *HACKATHON_LABELS, "risk:low"],
        "priority": "high", "state": "Backlog", "cycle": "cycle-5",
        "description": desc(
            "As the system, I assemble a complete EvidencePackage for every Decision, including "
            "document hashes, policy version, rule evaluations, and reviewer identities [EVD-001].",
            acceptance=["Evidence and EvidencePackage entities created.", "Every Decision from EPIC-6 gets exactly one EvidencePackage.", "The package includes every field listed in the Decision Passport description."],
            dependencies="EPIC-6.",
            tasks=["Create Evidence/EvidencePackage models.", "Implement the assembly logic pulling from Decision/ComplianceReview/RuleEvaluation/Contract/Supplier."],
            refs="docs/00-project/overview.md, docs/03-domain/evidence.md",
        ),
    },
    {
        "key": "STORY-7.1.2", "parent": "FEATURE-7.1",
        "title": "Compute a deterministic, recomputable Merkle root",
        "module": "evidence-audit", "labels": ["type:feature", "area:backend", *HACKATHON_LABELS, "risk:medium", "mvp:required"],
        "priority": "high", "state": "Backlog", "cycle": "cycle-5",
        "description": desc(
            "As an Auditor, I can recompute an EvidencePackage's merkle_root at any time and get "
            "the same value [EVD-002, BR-EVD-001].",
            acceptance=["A fixed, documented canonical ordering of evidence items is used.", "Recomputing the Merkle root from the persisted Evidence set always matches the stored value."],
            dependencies="STORY-7.1.1.",
            tasks=["Implement the deterministic Merkle-root computation with documented canonical ordering.", "Add a recomputation-matches test."],
            refs="docs/06-blockchain/evidence-model.md",
        ),
    },
    {
        "key": "FEATURE-7.2", "parent": "EPIC-7",
        "title": "FEATURE: Full audit catalog coverage",
        "module": "evidence-audit", "labels": ["type:feature", "area:backend", *HACKATHON_LABELS],
        "priority": "high", "state": "Backlog", "cycle": "cycle-5",
        "description": desc("Close any gap between the documented event catalog and what's actually emitted."),
    },
    {
        "key": "STORY-7.2.1", "parent": "FEATURE-7.2",
        "title": "Audit and close gaps against the documented event catalog",
        "module": "evidence-audit", "labels": ["type:test", "area:backend", *HACKATHON_LABELS, "risk:medium"],
        "priority": "high", "state": "Backlog", "cycle": "cycle-5",
        "description": desc(
            "As an Auditor, I can see an AuditEvent for every state-changing action across "
            "Identity, Suppliers, Contracts, Policy, Compliance, and Approvals built so far [AUD-001].",
            acceptance=["The event catalog in docs/03-domain/audit.md is cross-checked against actual emitted events from every EPIC 0-6 use case.", "Any gap found is closed by adding the missing emit_audit_event() call."],
            dependencies="EPIC-0 through EPIC-6.",
            tasks=["Audit every use case built so far for a missing audit-event emission.", "Close each gap found.", "Add a coverage test asserting every documented event type has at least one emission test."],
            refs="docs/03-domain/audit.md",
        ),
    },
    {
        "key": "FEATURE-7.3", "parent": "EPIC-7",
        "title": "FEATURE: Decision Passport",
        "module": "evidence-audit", "labels": ["type:feature", "area:frontend", *HACKATHON_LABELS],
        "priority": "high", "state": "Backlog", "cycle": "cycle-5",
        "description": desc("The human-readable 'why was this approved?' view."),
    },
    {
        "key": "STORY-7.3.1", "parent": "FEATURE-7.3",
        "title": "Build the Decision Passport view",
        "module": "evidence-audit", "labels": ["type:feature", "area:frontend", "area:backend", *HACKATHON_LABELS, "risk:low", "mvp:required"],
        "priority": "high", "state": "Backlog", "cycle": "cycle-5",
        "description": desc(
            "As a Compliance user or external auditor, I can view a complete, reproducible 'why "
            "was this approved?' narrative for any Decision, months or years later.",
            acceptance=["The Decision Passport view renders decision id, supplier, contract, document hashes, policies evaluated (with version), rules triggered, external sources consulted, AI executions (model/prompt version), reviewers, final decision, and timestamp, all sourced from immutable records."],
            dependencies="STORY-7.1.1.",
            tasks=["Build the Decision Passport read-model API.", "Build the frontend view."],
        ),
    },

    # ============================================================ EPIC-8 — Blockchain ==============
    {
        "key": "EPIC-8", "parent": None,
        "title": "EPIC: Blockchain (Phase 8, Hackathon Cut)",
        "module": "blockchain-trust-layer", "labels": ["type:feature", "area:blockchain", *HACKATHON_LABELS, "risk:high"],
        "priority": "urgent", "state": "Backlog", "cycle": "cycle-5",
        "description": desc(
            "Resolve ADR-007 via a technical spike, implement the chosen AnchoringProvider adapter, "
            "build the public verification page, and freeze scope for the hackathon submission. "
            "This is the end of the Hackathon Cut.",
            acceptance=[
                "A complete, demoable, publicly verifiable anchored Decision exists and is reachable via the public verification page before judging opens 2026-11-05, and remains live through 2026-12-05.",
                "ADR-007 is resolved to Accepted with a working default adapter, or the documented last-resort fallback is live instead.",
            ],
            dependencies="Phase 7 (needs a real EvidencePackage to anchor).",
            refs="docs/09-planning/roadmap.md (Phase 8), docs/08-hackathon/fallback-mvp.md",
        ),
    },
    {
        "key": "FEATURE-8.1", "parent": "EPIC-8",
        "title": "FEATURE: AnchoringProvider spike (ADR-007)",
        "module": "blockchain-trust-layer", "labels": ["type:spike", "area:blockchain", *HACKATHON_LABELS],
        "priority": "urgent", "state": "Backlog", "cycle": "cycle-5",
        "description": desc("Pick the default anchoring provider for the hackathon demo before building production code against it."),
    },
    {
        "key": "STORY-8.1.1", "parent": "FEATURE-8.1",
        "title": "Spike: attempt Constellation, fall back to EVM L2 testnet",
        "module": "blockchain-trust-layer", "labels": ["type:spike", "area:blockchain", *HACKATHON_LABELS, "risk:high"],
        "priority": "urgent", "state": "Backlog", "cycle": "cycle-5",
        "description": desc(
            "As the engineering team, I know which AnchoringProvider adapter to ship for the "
            "hackathon demo before building against it in production code.",
            acceptance=[
                "A timeboxed spike attempts Constellation Network first, falls back to an EVM L2 testnet if Constellation's SDK/tooling proves too heavy, and evaluates ICP/Caffeine AI only if it shows unusually low integration effort.",
                "ADR-007's status is updated to Accepted with the chosen adapter and rationale documented.",
            ],
            dependencies="EPIC-7.",
            tasks=["Attempt Constellation SDK integration.", "If infeasible within budget, attempt the EVM L2 testnet path (viem/ethers + minimal hash-anchoring contract).", "Document findings and update ADR-007."],
            refs="ADR-007, docs/06-blockchain/anchoring-providers.md",
        ),
    },
    {
        "key": "FEATURE-8.2", "parent": "EPIC-8",
        "title": "FEATURE: BlockchainAnchor implementation",
        "module": "blockchain-trust-layer", "labels": ["type:feature", "area:blockchain", *HACKATHON_LABELS],
        "priority": "urgent", "state": "Backlog", "cycle": "cycle-5",
        "description": desc("Anchor an EvidencePackage hash for real, with a documented fallback if the chain integration slips."),
    },
    {
        "key": "STORY-8.2.1", "parent": "FEATURE-8.2",
        "title": "Anchor an EvidencePackage hash via the chosen AnchoringProvider",
        "module": "blockchain-trust-layer", "labels": ["type:feature", "area:blockchain", *HACKATHON_LABELS, "risk:high", "mvp:required"],
        "priority": "urgent", "state": "Backlog", "cycle": "cycle-5",
        "description": desc(
            "As the system, I anchor an EvidencePackage's hash via the chosen AnchoringProvider, "
            "submitting only the hash, never raw contract/supplier data [EVD-003, EVD-004, BR-EVD-002].",
            acceptance=[
                "BlockchainAnchor entity created (provider, anchor_ref, submitted_at, proof).",
                "submit_hash/get_proof/verify implemented against the chosen adapter.",
                "A test confirms no raw document/personal-data field ever appears in the anchor payload.",
            ],
            dependencies="STORY-8.1.1.",
            tasks=["Create BlockchainAnchor model.", "Implement the interface against the chosen adapter.", "Add the payload-content test."],
        ),
    },
    {
        "key": "STORY-8.2.2", "parent": "FEATURE-8.2",
        "title": "Implement the signed-hash transparency-log fallback",
        "module": "blockchain-trust-layer", "labels": ["type:feature", "area:blockchain", *HACKATHON_LABELS, "risk:medium", "mvp:required"],
        "priority": "urgent", "state": "Backlog", "cycle": "cycle-5",
        "description": desc(
            "As the system, if no chain integration lands in time, I fall back to a signed hash + "
            "timestamp published to a public, git-backed transparency log, clearly labeled as a "
            "fallback, not a blockchain anchor.",
            acceptance=[
                "The fallback implements the same AnchoringProvider interface so nothing above it in the stack changes.",
                "The product UI and hackathon submission materials both clearly label this mode as a fallback verification mechanism.",
            ],
            dependencies="STORY-8.1.1 (activates only if the spike/adapter miss the deadline, per risks.md).",
            tasks=["Implement the signed-hash + transparency-log adapter.", "Add the explicit fallback label in both API response and UI copy."],
            refs="docs/09-planning/risks.md",
        ),
    },
    {
        "key": "FEATURE-8.3", "parent": "EPIC-8",
        "title": "FEATURE: Public verification page",
        "module": "blockchain-trust-layer", "labels": ["type:feature", "area:frontend", "area:blockchain", *HACKATHON_LABELS],
        "priority": "urgent", "state": "Backlog", "cycle": "cycle-5",
        "description": desc("Let anyone verify an anchored decision without logging in."),
    },
    {
        "key": "STORY-8.3.1", "parent": "FEATURE-8.3",
        "title": "Build the public, unauthenticated verification page",
        "module": "blockchain-trust-layer", "labels": ["type:feature", "area:frontend", "area:security", *HACKATHON_LABELS, "risk:medium", "mvp:required"],
        "priority": "urgent", "state": "Backlog", "cycle": "cycle-5",
        "description": desc(
            "As a third party (auditor, counterparty, hackathon judge), I can verify an anchored "
            "Decision's hash without logging in [EVD-003].",
            acceptance=["A public page accepts a decision/evidence reference or raw hash, calls verify(), and renders a plain-language result.", "The page works correctly whether the real chain adapter or the fallback is in effect."],
            dependencies="STORY-8.2.1.",
            tasks=["Build the public verification API endpoint (no auth).", "Build the public frontend page."],
            refs="docs/06-blockchain/verification.md",
        ),
    },
    {
        "key": "FEATURE-8.4", "parent": "EPIC-8",
        "title": "FEATURE: Landing page rewrite",
        "module": "frontend", "labels": ["type:documentation", "area:frontend", *HACKATHON_LABELS],
        "priority": "high", "state": "Backlog", "cycle": "cycle-5",
        "description": desc("Replace the legacy legal-ERP marketing copy with JuriSense Gate's actual positioning."),
    },
    {
        "key": "STORY-8.4.1", "parent": "FEATURE-8.4",
        "title": "Rewrite landing-data.ts for JuriSense Gate",
        "module": "frontend", "labels": ["type:documentation", "area:frontend", *HACKATHON_LABELS, "risk:low"],
        "priority": "high", "state": "Backlog", "cycle": "cycle-5",
        "description": desc(
            "As a prospective customer visiting the marketing site, I see JuriSense Gate's actual "
            "positioning, features, and pricing -- not the legacy legal-ERP copy.",
            acceptance=["frontend/src/lib/landing-data.ts is fully rewritten per pivot-migration.md item (d) -- features, plans, steps, faqs, allPlansInclude all replaced.", "Only the contact object and TypeScript type declarations are carried over unchanged."],
            dependencies="docs/02-business/pricing-strategy.md existing with final plan tiers.",
            tasks=["Rewrite features.", "Rewrite plans.", "Rewrite steps/faqs/allPlansInclude.", "Visual QA against the existing landing page components."],
        ),
    },
    {
        "key": "FEATURE-8.5", "parent": "EPIC-8",
        "title": "FEATURE: Hackathon submission prep",
        "module": "hackathon", "labels": ["type:documentation", *HACKATHON_LABELS],
        "priority": "urgent", "state": "Backlog", "cycle": "cycle-5",
        "description": desc("Everything needed to actually file the submission, per docs/08-hackathon/submission-plan.md."),
    },
    {
        "key": "STORY-8.5.1", "parent": "FEATURE-8.5",
        "title": "Submit the complete working demo before judging opens",
        "module": "hackathon", "labels": ["type:documentation", *HACKATHON_LABELS, "risk:high"],
        "priority": "urgent", "state": "Backlog", "cycle": "cycle-5",
        "description": desc(
            "As the team, I submit a complete, working demo before judging opens on 2026-11-05.",
            acceptance=[
                "Pitch deck, demo video (covering the full Supplier->Contract->Policy->Compliance->Approval->Decision->Evidence->Anchor->Verify pipeline), and an updated root README.md are all complete.",
                "The public verification page is live and stable through the 2026-12-05 judging close.",
            ],
            dependencies="All of EPIC-8.",
            tasks=["Record the demo video.", "Build the pitch deck.", "Update root README.md.", "File the submission."],
            refs="docs/08-hackathon/submission-plan.md, demo-scenario.md, pitch.md",
        ),
    },

    # ============================================================ EPIC-9 — Integrations (post-hack)
    {
        "key": "EPIC-9", "parent": None,
        "title": "EPIC: Integrations (Phase 9, post-hackathon)",
        "module": "integrations", "labels": ["type:feature", "scope:commercial", "risk:medium"],
        "priority": "medium", "state": "Backlog", "cycle": None,
        "description": desc(
            "Build out the Integrations bounded context beyond the Phase 1 scaffold into real, "
            "production-usable connectors, unblocking customers who need JuriSense Gate to "
            "participate in their existing procurement and e-signature workflows.",
            dependencies="Phase 8 complete -- needs stable, final domain events across every context built through the Hackathon Cut.",
            refs="docs/09-planning/roadmap.md (Phase 9)",
        ),
    },
    {
        "key": "FEATURE-9.1", "parent": "EPIC-9",
        "title": "Implement outbound webhooks with retry and signature verification",
        "module": "integrations", "labels": ["type:feature", "area:backend", "area:api", "scope:commercial", "risk:medium"],
        "priority": "medium", "state": "Backlog", "cycle": None,
        "description": desc(
            "Implement INT-002's four lifecycle webhooks (supplier.review.completed, "
            "contract.review.completed, approval.required, decision.completed) with retry/backoff "
            "and HMAC signature verification, so third-party systems can react to compliance "
            "events reliably and securely.",
        ),
    },
    {
        "key": "FEATURE-9.2", "parent": "EPIC-9",
        "title": "Integrate DocuSign for contract execution",
        "module": "integrations", "labels": ["type:feature", "area:backend", "scope:commercial", "risk:medium"],
        "priority": "medium", "state": "Backlog", "cycle": None,
        "description": desc("Connect contract execution to DocuSign so an APPROVEd contract can move directly to e-signature without leaving the platform."),
    },
    {
        "key": "FEATURE-9.3", "parent": "EPIC-9",
        "title": "Build the Slack notification connector",
        "module": "integrations", "labels": ["type:feature", "area:backend", "scope:commercial", "risk:low"],
        "priority": "low", "state": "Backlog", "cycle": None,
        "description": desc("Push approval-required and decision-completed notifications into a customer's Slack workspace."),
    },
    {
        "key": "FEATURE-9.4", "parent": "EPIC-9",
        "title": "Lay ERP connector groundwork",
        "module": "integrations", "labels": ["type:research", "area:backend", "scope:commercial", "risk:low"],
        "priority": "low", "state": "Backlog", "cycle": None,
        "description": desc("Lay the adapter groundwork (not a full integration) for future accounts-payable/procurement-system sync, informed by real pilot customers' actual ERP systems."),
    },

    # ============================================================ EPIC-10 — Enterprise (post-hack)
    {
        "key": "EPIC-10", "parent": None,
        "title": "EPIC: Enterprise (Phase 10, post-hackathon)",
        "module": "enterprise", "labels": ["type:feature", "scope:enterprise", "risk:high"],
        "priority": "medium", "state": "Backlog", "cycle": None,
        "description": desc(
            "Harden the platform for larger and more regulated buyers: real billing, stronger "
            "tenant isolation, and enterprise identity.",
            dependencies="Phase 9 (a working integration layer helps enterprise conversations); commercially gated on having real pilot customers from Phases 8-9.",
            refs="docs/09-planning/roadmap.md (Phase 10)",
        ),
    },
    {
        "key": "FEATURE-10.1", "parent": "EPIC-10",
        "title": "Integrate a real payment gateway (ADR-014)",
        "module": "enterprise", "labels": ["type:feature", "area:backend", "scope:enterprise", "risk:high"],
        "priority": "medium", "state": "Backlog", "cycle": None,
        "description": desc("Resolve ADR-014's deliberately deferred payment decision by integrating Stripe or a Brazilian equivalent, converting the modeled-but-unenforced plan state machine into real, billed subscriptions."),
    },
    {
        "key": "FEATURE-10.2", "parent": "EPIC-10",
        "title": "Harden multi-tenancy with PostgreSQL Row-Level Security",
        "module": "enterprise", "labels": ["type:security", "area:database", "scope:enterprise", "risk:high"],
        "priority": "medium", "state": "Backlog", "cycle": None,
        "description": desc("Add PostgreSQL RLS on top of the existing logical multi-tenancy (organization_id filtering) as defense-in-depth, addressing ADR-003's explicitly deferred v1.x hardening item."),
    },
    {
        "key": "FEATURE-10.3", "parent": "EPIC-10",
        "title": "Support custom and versioned roles",
        "module": "enterprise", "labels": ["type:feature", "area:backend", "scope:enterprise", "risk:medium"],
        "priority": "low", "state": "Backlog", "cycle": None,
        "description": desc("Let an enterprise customer define roles beyond the seeded 10, and version role definitions the way PolicyVersion is versioned."),
    },
    {
        "key": "FEATURE-10.4", "parent": "EPIC-10",
        "title": "Add SSO for enterprise identity providers",
        "module": "enterprise", "labels": ["type:feature", "area:security", "scope:enterprise", "risk:medium"],
        "priority": "low", "state": "Backlog", "cycle": None,
        "description": desc("Add SAML/OIDC support so enterprise buyers can provision and deprovision users through their existing IdP instead of the platform's own invite flow."),
    },

    # ============================================================ EPIC-11 — International (post-hack)
    {
        "key": "EPIC-11", "parent": None,
        "title": "EPIC: International (Phase 11, post-hackathon)",
        "module": "international", "labels": ["type:feature", "scope:international", "risk:high"],
        "priority": "low", "state": "Backlog", "cycle": None,
        "description": desc(
            "Extend JuriSense Gate beyond Brazil via the Core Platform / Jurisdiction Pack "
            "separation the domain model and Policy Engine were deliberately designed to support "
            "from Phase 2/4 onward.",
            dependencies="Phase 10 (enterprise-grade multi-tenancy and billing should be solid before multi-jurisdiction complexity is layered on).",
            refs="docs/09-planning/roadmap.md (Phase 11)",
        ),
    },
    {
        "key": "FEATURE-11.1", "parent": "EPIC-11",
        "title": "Formalize the Jurisdiction Pack architecture as a code seam",
        "module": "international", "labels": ["type:refactor", "area:backend", "scope:international", "risk:high"],
        "priority": "low", "state": "Backlog", "cycle": None,
        "description": desc("Separate Core Platform logic from jurisdiction-specific identifier schemes, sanctions sources, and policy rule packs, so a new jurisdiction never requires touching core domain logic."),
    },
    {
        "key": "FEATURE-11.2", "parent": "EPIC-11",
        "title": "Build the first non-Brazil jurisdiction pack",
        "module": "international", "labels": ["type:feature", "area:backend", "scope:international", "risk:high"],
        "priority": "low", "state": "Backlog", "cycle": None,
        "description": desc("Build a complete pack (US or EU, exact choice TBD pending commercial priority) with its own supplier-identity scheme, sanctions sources, and a GDPR-flavored policy rule pack."),
    },
    {
        "key": "FEATURE-11.3", "parent": "EPIC-11",
        "title": "Localize the frontend for the new market",
        "module": "international", "labels": ["type:feature", "area:frontend", "scope:international", "risk:low"],
        "priority": "low", "state": "Backlog", "cycle": None,
        "description": desc("Translate and adapt the frontend copy for the new market, building on the content structure established by the Phase 8 landing-page rewrite."),
    },

    # ============================================================ Cross-cutting: Security ==========
    {
        "key": "SEC-SEED-1", "parent": None,
        "title": "Set up the mandatory cross-tenant-isolation regression suite",
        "module": "security", "labels": ["type:security", "area:security", "scope:foundation", *HACKATHON_LABELS, "risk:high"],
        "priority": "urgent", "state": "Ready", "cycle": "cycle-1",
        "description": desc(
            "As the team, we run one reusable cross-tenant-access test suite against every new "
            "bounded context, per ADR-003/ADR-016, instead of re-inventing tenant-isolation tests "
            "per feature.",
            acceptance=["A shared test helper creates two organizations and asserts no role in Org A can read or write Org B's data for the entity under test.", "Every new context's test suite (starting with EPIC-0/1) imports and uses this helper."],
            refs="ADR-003, ADR-016, docs/auditorias/",
        ),
    },
    {
        "key": "SEC-SEED-2", "parent": None,
        "title": "Add dependency and secret scanning to CI",
        "module": "security", "labels": ["type:infrastructure", "area:security", "area:devops", "scope:foundation", *HACKATHON_LABELS, "risk:medium"],
        "priority": "high", "state": "Ready", "cycle": "cycle-1",
        "description": desc(
            "As the team, CI fails if a dependency with a known vulnerability or a committed secret "
            "is introduced.",
            acceptance=["A dependency-scanning step runs on every push.", "A secret-scanning step runs on every push and on the full git history at least once."],
            refs="docs/07-engineering/security.md, ci-cd.md",
        ),
    },
    {
        "key": "SEC-SEED-3", "parent": None,
        "title": "Add rate limiting to the public verification endpoint",
        "module": "security", "labels": ["type:security", "area:security", "area:api", *HACKATHON_LABELS, "risk:medium"],
        "priority": "high", "state": "Backlog", "cycle": "cycle-5",
        "description": desc(
            "As the system, I rate-limit the unauthenticated public verification endpoint "
            "(GET /verify/{hash}) so it cannot be used for enumeration or denial-of-service against "
            "a hackathon-judged, publicly reachable feature.",
            acceptance=["A per-IP rate limit is enforced on the public verification route.", "The limit does not block legitimate hackathon-judging traffic under expected load."],
            dependencies="FEATURE-8.3.",
            refs="docs/07-engineering/security.md",
        ),
    },
    {
        "key": "SEC-SEED-4", "parent": None,
        "title": "Add prompt-injection and RAG-poisoning defenses",
        "module": "security", "labels": ["type:security", "area:security", "area:ai", *HACKATHON_LABELS, "risk:high"],
        "priority": "high", "state": "Backlog", "cycle": "cycle-3",
        "description": desc(
            "As the system, I treat every AI-extracted or retrieved document/clause as untrusted "
            "data, never as instructions, so a malicious contract or poisoned policy playbook "
            "cannot manipulate extraction or retrieval behavior.",
            acceptance=["System-prompt isolation and output-schema enforcement are in place for every AI Gateway call (STORY-3.3.1).", "A test exercises a contract containing an embedded prompt-injection attempt and asserts extraction output is unaffected."],
            dependencies="STORY-3.3.1.",
            refs="docs/05-ai/guardrails.md",
        ),
    },

    # ============================================================ Cross-cutting: DevOps & Infra ====
    {
        "key": "DEVOPS-SEED-1", "parent": None,
        "title": "Extend docker-compose.yml with MinIO and a Celery worker",
        "module": "devops-infra", "labels": ["type:infrastructure", "area:devops", "scope:foundation", *HACKATHON_LABELS, "risk:low", "tech:docker"],
        "priority": "high", "state": "Ready", "cycle": "cycle-1",
        "description": desc(
            "As a developer, my local dev environment matches the target architecture: object "
            "storage (MinIO) and an async worker (Celery) alongside the existing frontend/backend/"
            "redis services.",
            acceptance=["docker compose up -d starts a working MinIO service and a Celery worker service.", "The backend can reach both from within the compose network."],
            refs="ADR-006, ADR-008, docs/07-engineering/development-workflow.md",
        ),
    },
    {
        "key": "DEVOPS-SEED-2", "parent": None,
        "title": "Stand up the CI pipeline (lint, typecheck, tests, build)",
        "module": "devops-infra", "labels": ["type:infrastructure", "area:devops", "scope:foundation", *HACKATHON_LABELS, "risk:medium"],
        "priority": "high", "state": "Ready", "cycle": "cycle-1",
        "description": desc(
            "As the team, every push runs lint, typecheck, unit/integration tests, and a container "
            "build, so regressions are caught before merge.",
            acceptance=["A CI workflow runs uv run ruff check ., uv run pytest, npm run lint, and npm run build on every push.", "A failing step blocks merge."],
            refs="docs/07-engineering/ci-cd.md",
        ),
    },
    {
        "key": "DEVOPS-SEED-3", "parent": None,
        "title": "Document and validate required environment variables on startup",
        "module": "devops-infra", "labels": ["type:infrastructure", "area:devops", "scope:foundation", "risk:low"],
        "priority": "medium", "state": "Backlog", "cycle": "cycle-2",
        "description": desc(
            "As a developer, the backend fails fast with a clear error at startup if a required "
            "environment variable (AI provider keys, storage credentials, anchoring-provider "
            "config) is missing, instead of failing confusingly at first use.",
            acceptance=["A startup validator checks every required env var and lists exactly what's missing."],
            refs="docs/07-engineering/development-workflow.md",
        ),
    },
    {
        "key": "DEVOPS-SEED-4", "parent": None,
        "title": "Stand up a staging environment for the hackathon demo",
        "module": "devops-infra", "labels": ["type:infrastructure", "area:devops", *HACKATHON_LABELS, "risk:medium"],
        "priority": "high", "state": "Backlog", "cycle": "cycle-4",
        "description": desc(
            "As the team, we have a stable, publicly reachable staging deployment before the "
            "hackathon submission, distinct from local dev, so the demo and public verification "
            "page are reliably reachable by judges through the judging window.",
            acceptance=["A staging deployment is reachable over HTTPS.", "It stays up through the 2026-12-05 judging close, per FEATURE-8.5's acceptance criteria."],
            dependencies="EPIC-8.",
            refs="docs/04-architecture/deployment.md",
        ),
    },

    # ============================================================ Hackathon tracking issue =========
    {
        "key": "HACKATHON-TRACKING", "parent": None,
        "title": "Legal Hack 2026 — submission readiness tracker",
        "module": "hackathon", "labels": ["type:documentation", *HACKATHON_LABELS],
        "priority": "urgent", "state": "Backlog", "cycle": "cycle-5",
        "description": desc(
            "Top-level tracking issue for the BLI Legal Tech Hackathon 2 / Legal Hack 2026 "
            "submission. Not a container for implementation work (that lives in EPIC-0 through "
            "EPIC-8, all labeled scope:hackathon) -- this issue tracks the submission act itself "
            "and its explicit checklist.",
            acceptance=[
                "Every item in docs/08-hackathon/fallback-mvp.md's checklist is Done or has a labeled fallback in place.",
                "docs/08-hackathon/submission-plan.md's checklist (demo, deck, public repo, technical write-up, team info, BUIDL page, manual rules check) is complete.",
                "Submission is filed before 2026-11-05.",
            ],
            dependencies="EPIC-8 (in particular FEATURE-8.5).",
            refs="docs/08-hackathon/",
        ),
    },
]
