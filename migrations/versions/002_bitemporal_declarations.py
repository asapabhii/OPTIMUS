"""002: Bitemporal declarations (G3) — SoR declarations and resolution rules.

Canon-shaped from day one. Gate 5 RATIFIES rather than re-collects.
Resolution rules carry scope predicates (REQ-6.4b).

Revision ID: 002
Revises: 001
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "declarations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("entity_id", UUID(as_uuid=True), sa.ForeignKey("entities.id"), nullable=True),
        sa.Column("fact_type", sa.String(200), nullable=False),
        sa.Column("declaration_type", sa.String(50), nullable=False),
        sa.Column("declared_value", sa.Text(), nullable=False),
        sa.Column("system_of_record_source_id", UUID(as_uuid=True), sa.ForeignKey("sources.id"), nullable=True),
        sa.Column("scope_predicate", sa.String(500), nullable=True),
        # Bitemporal columns
        sa.Column("valid_from", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tx_from", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("tx_to", sa.DateTime(timezone=True), nullable=True),
        # Ownership
        sa.Column("viewer_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index("ix_declarations_entity", "declarations", ["entity_id"])
    op.create_index("ix_declarations_fact_type", "declarations", ["fact_type"])
    op.create_index(
        "ix_declarations_valid",
        "declarations",
        ["viewer_id", "fact_type"],
        postgresql_where=sa.text("valid_to IS NULL AND tx_to IS NULL"),
    )

    # Resolution rules stored as declarations with declaration_type = 'resolution_rule'
    op.create_table(
        "resolution_rules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("declaration_id", UUID(as_uuid=True), sa.ForeignKey("declarations.id"), nullable=False),
        sa.Column("source_name", sa.String(500), nullable=False),
        sa.Column("target_name", sa.String(500), nullable=False),
        sa.Column("scope_predicate", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("viewer_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.execute("ALTER TABLE declarations ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE resolution_rules ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_table("resolution_rules")
    op.drop_table("declarations")
