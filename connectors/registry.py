"""Dynamic connector registry — supports ANY Nango integration.

Not limited to a fixed set. The registry can create a connector
for any provider type in Nango's catalog. Specialized connectors
are registered for providers that need source-specific logic.
"""

from __future__ import annotations

from connectors.base import ConnectorInterface
from connectors.nango_connector import NangoConnector
from libs.adapters.credentials import CredentialAdapter
from libs.observability.logging import get_logger

logger = get_logger("connector_registry")

# Registry of specialized connector classes
_SPECIALIZED_CONNECTORS: dict[str, type[ConnectorInterface]] = {}


def register_specialized(provider_type: str, connector_class: type[ConnectorInterface]) -> None:
    """Register a specialized connector for a provider type."""
    _SPECIALIZED_CONNECTORS[provider_type] = connector_class
    logger.info("specialized_connector_registered", provider=provider_type)


def get_connector(
    provider_type: str,
    credential_adapter: CredentialAdapter,
) -> ConnectorInterface:
    """Get a connector for a provider type.

    If a specialized connector exists, use it.
    Otherwise, fall back to the generic NangoConnector.
    """
    specialized = _SPECIALIZED_CONNECTORS.get(provider_type)
    if specialized:
        logger.debug("using_specialized_connector", provider=provider_type)
        return specialized(credential_adapter=credential_adapter, provider_type=provider_type)

    logger.debug("using_generic_connector", provider=provider_type)
    return NangoConnector(
        credential_adapter=credential_adapter,
        provider_type=provider_type,
    )


def list_specialized() -> list[str]:
    """List all provider types with specialized connectors."""
    return list(_SPECIALIZED_CONNECTORS.keys())
