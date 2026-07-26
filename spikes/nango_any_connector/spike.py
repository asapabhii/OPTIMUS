"""Phase 0 spike: Nango any-connector pattern.

Verify that the generic connector pattern works for dynamically
connecting to 5+ different integration types without provider-specific
code changes.

Success criteria:
1. Can list available integrations from Nango catalog
2. Can initiate OAuth for at least 5 different provider types
3. Can proxy a basic read through each connected provider
4. The generic NangoConnector handles all of them
"""

from __future__ import annotations

import asyncio
import httpx

from libs.config.settings import get_settings

# Target integrations for the spike
TARGET_INTEGRATIONS = [
    "hubspot",
    "google-drive",
    "google-sheets",
    "gmail",
    "slack",
    "notion",
    "jira",
]


async def run_spike() -> None:
    """Verify the any-connector pattern with Nango."""
    settings = get_settings()

    async with httpx.AsyncClient() as client:
        # Step 1: List available integrations
        response = await client.get(
            f"{settings.nango_base_url}/config",
            headers={"Authorization": f"Bearer {settings.nango_secret_key.get_secret_value()}"},
        )
        print(f"Available integrations: {response.status_code}")
        if response.status_code == 200:
            configs = response.json().get("configs", [])
            available = [c["unique_key"] for c in configs]
            print(f"  Found {len(available)} integrations")

            # Step 2: Check which target integrations are available
            for target in TARGET_INTEGRATIONS:
                status = "AVAILABLE" if target in available else "NOT CONFIGURED"
                print(f"  {target}: {status}")

        # Step 3: For each configured integration, verify proxy capability
        # TODO: Create test connections and verify proxy reads


if __name__ == "__main__":
    asyncio.run(run_spike())
