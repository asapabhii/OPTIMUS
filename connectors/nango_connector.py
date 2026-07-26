"""Generic Nango-backed connector — works with ANY Nango integration.

This is the default connector for all sources. It delegates OAuth,
token lifecycle, and API proxying to Nango Cloud. Specialized
connectors (Google Sheets, HubSpot) inherit from this and add
source-specific logic.

The key invariant: every API call uses the VIEWER'S OWN token
via Nango's authenticated proxy. Never a service account.
"""

from __future__ import annotations

from datetime import datetime, timezone

from connectors.base import (
    ConnectorInterface,
    IngestedItem,
    LiveReadResult,
    PermissionPingResult,
)
from core.enums import SourceClass, VolatilityClass
from libs.adapters.credentials import CredentialAdapter, ProxyRequest
from libs.observability.logging import get_logger
from libs.resilience.circuit_breaker import vendor_circuit_breaker
from libs.resilience.rate_limiter import rate_limiter
from libs.resilience.timeout import with_timeout

logger = get_logger("nango_connector")


class NangoConnector(ConnectorInterface):
    """Generic connector for any Nango-supported integration.

    Works out of the box for basic ingestion and permission pinging.
    Specialized connectors override specific methods for richer behavior.
    """

    provider_type: str = "generic"
    default_source_class: SourceClass = SourceClass.EVIDENCE
    default_volatility: VolatilityClass = VolatilityClass.APPEND_ONLY

    def __init__(
        self,
        credential_adapter: CredentialAdapter,
        provider_type: str = "generic",
    ) -> None:
        self.credential_adapter = credential_adapter
        self.provider_type = provider_type

    @with_timeout("live_read")
    @vendor_circuit_breaker("nango")
    async def ingest_fast_path(
        self, connection_id: str, limit: int = 50
    ) -> list[IngestedItem]:
        """Fast-path: fetch the most recent N items via Nango proxy.

        The specific endpoint depends on the provider type.
        Override in specialized connectors for richer extraction.
        """
        await rate_limiter.acquire(self.provider_type)

        response = await self.credential_adapter.proxy_request(
            connection_id=connection_id,
            request=ProxyRequest(
                method="GET",
                endpoint="/records",
                params={"limit": limit, "sort": "-updated_at"},
            ),
        )

        items: list[IngestedItem] = []
        if response.status_code == 200 and isinstance(response.data, list):
            for record in response.data[:limit]:
                items.append(
                    IngestedItem(
                        source_ref=str(record.get("id", "")),
                        content=str(record),
                        item_type=self.provider_type,
                        metadata=record if isinstance(record, dict) else {},
                    )
                )

        logger.info(
            "fast_path_ingested",
            provider=self.provider_type,
            count=len(items),
            limit=limit,
        )
        return items

    async def ingest_full(
        self, connection_id: str, depth_days: int = 365
    ) -> list[IngestedItem]:
        """Full ingestion — paginate through all records within depth.

        For production, this is handled by Airbyte Cloud (Plane A batch).
        This method exists for direct testing and spike work.
        """
        # In production, Airbyte handles this. This is for testing.
        return await self.ingest_fast_path(connection_id, limit=1000)

    @with_timeout("live_read")
    @vendor_circuit_breaker("nango")
    async def live_read(
        self, connection_id: str, source_ref: str
    ) -> LiveReadResult:
        """Live read: fetch current value using the viewer's own token."""
        await rate_limiter.acquire(self.provider_type)

        try:
            response = await self.credential_adapter.proxy_request(
                connection_id=connection_id,
                request=ProxyRequest(
                    method="GET",
                    endpoint=f"/records/{source_ref}",
                ),
            )

            return LiveReadResult(
                source_ref=source_ref,
                value=response.data,
                fetched_at=datetime.now(timezone.utc).isoformat(),
                is_accessible=response.status_code == 200,
                error=None if response.status_code == 200 else f"HTTP {response.status_code}",
            )
        except Exception as e:
            return LiveReadResult(
                source_ref=source_ref,
                value=None,
                fetched_at=datetime.now(timezone.utc).isoformat(),
                is_accessible=False,
                error=str(e),
            )

    @with_timeout("permission_ping")
    @vendor_circuit_breaker("nango")
    async def permission_ping(
        self, connection_id: str, source_ref: str
    ) -> PermissionPingResult:
        """Permission ping: verify the viewer can still see this item.

        Uses the viewer's own Nango-managed token.
        A failed ping means the claim is OMITTED from the answer —
        never mirror-fallback (Gate 4 test (e)).
        """
        await rate_limiter.acquire(self.provider_type)

        try:
            response = await self.credential_adapter.proxy_request(
                connection_id=connection_id,
                request=ProxyRequest(
                    method="HEAD",
                    endpoint=f"/records/{source_ref}",
                ),
            )

            return PermissionPingResult(
                source_ref=source_ref,
                is_accessible=response.status_code in (200, 204),
                checked_at=datetime.now(timezone.utc).isoformat(),
            )
        except Exception:
            return PermissionPingResult(
                source_ref=source_ref,
                is_accessible=False,
                checked_at=datetime.now(timezone.utc).isoformat(),
            )
