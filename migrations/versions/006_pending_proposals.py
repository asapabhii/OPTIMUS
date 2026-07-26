"""006: Pending proposals — stored in Phase 1, activated at Gate 5.

At most 1 promotion prompt per answer (P15).
Evidence-class sources BARRED from generating proposals (REQ-6.9b).
The CHECK constraint enforces this at the database level.

Revision ID: 006
Revises: 005
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ARRAY

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pending_proposals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("claim_text", sa.Text(), nullable=False),
        sa.Column("replaces_declaration_id", UUID(as_uuid=True), sa.ForeignKey("declarations.id"), nullable=True),
        sa.Column("replaces_value", sa.Text(), nullable=True),
        sa.Column("evidence_ids", ARRAY(UUID(as_uuid=True)), server_default=sa.text("ARRAY[]::uuid[]")),
        sa.Column("proposed_sor_source_id", UUID(as_uuid=True), sa.ForeignKey("sources.id"), nullable=True),
        sa.Column("source_class_of_origin", sa.String(50), nullable=False),
        sa.Column("surfaced_in_answer_id", UUID(as_uuid=True), nullable=True),
        sa.Column("viewer_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # THE CONSTRAINT: evidence-class sources CANNOT generate proposals (REQ-6.9b)
    op.execute("""
        ALTER TABLE pending_proposals
        ADD CONSTRAINT evidence_class_bar
        CHECK (source_class_of_origin = 'authority')
    """)

    op.execute("ALTER TABLE pending_proposals ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_table("pending_proposals")
