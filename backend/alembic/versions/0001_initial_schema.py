"""initial phase 1 schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-19

"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

user_role = sa.Enum("USER", "COMPLIANCE_OFFICER", "ADMIN", "SUPER_ADMIN", name="userrole")
verification_state = sa.Enum(
    "UNVERIFIED", "EMAIL_VERIFIED", "KYC_PENDING", "KYC_VERIFIED", "KYC_REJECTED", "SUSPENDED",
    name="verificationstate",
)
network = sa.Enum(
    "BITCOIN_TESTNET", "ETHEREUM_SEPOLIA", "SOLANA_DEVNET", "EVM_TESTNET", name="network"
)
asset = sa.Enum("BTC", "ETH", "SOL", "EVMT", "USDC", name="asset")
payment_status = sa.Enum(
    "CREATED", "PENDING", "SUBMITTED", "CONFIRMING", "COMPLETED", "FAILED", "EXPIRED",
    "CANCELLED", name="paymentstatus",
)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=True),
        sa.Column("role", user_role, nullable=False),
        sa.Column("verification_state", verification_state, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("email_verification_token", sa.String(), nullable=True),
        sa.Column("email_verified_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "wallets",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("network", network, nullable=False),
        sa.Column("address", sa.String(), nullable=False),
        sa.Column("mock_private_key", sa.String(), nullable=False),
        sa.Column("balance", sa.Numeric(precision=36, scale=18), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("user_id", "network", name="uq_user_network"),
    )
    op.create_index("ix_wallets_address", "wallets", ["address"])

    op.create_table(
        "payments",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("transaction_id", sa.String(), nullable=False, unique=True),
        sa.Column("sender_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("recipient_email", sa.String(), nullable=False),
        sa.Column("recipient_id", sa.String(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("asset", asset, nullable=False),
        sa.Column("network", network, nullable=False),
        sa.Column("amount", sa.Numeric(precision=36, scale=18), nullable=False),
        sa.Column("network_fee", sa.Numeric(precision=36, scale=18), nullable=False),
        sa.Column("platform_fee", sa.Numeric(precision=36, scale=18), nullable=False),
        sa.Column("status", payment_status, nullable=False),
        sa.Column("is_confirmed", sa.String(), nullable=False),
        sa.Column("idempotency_key", sa.String(), nullable=True, unique=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_payments_recipient_email", "payments", ["recipient_email"])
    op.create_index("ix_payments_transaction_id", "payments", ["transaction_id"])
    op.create_index("ix_payments_idempotency_key", "payments", ["idempotency_key"])


def downgrade() -> None:
    op.drop_table("payments")
    op.drop_table("wallets")
    op.drop_table("users")
