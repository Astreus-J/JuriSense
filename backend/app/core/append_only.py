"""DB-layer enforcement of an append-only invariant (product decision 2026-10-10, #184;
`evidence_override_addenda` added the same day, #187; extended to Policy & Compliance's own
append-only tables by the 2026-10-12 security audit).

Lives in `app/core` (not owned by any one context) because more than one bounded context
needs the identical mechanism on its own tables -- Evidence & Audit originally, Policy &
Compliance now too -- and a context must never import another context's infrastructure
module (`docs/04-architecture/components.md`). Each context calls `register_append_only_
guards(Base.metadata, table_names=(...))` once, at the bottom of its own `models.py`, naming
only the tables it owns.

An append-only table's repository already exposes only `add`/`get`/`list`, never an update or
delete method -- that convention is not a guarantee: nothing stops a raw UPDATE/DELETE issued
through the application's own DB credential (a future ORM-layer bug, a stray raw-SQL call, or a
console session using that same credential) from mutating or erasing an immutable record. This
module makes the invariant a database constraint instead, via a `BEFORE UPDATE OR DELETE`
trigger per table that unconditionally rejects the operation.

Security review (2026-10-10): this trigger's actual threat model is bugs and mistakes made
through the application's own, non-privileged database role -- NOT a malicious actor who already
holds `ALTER TABLE`/ownership privilege on these tables, who can disable or drop the trigger
outright (`ALTER TABLE ... DISABLE TRIGGER`, or a superuser's `session_replication_role`). This
product has no separate, more-restricted application DB role configured yet (single external
Neon database, `DATABASE_URL` used for both migrations and runtime -- `docs/04-architecture/
security-architecture.md` §4); until that separation exists, treat this as defense against
accidents and bugs, not against a fully compromised database credential.

Attached as SQLAlchemy DDL events on each `Table`, dialect-aware (`postgresql` for the real
database, `sqlite` for the test suite's `Base.metadata.create_all`), so the same invariant the
Postgres migrations install in production is also exercised by every test that tries to bypass a
repository and mutate a row directly. `CREATE OR REPLACE FUNCTION` makes it harmless for more
than one context to register this same Postgres function.
"""

from collections.abc import Iterable

from sqlalchemy import DDL, MetaData, Table, event

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


def register_append_only_guards(metadata: MetaData, *, table_names: Iterable[str]) -> None:
    """Call once per context, after all of that context's tables are defined on `metadata`
    (i.e. at the bottom of that context's `models.py`), naming only the tables it owns. The
    Postgres trigger function is (re-)created on every call (`before_create`, idempotent via
    `CREATE OR REPLACE`) so it already exists by the time each table's own `after_create`
    trigger -- which references it by name -- runs, regardless of which context's `models.py`
    happens to import first."""
    event.listen(
        metadata, "before_create", _POSTGRES_REJECT_FUNCTION.execute_if(dialect="postgresql")
    )
    for name in table_names:
        _guard(metadata.tables[name])
