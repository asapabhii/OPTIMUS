"""Specialized Google Sheets connector — the differentiator.

Google Sheets is unique because:
1. Cells are live-state data (the renewal date in cell B12)
2. Sheet structure (headers, column types) needs semantic inference (G2)
3. It's the primary SoR for many RevOps teams — the wedge pain
4. The no_live_values constraint applies to every cell value

Inherits from NangoConnector, adds sheet-specific logic.
"""

from __future__ import annotations

from connectors.nango_connector import NangoConnector
from connectors.base import IngestedItem, LiveReadResult
from core.enums import SourceClass, VolatilityClass
from libs.adapters.credentials import CredentialAdapter, ProxyRequest
from libs.observability.logging import get_logger
from libs.resilience.timeout import with_timeout

logger = get_logger("connector.google_sheets")


class GoogleSheetsConnector(NangoConnector):
    """Specialized connector for Google Sheets.

    Adds:
    - Sheet-level ingestion (spreadsheet → sheets → cells)
    - Cell-level live reads (for live-state values)
    - Header inference for entity key detection (G2)
    """

    provider_type: str = "google_sheets"
    default_source_class: SourceClass = SourceClass.AUTHORITY
    default_volatility: VolatilityClass = VolatilityClass.LIVE_STATE

    def __init__(self, credential_adapter: CredentialAdapter, **kwargs: object) -> None:
        super().__init__(credential_adapter, provider_type="google_sheets")

    async def ingest_fast_path(
        self, connection_id: str, limit: int = 20
    ) -> list[IngestedItem]:
        """Fast-path: fetch recent spreadsheets and their first sheets.

        For onboarding, we ingest the first N spreadsheets and extract:
        - Sheet structure (headers, column types)
        - First 100 rows per sheet
        - Entity key column detection

        TODO: Wire to Google Sheets API via Nango proxy.
        """
        logger.info(
            "sheets_fast_path",
            connection_id=connection_id,
            limit=limit,
        )
        # TODO: Implement via Nango proxy:
        # 1. List spreadsheets (sorted by lastModifiedTime)
        # 2. For each (up to limit): get sheet metadata + first 100 rows
        # 3. Run header inference (G2)
        return await super().ingest_fast_path(connection_id, limit)

    @with_timeout("live_read")
    async def live_read_cell(
        self, connection_id: str, spreadsheet_id: str, range_notation: str
    ) -> LiveReadResult:
        """Live-read a specific cell or range.

        This is the core of the wedge pain: the renewal date in B12
        is a live value that must NEVER be cached (no_live_values).
        """
        from datetime import datetime, timezone

        try:
            response = await self.credential_adapter.proxy_request(
                connection_id=connection_id,
                request=ProxyRequest(
                    method="GET",
                    endpoint=f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{range_notation}",
                ),
            )

            return LiveReadResult(
                source_ref=f"{spreadsheet_id}!{range_notation}",
                value=response.data,
                fetched_at=datetime.now(timezone.utc).isoformat(),
                is_accessible=response.status_code == 200,
            )
        except Exception as e:
            return LiveReadResult(
                source_ref=f"{spreadsheet_id}!{range_notation}",
                value=None,
                fetched_at=datetime.now(timezone.utc).isoformat(),
                is_accessible=False,
                error=str(e),
            )
