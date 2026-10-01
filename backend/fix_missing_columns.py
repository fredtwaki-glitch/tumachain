import os
from sqlalchemy import create_engine, text

engine = create_engine(os.environ["DATABASE_URL"])

statements = [
    # users — missing columns
    'ALTER TABLE users ADD COLUMN IF NOT EXISTS username VARCHAR',
    'ALTER TABLE users ADD COLUMN IF NOT EXISTS phone_number VARCHAR',
    'ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_photo_url VARCHAR',
    'ALTER TABLE users ADD COLUMN IF NOT EXISTS preferred_settlement_method VARCHAR',
    'ALTER TABLE users ADD COLUMN IF NOT EXISTS notification_preferences VARCHAR',
    'ALTER TABLE users ADD COLUMN IF NOT EXISTS kyc_status VARCHAR',
    'ALTER TABLE users ADD COLUMN IF NOT EXISTS kyb_status VARCHAR',
    'ALTER TABLE users ADD COLUMN IF NOT EXISTS aml_status VARCHAR',
    # users — matching unique indexes from migration 0004
    'CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users (username)',
    'CREATE UNIQUE INDEX IF NOT EXISTS ix_users_phone_number ON users (phone_number)',
    # payments — missing columns
    'ALTER TABLE payments ADD COLUMN IF NOT EXISTS recipient_identifier VARCHAR',
    'ALTER TABLE payments ADD COLUMN IF NOT EXISTS destination_chain VARCHAR',
    'ALTER TABLE payments ADD COLUMN IF NOT EXISTS settlement_status VARCHAR',
    'ALTER TABLE payments ADD COLUMN IF NOT EXISTS environment VARCHAR',
]

with engine.begin() as conn:
    for stmt in statements:
        print("Running:", stmt)
        conn.execute(text(stmt))

print("\nAll statements applied successfully.")
