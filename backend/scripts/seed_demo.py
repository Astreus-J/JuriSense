"""Seeds the hackathon demo tenant described in docs/08-hackathon/demo-scenario.md's "Setup"
section: "Acme Tecnologia Ltda." with an admin, a `legal`-role approver, and a published
PolicyVersion containing LGPD-001/LEGAL-008/FIN-003 (plus SANC-001, a bonus BLOCK rule the
checklist calls out as a nice-to-have).

Run from inside the backend container (the service already has `app` installed and a working
`DATABASE_URL`): `docker compose exec backend uv run python scripts/seed_demo.py`.

Idempotent: re-running after a successful seed exits cleanly instead of creating a duplicate
organization (detected via the admin's email already being registered).

FIN-004 is deliberately NOT seeded here: its documented `approver_role` is "director"
(docs/03-domain/policy-engine.md), which is not a value of `app.identity.domain.constants.Role`
-- no user in this codebase can actually be assigned that role, so a REVIEW from FIN-004 would
have nowhere to route. That's a real gap in the domain rules, not something this script should
paper over by inventing a role; flagged in docs/08-hackathon/hackathon-checklist.md instead.
"""

import asyncio
import sys
from pathlib import Path

# Makes `app.*` importable regardless of the invoking cwd/PYTHONPATH (e.g. a plain
# `uv run python scripts/seed_demo.py` only puts this file's own directory on sys.path).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.db import task_session  # noqa: E402 -- must follow the sys.path fix above
from app.identity.application.auth_service import register_organization
from app.identity.application.user_service import create_user
from app.identity.domain.constants import Plan, Role
from app.identity.domain.errors import EmailAlreadyRegisteredError
from app.policies.application.policy_service import create_policy
from app.policies.application.publish_service import publish_version
from app.policies.application.rule_service import create_rule

ADMIN_EMAIL = "admin@acme-tecnologia.demo"
LEGAL_EMAIL = "legal@acme-tecnologia.demo"
DEMO_PASSWORD = "DemoJuriSense2026!"  # noqa: S105 -- demo-only fixture credential, not a real secret

RULES_YAML = [
    """
rule:
  id: LGPD-001
  name: DPA Required for Personal Data Processing
when:
  processes_personal_data: true
  dpa_present: false
result:
  status: BLOCK
severity: critical
approver_role: null
""",
    """
rule:
  id: LEGAL-008
  name: Unlimited Liability Requires Legal Review
when:
  contract.liability.type: unlimited
result:
  status: REVIEW
severity: high
approver_role: legal
""",
    """
rule:
  id: FIN-003
  name: High-Value Contract Requires Legal Approval
when:
  contract.value.brl: { gte: 250000 }
result:
  status: REVIEW
severity: medium
approver_role: legal
""",
    """
rule:
  id: SANC-001
  name: Supplier on a Sanctions List
when:
  supplier.sanctions_hit: true
result:
  status: BLOCK
severity: critical
approver_role: null
""",
]


async def main() -> None:
    async with task_session() as session:
        try:
            admin = await register_organization(
                session,
                organization_name="Acme Tecnologia Ltda.",
                full_name="Admin Demo",
                email=ADMIN_EMAIL,
                password=DEMO_PASSWORD,
                plan=Plan.BUSINESS,
            )
        except EmailAlreadyRegisteredError:
            print(
                f"Already seeded: {ADMIN_EMAIL} is already registered. "
                "Nothing to do (script is idempotent, not destructive)."
            )
            return

        print(f"Created organization 'Acme Tecnologia Ltda.' (id={admin.organization_id})")
        print(f"  Admin user: {ADMIN_EMAIL} / {DEMO_PASSWORD}")

        legal_user = await create_user(
            session,
            admin=admin,
            full_name="Legal Approver Demo",
            email=LEGAL_EMAIL,
            password=DEMO_PASSWORD,
            role=Role.LEGAL,
        )
        print(f"  Legal approver user: {LEGAL_EMAIL} / {DEMO_PASSWORD} (role={legal_user.role})")

        policy, version = await create_policy(
            session,
            organization_id=admin.organization_id,
            actor_id=admin.id,
            name="Acme Supplier & Contract Compliance Policy",
        )
        print(f"Created policy '{policy.name}' (id={policy.id}), draft version {version.id}")

        for rule_yaml in RULES_YAML:
            rule = await create_rule(
                session,
                organization_id=admin.organization_id,
                actor_id=admin.id,
                policy_id=policy.id,
                version_id=version.id,
                rule_yaml=rule_yaml,
            )
            print(f"  Added rule {rule.rule_key} ({rule.result_status}, severity={rule.severity})")

        published = await publish_version(
            session,
            organization_id=admin.organization_id,
            actor_id=admin.id,
            policy_id=policy.id,
            version_id=version.id,
        )
        print(f"Published policy version {published.version_number} (id={published.id})")
        print(
            "\nDemo tenant ready. Next: docs/08-hackathon/demo-scenario.md Part 1 (upload the "
            "CloudDocs supplier + contract from docs/08-hackathon/demo-assets/contracts/)."
        )


if __name__ == "__main__":
    asyncio.run(main())
