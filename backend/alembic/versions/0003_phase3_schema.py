"""phase 3: KYC/AML, audit logs, compliance flags, security fields

Revision ID: 0003_phase3
Revises: 0002_phase2
Create Date: 2026-09-19

"""
from alembic import op
import sqlalchemy as sa

revision = "0003_phase3"
down_revision = "0002_phase2"
branch_labels = None
depends_on = None

kyc_status = sa.Enum("PENDING", "APPROVED", "REJECTED", name="kycstatus")


def upgrade() -> None:
    op.add_column("users", sa.Column("country", sa.String(), nullable=True))
    op.add_column("users", sa.Column("suspended_previous_state", sa.String(), nullable=True))

    op.add_column(
        "payments",
        sa.Column("is_flagged", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("payments", sa.Column("flag_reason", sa.String(), nullable=True))
    op.add_column(
        "payments",
        sa.Column("held_for_review", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.add_column(
        "withdrawals",
        sa.Column("is_flagged", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("withdrawals", sa.Column("flag_reason", sa.String(), nullable=True))
    op.add_column(
        "withdrawals",
        sa.Column("held_for_review", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.create_table(
        "kyc_submissions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column("country", sa.String(), nullable=False),
        sa.Column("document_type", sa.String(), nullable=False),
        sa.Column("document_reference", sa.String(), nullable=False),
        sa.Column("status", kyc_status, nullable=False),
        sa.Column("rejection_reason", sa.String(), nullable=True),
        sa.Column("reviewed_by", sa.String(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("actor_user_id", sa.String(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("resource_type", sa.String(), nullable=False),
        sa.Column("resource_id", sa.String(), nullable=True),
        sa.Column("details", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("kyc_submissions")
    op.drop_column("withdrawals", "held_for_review")
    op.drop_column("withdrawals", "flag_reason")
    op.drop_column("withdrawals", "is_flagged")
    op.drop_column("payments", "held_for_review")
    op.drop_column("payments", "flag_reason")
    op.drop_column("payments", "is_flagged")
    op.drop_column("users", "suspended_previous_state")
    op.drop_column("users", "country")
