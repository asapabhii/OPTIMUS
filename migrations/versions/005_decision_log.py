"""005: Auto-decision log — every automatic decision visible and reversible.

Gate 3: every auto-merge and auto-classification shows here.
Approval must take SECONDS, not minutes (REQ-11.1).

Revision ID: 005
Revises: 004
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auto_decisions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("decision_type", sa.String(50), nullable=False),
        sa.Column("input_data", JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column("output_data", JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column("explanation", sa.Text(), server_default=""),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("applied_automatically", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("reversed", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("reversed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reversed_reason", sa.Text(), nullable=True),
        sa.Column("viewer_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index("ix_auto_decisions_type", "auto_decisions", ["decision_type", "viewer_id"])
    op.create_index(
        "ix_auto_decisions_pending",
        "auto_decisions",
        ["viewer_id"],
        postgresql_where=sa.text("reversed = false"),
    )

    op.execute("ALTER TABLE auto_decisions ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_table("auto_decisions")
