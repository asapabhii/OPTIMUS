"""Unit tests for the connector registry."""

from __future__ import annotations

from unittest.mock import MagicMock

from connectors.nango_connector import NangoConnector
from connectors.registry import get_connector, register_specialized, list_specialized


class TestConnectorRegistry:
    """Registry should support any Nango integration."""

    def test_unknown_provider_returns_generic(self) -> None:
        """Unknown providers get the generic NangoConnector."""
        mock_cred = MagicMock()
        connector = get_connector("some_new_saas_tool", mock_cred)
        assert isinstance(connector, NangoConnector)
        assert connector.provider_type == "some_new_saas_tool"

    def test_specialized_connector_registered(self) -> None:
        """Specialized connectors are returned when registered."""

        class SpecialConnector(NangoConnector):
            pass

        register_specialized("special_tool", SpecialConnector)
        assert "special_tool" in list_specialized()

    def test_any_provider_works(self) -> None:
        """Should work with any arbitrary provider type string."""
        mock_cred = MagicMock()
        for provider in ["notion", "asana", "monday", "linear", "intercom", "zendesk"]:
            connector = get_connector(provider, mock_cred)
            assert connector.provider_type == provider
