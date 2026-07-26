"""Specialized Gmail connector.

Gmail is ALWAYS evidence, never authority (P7, REQ-3.2).
An email saying "maybe change the pricing" must be structurally
incapable of conflicting with canonical pricing.

Adds email-specific parsing: subject, sender, recipients, thread grouping.
"""

from __future__ import annotations

from connectors.nango_connector import NangoConnector
from connectors.base import IngestedItem
from core.enums import SourceClass, VolatilityClass
from libs.adapters.credentials import CredentialAdapter
from libs.observability.logging import get_logger

logger = get_logger("connector.gmail")


class GmailConnector(NangoConnector):
    """Specialized connector for Gmail.

    Gmail is evidence — append-only, never authority.
    Emails inform but never assert.
    """

    provider_type: str = "gmail"
    default_source_class: SourceClass = SourceClass.EVIDENCE
    default_volatility: VolatilityClass = VolatilityClass.APPEND_ONLY

    def __init__(self, credential_adapter: CredentialAdapter, **kwargs: object) -> None:
        super().__init__(credential_adapter, provider_type="gmail")

    async def ingest_fast_path(
        self, connection_id: str, limit: int = 50
    ) -> list[IngestedItem]:
        """Fast-path: fetch most recent emails.

        Groups by thread for context preservation.
        Extracts: subject, sender, recipients, date, body preview.

        TODO: Wire to Gmail API via Nango proxy.
        """
        logger.info(
            "gmail_fast_path",
            connection_id=connection_id,
            limit=limit,
        )
        # TODO: Implement via Nango proxy:
        # 1. GET /gmail/v1/users/me/messages?maxResults={limit}
        # 2. For each: GET /gmail/v1/users/me/messages/{id}
        # 3. Extract thread grouping and metadata
        return await super().ingest_fast_path(connection_id, limit)
