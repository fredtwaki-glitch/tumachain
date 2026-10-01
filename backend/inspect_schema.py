import os
from sqlalchemy import create_engine, inspect

engine = create_engine(os.environ["DATABASE_URL"])
insp = inspect(engine)

all_tables = insp.get_table_names()
print("=== TABLES ===")
for t in sorted(all_tables):
    print(" -", t)

print("\n=== users columns ===")
for c in insp.get_columns("users"):
    print(" -", c["name"])

if "payments" in all_tables:
    print("\n=== payments columns ===")
    for c in insp.get_columns("payments"):
        print(" -", c["name"])

print("\n=== relevant V2 tables present? ===")
for t in ["payment_requests", "settlements", "api_credentials", "webhook_endpoints", "webhook_events"]:
    print(f" - {t}: {'EXISTS' if t in all_tables else 'missing'}")

print("\n=== alembic_version table ===")
if "alembic_version" in all_tables:
    with engine.connect() as conn:
        from sqlalchemy import text
        rows = conn.execute(text("SELECT version_num FROM alembic_version")).fetchall()
        print(" -", rows)
else:
    print(" - no alembic_version table found")
