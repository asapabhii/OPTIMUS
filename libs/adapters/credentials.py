"""Credential adapter — abstract interface for per-user OAuth + live proxy.

Commercial: Nango Cloud
OSS fallback: Nango hybrid (their runtime, our credential store) → self-hosted Nango

The model never sees credentials (PromptQL pattern).
Viewer's own token on every live read — never a service account.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ConnectionInfo:
    """Information about a user's connected source."""

    connection_id: str
    provider_type: str
    is_active: bool
    scopes: list[str]
    created_at: str


@dataclass
class ProxyRequest:
    """A proxied API request through the user's credentials."""

    method: str  # GET, POST, etc.
    endpoint: str
    params: dict[str, Any] | None = None
    body: dict[str, Any] | None = None
    headers: dict[str, str] | None = None


@dataclass
class ProxyResponse:
    """Response from a proxied API request."""

    status_code: int
    data: Any
    headers: dict[str, str]


class CredentialAdapter(ABC):
    """Abstract credential management.

    Implementations MUST:
    - Execute live reads with the VIEWER'S OWN token, never a service account
    - Support OAuth token lifecycle (grant, refresh, revoke)
    - Support scope introspection
    - Fail cleanly when access is revoked at the source
      (the custody spike tests exactly this — REQ-7.1)
    """

    @abstractmethod
    async def list_connections(self, viewer_id: str) -> list[ConnectionInfo]:
        """List all connections for a viewer."""

    @abstractmethod
    async def create_connection(
        self, viewer_id: str, provider_type: str, oauth_code: str | None = None
    ) -> ConnectionInfo:
        """Create a new connection for a viewer."""

    @abstractmethod
    async def delete_connection(self, connection_id: str) -> None:
        """Revoke and delete a connection."""

    @abstractmethod
    async def proxy_request(
        self, connection_id: str, request: ProxyRequest
    ) -> ProxyResponse:
        """Execute an API request using the viewer's credentials.

        This is the core of the live-read plane.
        The timeout + circuit breaker + trace span wrapper lives here.
        """

    @abstractmethod
    async def get_available_integrations(self) -> list[dict[str, Any]]:
        """List all available integrations from the provider catalog."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Liveness check."""
