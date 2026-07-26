"""Specialized HubSpot connector.

HubSpot is the primary CRM authority for RevOps teams.
Deals, contacts, and companies are authority sources.
Notes and activities are evidence.

Adds CRM-specific entity mapping and live-read for deal stage.
"""

from __future__ import annotations

from connectors.nango_connector import NangoConnector
from connectors.base import IngestedItem, LiveReadResult
from core.enums import SourceClass, VolatilityClass
from libs.adapters.credentials import CredentialAdapter, ProxyRequest
from libs.observability.logging import get_logger

logger = get_logger("connector.hubspot")

# HubSpot artifact → source class mapping
HUBSPOT_SOURCE_CLASSES = {
    "deal": SourceClass.AUTHORITY,
    "contact": SourceClass.AUTHORITY,
    "company": SourceClass.AUTHORITY,
    "note": SourceClass.EVIDENCE,
    "activity": SourceClass.EVIDENCE,
    "email": SourceClass.EVIDENCE,
    "task": SourceClass.EVIDENCE,
}


class HubSpotConnector(NangoConnector):
    """Specialized connector for HubSpot CRM.

    Adds:
    - Entity type mapping (deal → entity with type 'deal')
    - Source class per artifact type (P7)
    - Live read for deal stage (live-state, critical)
    """

    provider_type: str = "hubspot"
    default_source_class: SourceClass = SourceClass.AUTHORITY
    default_volatility: VolatilityClass = VolatilityClass.LIVE_STATE

    def __init__(self, credential_adapter: CredentialAdapter, **kwargs: object) -> None:
        super().__init__(credential_adapter, provider_type="hubspot")

    async def ingest_fast_path(
        self, connection_id: str, limit: int = 50
    ) -> list[IngestedItem]:
        """Fast-path: fetch recent deals, contacts, companies.

        Prioritizes deals (live-state, critical staleness) over
        contacts (slow-state) and companies (slow-state).

        TODO: Wire to HubSpot API via Nango proxy.
        """
        logger.info(
            "hubspot_fast_path",
            connection_id=connection_id,
            limit=limit,
        )
        # TODO: Implement via Nango proxy:
        # 1. GET /crm/v3/objects/deals?limit={limit}&sort=-hs_lastmodifieddate
        # 2. GET /crm/v3/objects/contacts?limit={limit}&sort=-hs_lastmodifieddate
        # 3. GET /crm/v3/objects/companies?limit={limit}&sort=-hs_lastmodifieddate
        return await super().ingest_fast_path(connection_id, limit)

    def get_source_class(self, artifact_type: str) -> SourceClass:
        """Get the source class for a HubSpot artifact type."""
        return HUBSPOT_SOURCE_CLASSES.get(artifact_type, SourceClass.EVIDENCE)
