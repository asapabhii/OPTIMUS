"""004: Belief cache with evidence-set-hash memoization.

Cache key: (entity_id, evidence_set_hash, viewer_id).
A cache hit is valid ONLY while the hash is unchanged.

Revision ID: 004
Revises: 003
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ARRAY

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "beliefs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("entity_id", UUID(as_uuid=True), sa.ForeignKey("entities.id"), nullable=False),
        sa.Column("belief_text", sa.Text(), nullable=False),
        sa.Column("evidence_set_hash", sa.String(64), nullable=False),
        sa.Column("evidence_ids", ARRAY(UUID(as_uuid=True)), server_default=sa.text("ARRAY[]::uuid[]")),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("is_stale", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("recomputed_from_partial", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("formed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("viewer_id", UUID(as_uuid=True), nullable=False, index=True),
    )

    # Memoization index: the cache lookup
    op.create_index(
        "ix_beliefs_memo",
        "beliefs",
        ["entity_id", "evidence_set_hash", "viewer_id"],
        unique=True,
    )

    op.create_index(
        "ix_beliefs_entity_viewer",
        "beliefs",
        ["entity_id", "viewer_id"],
    )

    op.execute("ALTER TABLE beliefs ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_table("beliefs")
