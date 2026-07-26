"""Parser adapter — abstract interface for document parsing.

Commercial: LlamaCloud (LlamaParse + LlamaExtract)
OSS fallback: Unstructured Platform (degraded, honestly labeled)

Decomposes documents into addressable structural units —
pages, tables, sheet ranges — which is precisely the sub-source
region model the policy engine classifies over.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ParsedUnit:
    """An addressable structural unit from a parsed document."""

    unit_id: str
    unit_type: str  # page, table, sheet_range, paragraph, heading
    content: str
    metadata: dict[str, str] = field(default_factory=dict)
    page_number: int | None = None
    table_data: list[list[str]] | None = None


@dataclass
class ParseResult:
    """Result of parsing a document."""

    source_ref: str
    content_hash: str
    units: list[ParsedUnit]
    document_type: str  # pdf, spreadsheet, presentation, document
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class SheetSemantics:
    """Extracted sheet semantics (G2) — header inference, column typing, entity keys.

    This is the hardest unpriced engineering item. LlamaExtract schemas
    absorb most of it (the reason LlamaCloud was chosen over Unstructured).
    """

    header_row: int
    columns: list[dict[str, str]]  # name, semantic_type, is_entity_key
    entity_key_column: str | None = None
    fact_type_columns: list[str] = field(default_factory=list)


class ParserAdapter(ABC):
    """Abstract document parser."""

    @abstractmethod
    async def parse_document(self, content: bytes, filename: str) -> ParseResult:
        """Parse a document into addressable structural units."""

    @abstractmethod
    async def extract_sheet_semantics(
        self, content: bytes, filename: str
    ) -> SheetSemantics:
        """Extract sheet semantics — the G2 spike."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Liveness check."""
