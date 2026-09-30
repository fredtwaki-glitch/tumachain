"""phase 2: cross-chain routing, ledger balances, withdrawals

Revision ID: 0002_phase2
Revises: 0001_initial
Create Date: 2026-09-19

"""
from alembic import op
import sqlalchemy as sa

revision = "0002_phase2"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

asset = sa.Enum("BTC", "ETH", "SOL", "EVMT", "USDC", name="asset")
network = sa.Enum(
    "BITCOIN_TESTNET", "ETHEREUM_SEPOLIA", "SOLANA_DEVNET", "EVM_TESTNET", name="network"
)
withdrawal_status = sa.Enum(
    "REQUESTED", "VALIDATING", "PROCESSING", "COMPLETED", "FAILED", "REJECTED",
    name="withdrawalstatus",
)


def upgrade() -> None:
    op.add_column("payments", sa.Column("settlement_asset", asset, nullable=True))
    op.add_column(
        "payments",
        sa.Column("conversion_rate", sa.Numeric(precision=36, scale=18), nullable=True),
    )
    op.add_column(
        "payments",
        sa.Column(
            "conversion_fee", sa.Numeric(precision=36, scale=18), nullable=False, server_default="0"
        ),
    )
    op.add_column(
        "payments", sa.Column("final_amount", sa.Numeric(precision=36, scale=18), nullable=True)
    )
    op.add_column("payments", sa.Column("blockchain_tx_hash", sa.String(), nullable=True))
    op.add_column("payments", sa.Column("failure_reason", sa.String(), nullable=True))

    op.create_table(
        "ledger_balances",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("asset", asset, nullable=False),
        sa.Column("amount", sa.Numeric(precision=36, scale=18), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("user_id", "asset", name="uq_user_asset_ledger"),
    )

    op.create_table(
        "withdrawals",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("transaction_id", sa.String(), nullable=False, unique=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("asset", asset, nullable=False),
        sa.Column("destination_network", network, nullable=False),
        sa.Column("destination_address", sa.String(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=36, scale=18), nullable=False),
        sa.Column("network_fee", sa.Numeric(precision=36, scale=18), nullable=False),
        sa.Column("status", withdrawal_status, nullable=False),
        sa.Column("idempotency_key", sa.String(), nullable=True, unique=True),
        sa.Column("blockchain_tx_hash", sa.String(), nullable=True),
        sa.Column("failure_reason", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_withdrawals_transaction_id", "withdrawals", ["transaction_id"])
    op.create_index("ix_withdrawals_idempotency_key", "withdrawals", ["idempotency_key"])


def downgrade() -> None:
    op.drop_table("withdrawals")
    op.drop_table("ledger_balances")
    op.drop_column("payments", "failure_reason")
    op.drop_column("payments", "blockchain_tx_hash")
    op.drop_column("payments", "final_amount")
    op.drop_column("payments", "conversion_fee")
    op.drop_column("payments", "conversion_rate")
    op.drop_column("payments", "settlement_asset")
