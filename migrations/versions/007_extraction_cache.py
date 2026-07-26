"""007: Content-hash extraction cache.

Viewer-INDEPENDENT cache for parsed/extracted document content.
The content hash is the key — same document yields same extraction
regardless of who triggered it. Avoids duplicate LLM costs.

Revision ID: 007
Revises: 006
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "extraction_cache",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("content_hash", sa.String(64), nullable=False, unique=True, index=True),
        sa.Column("source_ref", sa.String(500), nullable=False),
        sa.Column("document_type", sa.String(100), nullable=False),
        sa.Column("extracted_entities", JSONB, server_default=sa.text("'[]'::jsonb")),
        sa.Column("extracted_facts", JSONB, server_default=sa.text("'[]'::jsonb")),
        sa.Column("parsed_units", JSONB, server_default=sa.text("'[]'::jsonb")),
        sa.Column("extraction_model", sa.String(100), server_default=""),
        sa.Column("extraction_cost_usd", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    # NOTE: No RLS — this cache is viewer-independent by design.
    # The content hash makes it safe: same document = same extraction.


def downgrade() -> None:
    op.drop_table("extraction_cache")
