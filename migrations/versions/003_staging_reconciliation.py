"""003: Staging/reconciliation tables — staged candidates and merge log.

Staged candidates are NEVER answerable (REQ-3.6a).
The three-way sort: novel, confident match, conflict.

Revision ID: 003
Revises: 002
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "staged_candidates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("source_id", UUID(as_uuid=True), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("source_ref", sa.String(500), nullable=False),
        sa.Column("extracted_name", sa.String(500), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("attributes", JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column("sort_outcome", sa.String(50), nullable=True),
        sa.Column("matched_entity_id", UUID(as_uuid=True), sa.ForeignKey("entities.id"), nullable=True),
        sa.Column("match_confidence", sa.Float(), nullable=True),
        sa.Column("match_explanation", sa.Text(), nullable=True),
        sa.Column("processed", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("viewer_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index("ix_staged_unprocessed", "staged_candidates", ["viewer_id", "processed"],
                    postgresql_where=sa.text("processed = false"))

    op.create_table(
        "merge_log",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("source_entity_id", UUID(as_uuid=True), sa.ForeignKey("entities.id"), nullable=False),
        sa.Column("target_entity_id", UUID(as_uuid=True), sa.ForeignKey("entities.id"), nullable=False),
        sa.Column("merge_type", sa.String(50), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("explanation", sa.Text(), server_default=""),
        sa.Column("auto_decision_id", UUID(as_uuid=True), nullable=True),
        sa.Column("reversed", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("viewer_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.execute("ALTER TABLE staged_candidates ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE merge_log ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_table("merge_log")
    op.drop_table("staged_candidates")
