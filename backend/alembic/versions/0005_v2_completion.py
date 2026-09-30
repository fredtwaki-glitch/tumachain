"""Complete V2 merchant webhook/audit support
Revision ID: 0005_v2_completion
Revises: 0004_v2
"""
from alembic import op
import sqlalchemy as sa
revision="0005_v2_completion"; down_revision="0004_v2"; branch_labels=None; depends_on=None

def upgrade():
    op.create_table("webhook_events",
        sa.Column("id",sa.String(),primary_key=True),
        sa.Column("endpoint_id",sa.String(),sa.ForeignKey("webhook_endpoints.id"),nullable=True),
        sa.Column("event_id",sa.String(),nullable=False,unique=True),
        sa.Column("event_type",sa.String(),nullable=False),
        sa.Column("payload_hash",sa.String(),nullable=False),
        sa.Column("status",sa.String(),nullable=False),
        sa.Column("created_at",sa.DateTime()),
    )
    op.create_index("ix_webhook_events_endpoint_id","webhook_events",["endpoint_id"])
    op.create_index("ix_webhook_events_event_id","webhook_events",["event_id"],unique=True)

def downgrade():
    op.drop_table("webhook_events")
