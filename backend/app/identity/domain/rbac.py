"""Default RBAC grid (ADR-003 / ADR-012 — RBAC as data, not hardcoded branches).

`DEFAULT_ROLE_GRID` is the role x module x action permission table seeded, as literal
`ModulePermission` rows, for every user at the moment they're created (organization
registration, admin-created user, invite acceptance — see `permission_service.py`). An
org admin may still grant a specific user permissions beyond this default via a per-user
`ModulePermission` override (STORY-0.2.4/ADR-012), exactly like any other row in that table.

Reviewable grid (C=create, R=read, U=update, D=delete; every cell not listed is all-False).
Columns: suppliers / contracts / policies / compliance_reviews / approvals / evidence /
integrations / organization_settings.

| Role        | sup  | con  | pol  | cmp_rev | apr  | evd  | int  | org_settings |
|-------------|------|------|------|---------|------|------|------|--------------|
| admin       | CRUD | CRUD | CRUD | CRUD    | CRUD | CRUD | CRUD | CRUD         |
| procurement | CRUD | CRUD | R    | R       | R    | -    | -    | -            |
| legal       | R    | CRU  | CRU  | CRU     | RU   | R    | -    | -            |
| compliance  | R    | R    | CRU  | CRU     | RU   | R    | -    | -            |
| privacy     | R    | R    | CRU  | R       | RU   | R    | -    | -            |
| security    | R    | R    | CRU  | R       | RU   | R    | R    | R            |
| finance     | R    | R    | CRU  | R       | RU   | R    | -    | -            |
| approver    | R    | R    | R    | RU      | RU   | R    | -    | -            |
| auditor     | R    | R    | R    | R       | R    | R    | R    | R            |
| viewer      | R    | R    | R    | R       | R    | R    | -    | -            |

Rationale per role (grounded in each role's real-world function; the module vocabulary is
`Module`, ADR-003), cross-checked against `docs/01-product/personas.md`:

- **admin**: owns the org, full access everywhere including `organization_settings`.
- **procurement**: owns the Supplier/Contract lifecycle end to end (full CRUD); needs to see
  the policy/compliance/approval status attached to their own suppliers/contracts but not
  edit those records, and has no reason to see evidence, integrations, or org settings.
  Unlike the five specialist reviewer roles below, Procurement is never itself an
  `approver_role` target (`personas.md` gives it no approval queue), so `approvals` stays
  read-only.
- **legal**, **compliance**, **privacy**, **security**, **finance**: these five share the
  same *shape* of access, because `personas.md` documents the same two capabilities for each
  of them: (1) rule-authoring rights on their own policy category (LEGAL-*/contract clauses
  for Legal, sanctions/regulatory for Compliance, LGPD/privacy for Privacy, security-category
  for Security, value-threshold FIN-*/finance for Finance) — hence `create`+`update` on
  `policies`, not just `read`; and (2) "an approval queue for `approver_role = <role>`" — each
  one can itself be the `approver_role` a `Rule` routes a `REVIEW` to (e.g. `LEGAL-008`
  routes to `legal`, `FIN-003`/`FIN-004` to `legal`/`director`, a security-category rule to
  `security`), and *resolving* a request in that queue means updating its status — hence
  `read`+`update` on `approvals`, not just `read`. `ApprovalRequest` rows are created by the
  Compliance Engine automatically when a rule fires (`docs/03-domain/approvals.md`), never by
  a human, so none of these five roles gets `create` on `approvals`.
  - **legal**: additionally owns drafting/negotiating contracts (`create`/`read`/`update` on
    `contracts`) and triggers/reviews compliance runs (`create`/`read`/`update` on
    `compliance_reviews`); only reads `suppliers` (owned by Procurement).
  - **compliance**: mirrors legal's write access on `compliance_reviews` (their core job);
    only reads `suppliers`/`contracts` (owned by Procurement/Legal).
  - **privacy**, **security**, **finance**: narrower specialists — read (not write) on
    `suppliers`/`contracts`/`compliance_reviews`; their write access is scoped to their own
    policy category and their own approval queue, not the underlying review record itself.
  - **security** additionally keeps read access to `integrations`/`organization_settings`
    (security-relevant configuration) — the only one of these five with that visibility,
    matching its broader "reviews the whole business surface" persona description.
  - No delete anywhere for any of the five — nothing in this domain is meant to be destroyed,
    only versioned/superseded.
- **approver**: the generic Director/Approver persona — exists specifically to resolve
  approval requests without owning a policy category of its own, so it gets read+update on
  `approvals` and on `compliance_reviews` (to see why a review triggered an approval), read
  elsewhere, no `organization_settings` access (per STORY-1.1.1's own example).
- **auditor**: BR-EVD-003-style read-only visibility into *everything*, including
  `integrations`/`organization_settings`, and never a write anywhere — auditors observe, they
  never act.
- **viewer**: the generic read-only role for day-to-day business visibility; unlike auditor,
  it has no visibility into `integrations`/`organization_settings`, which are
  admin/security/auditor-only surfaces.
"""

from dataclasses import dataclass

from app.identity.domain.constants import Module, Role


@dataclass(frozen=True)
class Permission:
    can_create: bool = False
    can_read: bool = False
    can_update: bool = False
    can_delete: bool = False


_NONE = Permission()
_READ = Permission(can_read=True)
_READ_UPDATE = Permission(can_read=True, can_update=True)
_CREATE_READ_UPDATE = Permission(can_create=True, can_read=True, can_update=True)
_FULL = Permission(can_create=True, can_read=True, can_update=True, can_delete=True)

DEFAULT_ROLE_GRID: dict[Role, dict[Module, Permission]] = {
    Role.ADMIN: dict.fromkeys(Module, _FULL),
    Role.PROCUREMENT: {
        Module.SUPPLIERS: _FULL,
        Module.CONTRACTS: _FULL,
        Module.POLICIES: _READ,
        Module.COMPLIANCE_REVIEWS: _READ,
        Module.APPROVALS: _READ,
        Module.EVIDENCE: _NONE,
        Module.INTEGRATIONS: _NONE,
        Module.ORGANIZATION_SETTINGS: _NONE,
    },
    Role.LEGAL: {
        Module.SUPPLIERS: _READ,
        Module.CONTRACTS: _CREATE_READ_UPDATE,
        Module.POLICIES: _CREATE_READ_UPDATE,
        Module.COMPLIANCE_REVIEWS: _CREATE_READ_UPDATE,
        Module.APPROVALS: _READ_UPDATE,
        Module.EVIDENCE: _READ,
        Module.INTEGRATIONS: _NONE,
        Module.ORGANIZATION_SETTINGS: _NONE,
    },
    Role.COMPLIANCE: {
        Module.SUPPLIERS: _READ,
        Module.CONTRACTS: _READ,
        Module.POLICIES: _CREATE_READ_UPDATE,
        Module.COMPLIANCE_REVIEWS: _CREATE_READ_UPDATE,
        Module.APPROVALS: _READ_UPDATE,
        Module.EVIDENCE: _READ,
        Module.INTEGRATIONS: _NONE,
        Module.ORGANIZATION_SETTINGS: _NONE,
    },
    Role.PRIVACY: {
        Module.SUPPLIERS: _READ,
        Module.CONTRACTS: _READ,
        Module.POLICIES: _CREATE_READ_UPDATE,
        Module.COMPLIANCE_REVIEWS: _READ,
        Module.APPROVALS: _READ_UPDATE,
        Module.EVIDENCE: _READ,
        Module.INTEGRATIONS: _NONE,
        Module.ORGANIZATION_SETTINGS: _NONE,
    },
    Role.SECURITY: {
        Module.SUPPLIERS: _READ,
        Module.CONTRACTS: _READ,
        Module.POLICIES: _CREATE_READ_UPDATE,
        Module.COMPLIANCE_REVIEWS: _READ,
        Module.APPROVALS: _READ_UPDATE,
        Module.EVIDENCE: _READ,
        Module.INTEGRATIONS: _READ,
        Module.ORGANIZATION_SETTINGS: _READ,
    },
    Role.FINANCE: {
        Module.SUPPLIERS: _READ,
        Module.CONTRACTS: _READ,
        Module.POLICIES: _CREATE_READ_UPDATE,
        Module.COMPLIANCE_REVIEWS: _READ,
        Module.APPROVALS: _READ_UPDATE,
        Module.EVIDENCE: _READ,
        Module.INTEGRATIONS: _NONE,
        Module.ORGANIZATION_SETTINGS: _NONE,
    },
    Role.APPROVER: {
        Module.SUPPLIERS: _READ,
        Module.CONTRACTS: _READ,
        Module.POLICIES: _READ,
        Module.COMPLIANCE_REVIEWS: _READ_UPDATE,
        Module.APPROVALS: _READ_UPDATE,
        Module.EVIDENCE: _READ,
        Module.INTEGRATIONS: _NONE,
        Module.ORGANIZATION_SETTINGS: _NONE,
    },
    Role.AUDITOR: dict.fromkeys(Module, _READ),
    Role.VIEWER: {
        Module.SUPPLIERS: _READ,
        Module.CONTRACTS: _READ,
        Module.POLICIES: _READ,
        Module.COMPLIANCE_REVIEWS: _READ,
        Module.APPROVALS: _READ,
        Module.EVIDENCE: _READ,
        Module.INTEGRATIONS: _NONE,
        Module.ORGANIZATION_SETTINGS: _NONE,
    },
}
