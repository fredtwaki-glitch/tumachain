"""TumaChain V2 identity, payment links, settlement and merchant layer
Revision ID: 0004_v2
Revises: 0003_phase3
"""
from alembic import op
import sqlalchemy as sa
revision="0004_v2"; down_revision="0003_phase3"; branch_labels=None; depends_on=None

def upgrade():
    op.add_column("users", sa.Column("username", sa.String(), nullable=True)); op.create_index("ix_users_username","users",["username"],unique=True)
    op.add_column("users", sa.Column("phone_number", sa.String(), nullable=True)); op.create_index("ix_users_phone_number","users",["phone_number"],unique=True)
    op.add_column("users", sa.Column("profile_photo_url", sa.String(), nullable=True)); op.add_column("users", sa.Column("preferred_settlement_method", sa.String(), nullable=True)); op.add_column("users", sa.Column("notification_preferences", sa.String(), nullable=True)); op.add_column("users", sa.Column("kyc_status", sa.String(), nullable=True)); op.add_column("users", sa.Column("kyb_status", sa.String(), nullable=True)); op.add_column("users", sa.Column("aml_status", sa.String(), nullable=True))
    op.add_column("payments", sa.Column("recipient_identifier", sa.String(), nullable=True)); op.add_column("payments", sa.Column("destination_chain", sa.String(), nullable=True)); op.add_column("payments", sa.Column("settlement_status", sa.String(), nullable=True)); op.add_column("payments", sa.Column("environment", sa.String(), nullable=True))
    op.create_table("payment_requests",sa.Column("id",sa.String(),primary_key=True),sa.Column("code",sa.String(),unique=True,index=True),sa.Column("creator_id",sa.String(),sa.ForeignKey("users.id"),nullable=False),sa.Column("amount",sa.Numeric(36,18),nullable=False),sa.Column("asset",sa.String(),nullable=False),sa.Column("description",sa.String()),sa.Column("expires_at",sa.DateTime()),sa.Column("status",sa.String(),nullable=False),sa.Column("created_at",sa.DateTime()))
    op.create_table("settlements",sa.Column("id",sa.String(),primary_key=True),sa.Column("payment_id",sa.String(),sa.ForeignKey("payments.id")),sa.Column("user_id",sa.String(),sa.ForeignKey("users.id"),nullable=False),sa.Column("provider",sa.String(),nullable=False),sa.Column("source_asset",sa.String(),nullable=False),sa.Column("destination_method",sa.String(),nullable=False),sa.Column("destination_currency",sa.String()),sa.Column("amount",sa.Numeric(36,18),nullable=False),sa.Column("fee",sa.Numeric(36,18),nullable=False),sa.Column("status",sa.String(),nullable=False),sa.Column("environment",sa.String(),nullable=False),sa.Column("provider_reference",sa.String()),sa.Column("created_at",sa.DateTime()),sa.Column("updated_at",sa.DateTime()))
    op.create_table("api_credentials",sa.Column("id",sa.String(),primary_key=True),sa.Column("user_id",sa.String(),sa.ForeignKey("users.id"),nullable=False),sa.Column("name",sa.String(),nullable=False),sa.Column("key_prefix",sa.String(),nullable=False),sa.Column("key_hash",sa.String(),nullable=False),sa.Column("active",sa.Boolean(),nullable=False),sa.Column("created_at",sa.DateTime()))
    op.create_table("webhook_endpoints",sa.Column("id",sa.String(),primary_key=True),sa.Column("user_id",sa.String(),sa.ForeignKey("users.id"),nullable=False),sa.Column("url",sa.String(),nullable=False),sa.Column("secret_hash",sa.String(),nullable=False),sa.Column("active",sa.Boolean(),nullable=False),sa.Column("created_at",sa.DateTime()))

def downgrade():
    for t in ["webhook_endpoints","api_credentials","settlements","payment_requests"]: op.drop_table(t)
    for c in ["environment","settlement_status","destination_chain","recipient_identifier"]: op.drop_column("payments",c)
    for c in ["aml_status","kyb_status","kyc_status","notification_preferences","preferred_settlement_method","profile_photo_url","phone_number","username"]: op.drop_column("users",c)
