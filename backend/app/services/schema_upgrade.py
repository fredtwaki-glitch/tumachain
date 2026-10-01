"""
Self-healing compatibility bootstrap for the `users`/`payments` V2 columns.

This exists because the project historically relied on
`Base.metadata.create_all()` rather than Alembic for day-to-day schema
changes -- and `create_all()` never alters a table that already exists.
That meant older SQLite dev databases *and* older Postgres deployments
could both be left missing columns that newer code expects.

This function is now dialect-aware and safe to run unconditionally on
every single app startup, on SQLite or Postgres:

  - Postgres natively supports `ADD COLUMN IF NOT EXISTS`, so columns are
    added idempotently with no need to inspect existing columns first.
  - SQLite does not support `IF NOT EXISTS` on `ADD COLUMN`, so existing
    columns are inspected first and only missing ones are added.

Alembic (`alembic upgrade head`) is still the preferred, authoritative
migration path going forward -- especially for brand-new tables, which
`Base.metadata.create_all()` already handles correctly on any dialect.
This function exists purely as a safety net so a deploy without shell/
console access (e.g. Render's free tier) can still self-repair existing
tables that drifted out of sync with the models.
"""
from sqlalchemy import inspect, text

from app.database import engine, Base


def _add_column_if_missing(conn, inspector, dialect: str, table: str, column: str, ddl: str) -> None:
    if dialect == "postgresql":
        # Postgres has supported "ADD COLUMN IF NOT EXISTS" since 9.6 --
        # idempotent and safe to run on every boot, no inspection needed.
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {ddl}"))
        return

    # SQLite (and other dialects without IF NOT EXISTS support): check first.
    existing_columns = {c["name"] for c in inspector.get_columns(table)}
    if column not in existing_columns:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))


def ensure_v2_schema() -> None:
    # New tables are safe to create on any dialect -- create_all() only
    # creates tables that don't exist yet; it never touches existing ones.
    Base.metadata.create_all(bind=engine)

    dialect = engine.dialect.name
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    with engine.begin() as conn:
        if "users" in tables:
            for column, ddl in [
                ("username", "username VARCHAR"),
                ("phone_number", "phone_number VARCHAR"),
                ("profile_photo_url", "profile_photo_url VARCHAR"),
                ("preferred_settlement_method", "preferred_settlement_method VARCHAR DEFAULT 'stablecoin'"),
                ("notification_preferences", "notification_preferences VARCHAR DEFAULT '{}'"),
                ("kyc_status", "kyc_status VARCHAR DEFAULT 'UNVERIFIED'"),
                ("kyb_status", "kyb_status VARCHAR DEFAULT 'NOT_APPLICABLE'"),
                ("aml_status", "aml_status VARCHAR DEFAULT 'CLEAR'"),
            ]:
                _add_column_if_missing(conn, inspector, dialect, "users", column, ddl)

            # CREATE [UNIQUE] INDEX IF NOT EXISTS is supported natively by
            # both SQLite and Postgres (9.5+), so this line needs no
            # dialect branching.
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users(username)"))
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_phone_number ON users(phone_number)"))

        if "payments" in tables:
            for column, ddl in [
                ("recipient_identifier", "recipient_identifier VARCHAR"),
                ("destination_chain", "destination_chain VARCHAR"),
                ("settlement_status", "settlement_status VARCHAR DEFAULT 'PENDING'"),
                ("environment", "environment VARCHAR DEFAULT 'testnet'"),
            ]:
                _add_column_if_missing(conn, inspector, dialect, "payments", column, ddl)

        # Re-inspect after any ALTERs in case later logic in this process
        # needs an up-to-date column list.
        inspector = inspect(engine)
