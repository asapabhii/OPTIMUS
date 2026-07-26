"""009: Connector configuration — backfill depth, fast-path N, cost bounds.

Per-viewer, per-connector configuration. Controls ingestion behavior
and cost guardrails.

Revision ID: 009
Revises: 008
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "connector_configs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("viewer_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("source_id", UUID(as_uuid=True), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("provider_type", sa.String(100), nullable=False),
        sa.Column("fast_path_n", sa.Integer(), server_default=sa.text("50")),
        sa.Column("backfill_depth_days", sa.Integer(), server_default=sa.text("365")),
        sa.Column("max_items", sa.Integer(), nullable=True),
        sa.Column("is_fast_path_complete", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("is_full_backfill_complete", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index("ix_cc_viewer_source", "connector_configs", ["viewer_id", "source_id"], unique=True)
    op.execute("ALTER TABLE connector_configs ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_table("connector_configs")
