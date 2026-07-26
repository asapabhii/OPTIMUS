"""008: Task-class routing registry (P28).

Maps task class -> model tier -> Portkey virtual key.
The APPROVED_ONLY tier has NO OVERRIDE (REQ-13.2).

Revision ID: 008
Revises: 007
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ARRAY

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "task_class_routes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("task_class", sa.String(50), nullable=False, unique=True),
        sa.Column("model_tier", sa.String(50), nullable=False),
        sa.Column("portkey_virtual_key", sa.String(255), server_default=""),
        sa.Column("model_allow_list", ARRAY(sa.String(100)), server_default=sa.text("ARRAY[]::varchar[]")),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Seed the default routes
    op.execute("""
        INSERT INTO task_class_routes (task_class, model_tier, model_allow_list, description) VALUES
        ('classification', 'cheapest_adequate', ARRAY['gpt-4o-mini', 'deepseek-chat'], 'High volume, low stakes'),
        ('extraction', 'cheapest_adequate', ARRAY['gpt-4o-mini', 'deepseek-chat'], 'Structured extraction — high volume'),
        ('retrieval_planning', 'mid_tier', ARRAY['gpt-4o', 'claude-sonnet-4-20250514'], 'Query planning, fan-out'),
        ('synthesis', 'most_capable', ARRAY['gpt-4o', 'claude-sonnet-4-20250514'], 'Answer synthesis, reasoning'),
        ('canon_mutation', 'approved_only', ARRAY['gpt-4o'], 'ANYTHING touching canon — NO OVERRIDE')
    """)

    # NOTE: No RLS — system-wide configuration, not per-viewer.


def downgrade() -> None:
    op.drop_table("task_class_routes")
