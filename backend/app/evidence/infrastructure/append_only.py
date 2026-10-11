"""DB-layer enforcement of the append-only invariant on the evidence tables (product
decision 2026-10-10, closing #184; `evidence_override_addenda` added the same day, #187).

`audit_events`, `evidence_packages`, `evidence` and `evidence_override_addenda` are
append-only by convention already --
their repositories (`repositories.py`) expose only `add`/`get`/`list`, never an update or delete
method. That convention is not a guarantee: nothing stops a raw UPDATE/DELETE issued through the
application's own DB credential -- a future ORM-layer bug, a stray raw-SQL call, or a console
session using that same credential -- from mutating or erasing anchored evidence. This module
makes the invariant a database constraint instead, via a `BEFORE UPDATE OR DELETE` trigger per
table that unconditionally rejects the operation.

Security review (2026-10-10): this trigger's actual threat model is bugs and mistakes made
through the application's own, non-privileged database role -- NOT a malicious actor who already
holds `ALTER TABLE`/ownership privilege on these tables, who can disable or drop the trigger
outright (`ALTER TABLE ... DISABLE TRIGGER`, or a superuser's `session_replication_role`). This
product has no separate, more-restricted application DB role configured yet (single external
Neon database, `DATABASE_URL` used for both migrations and runtime -- `docs/04-architecture/
security-architecture.md` §4); until that separation exists, treat this as defense against
accidents and bugs, not against a fully compromised database credential.

`blockchain_anchors` is deliberately NOT guarded here: `anchoring_service._refresh_from_provider`
legitimately updates `status`/`proof`/`confirmed_at` in place as a submission moves from
`submitted` to `confirmed`/`failed` -- that table has a real update path, so it stays governed by
application-layer checks only.

Attached as SQLAlchemy DDL events on each `Table`, dialect-aware (`postgresql` for the real
database, `sqlite` for the test suite's `Base.metadata.create_all`), so the same invariant the
Postgres migration (`alembic/versions/`) installs in production is also exercised by every test
that tries to bypass a repository and mutate a row directly.
"""

from sqlalchemy import DDL, MetaData, Table, event

APPEND_ONLY_TABLE_NAMES = (
    "audit_events",
    "evidence_packages",
    "evidence",
    "evidence_override_addenda",
)

_POSTGRES_REJECT_FUNCTION = DDL(
    """
    CREATE OR REPLACE FUNCTION reject_append_only_mutation() RETURNS TRIGGER AS $$
    BEGIN
        RAISE EXCEPTION '% rows are append-only: % is not allowed', TG_TABLE_NAME, TG_OP;
    END;
    $$ LANGUAGE plpgsql;
    """
)


def _guard(table: Table) -> None:
    name = table.name
    event.listen(
        table,
        "after_create",
        DDL(
            f"CREATE TRIGGER trg_{name}_append_only "
            f"BEFORE UPDATE OR DELETE ON {name} "
            f"FOR EACH ROW EXECUTE FUNCTION reject_append_only_mutation();"
        ).execute_if(dialect="postgresql"),
    )
    event.listen(
        table,
        "after_create",
        DDL(
            f"CREATE TRIGGER trg_{name}_append_only_update "
            f"BEFORE UPDATE ON {name} "
            f"BEGIN SELECT RAISE(ABORT, '{name} rows are append-only: UPDATE is not allowed'); END;"
        ).execute_if(dialect="sqlite"),
    )
    event.listen(
        table,
        "after_create",
        DDL(
            f"CREATE TRIGGER trg_{name}_append_only_delete "
            f"BEFORE DELETE ON {name} "
            f"BEGIN SELECT RAISE(ABORT, '{name} rows are append-only: DELETE is not allowed'); END;"
        ).execute_if(dialect="sqlite"),
    )


def register_append_only_guards(metadata: MetaData) -> None:
    """Call once, after all of this context's tables are defined on `metadata` (i.e. at the
    bottom of `models.py`). The Postgres trigger function is created on `before_create` (fires
    once, before any table in `metadata` is created) so it already exists by the time each
    table's own `after_create` trigger -- which references it by name -- runs."""
    event.listen(
        metadata, "before_create", _POSTGRES_REJECT_FUNCTION.execute_if(dialect="postgresql")
    )
    for name in APPEND_ONLY_TABLE_NAMES:
        _guard(metadata.tables[name])
