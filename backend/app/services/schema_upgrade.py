"""Small compatibility bootstrap for the existing SQLite deployment.

The project historically used SQLAlchemy create_all() instead of Alembic at startup.
This helper adds only V2 columns missing from that legacy schema. Alembic remains the
authoritative migration path for fresh/managed deployments.
"""
from sqlalchemy import inspect, text
from app.database import engine, Base

def ensure_v2_schema():
    if engine.dialect.name != "sqlite":
        return
    insp=inspect(engine)
    tables=set(insp.get_table_names())
    # New V2 tables are safe to create with SQLAlchemy.
    Base.metadata.create_all(bind=engine)
    insp=inspect(engine)
    def add(table, column, ddl):
        cols={c["name"] for c in insp.get_columns(table)}
        if column not in cols:
            with engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))
            insp.invalidate()
    if "users" in tables:
        add("users","username","username VARCHAR")
        add("users","phone_number","phone_number VARCHAR")
        add("users","profile_photo_url","profile_photo_url VARCHAR")
        add("users","preferred_settlement_method","preferred_settlement_method VARCHAR DEFAULT 'stablecoin'")
        add("users","notification_preferences","notification_preferences VARCHAR DEFAULT '{}' ")
        add("users","kyc_status","kyc_status VARCHAR DEFAULT 'UNVERIFIED'")
        add("users","kyb_status","kyb_status VARCHAR DEFAULT 'NOT_APPLICABLE'")
        add("users","aml_status","aml_status VARCHAR DEFAULT 'CLEAR'")
    if "users" in tables:
        with engine.begin() as conn:
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users(username)"))
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_phone_number ON users(phone_number)"))
    if "payments" in tables:
        add("payments","recipient_identifier","recipient_identifier VARCHAR")
        add("payments","destination_chain","destination_chain VARCHAR")
        add("payments","settlement_status","settlement_status VARCHAR DEFAULT 'PENDING'")
        add("payments","environment","environment VARCHAR DEFAULT 'testnet'")
