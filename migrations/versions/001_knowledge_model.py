"""001: Core knowledge model — entities, sources, links, provenance.

Entity-centric model (P1). Sources attach to entities via links.
Freshness policy lives on the LINK, not the entity or source.
RLS via viewer_id on every table.
no_live_values CHECK constraint on source_entity_links (REQ-3.3c).

Revision ID: 001
Revises: None
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable UUID extension
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")

    # --- Entities ---
    op.create_table(
        "entities",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("canonical_name", sa.String(500), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("visibility_level", sa.String(50), nullable=False, server_default="readable"),
        sa.Column("merged_into", UUID(as_uuid=True), sa.ForeignKey("entities.id"), nullable=True),
        sa.Column("viewer_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_entities_viewer_type", "entities", ["viewer_id", "entity_type"])
    op.create_index("ix_entities_canonical_name", "entities", ["canonical_name"])

    # --- Sources ---
    op.create_table(
        "sources",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("nango_connection_id", sa.String(255), nullable=False),
        sa.Column("provider_type", sa.String(100), nullable=False),
        sa.Column("display_name", sa.String(255), server_default=""),
        sa.Column("source_class", sa.String(50), nullable=False, server_default="evidence"),
        sa.Column("viewer_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("connected_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
    )

    # --- Source-Entity Links (where freshness policy lives) ---
    op.create_table(
        "source_entity_links",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("entity_id", UUID(as_uuid=True), sa.ForeignKey("entities.id"), nullable=False),
        sa.Column("source_id", UUID(as_uuid=True), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("source_ref", sa.String(500), nullable=False),
        sa.Column("volatility_class", sa.String(50), nullable=False, server_default="append_only"),
        sa.Column("cost_of_staleness", sa.String(50), nullable=False, server_default="medium"),
        sa.Column("held_value", sa.Text(), nullable=True),
        sa.Column("is_stale", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("version_counter", sa.Integer(), server_default=sa.text("0")),
        sa.Column("last_fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("viewer_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # THE CONSTRAINT: live-state facts MUST NOT store values (REQ-3.3c)
    op.execute("""
        ALTER TABLE source_entity_links
        ADD CONSTRAINT no_live_values
        CHECK (
            CASE WHEN volatility_class = 'live_state'
                 THEN held_value IS NULL
                 ELSE true
            END
        )
    """)

    op.create_index("ix_sel_entity_source", "source_entity_links", ["entity_id", "source_id"])

    # --- Entity Links (relationships) ---
    op.create_table(
        "entity_links",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("source_entity_id", UUID(as_uuid=True), sa.ForeignKey("entities.id"), nullable=False),
        sa.Column("target_entity_id", UUID(as_uuid=True), sa.ForeignKey("entities.id"), nullable=False),
        sa.Column("relationship_type", sa.String(100), nullable=False),
        sa.Column("confidence", sa.Float(), server_default=sa.text("1.0")),
        sa.Column("visibility_level", sa.String(50), server_default="readable"),
        sa.Column("viewer_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- Provenance ---
    op.create_table(
        "provenance",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("provenance_type", sa.String(50), nullable=False),
        sa.Column("source_id", UUID(as_uuid=True), sa.ForeignKey("sources.id"), nullable=True),
        sa.Column("source_ref", sa.String(500), nullable=True),
        sa.Column("human_asserter_id", UUID(as_uuid=True), nullable=True),
        sa.Column("human_asserter_role", sa.String(200), nullable=True),
        sa.Column("asserted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("needs_reconfirmation", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- Enable RLS on all tables ---
    for table in ["entities", "sources", "source_entity_links", "entity_links", "provenance"]:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_table("provenance")
    op.drop_table("entity_links")
    op.drop_table("source_entity_links")
    op.drop_table("sources")
    op.drop_table("entities")
