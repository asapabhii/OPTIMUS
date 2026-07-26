"""Phase 0 spike: Nango credential custody test.

THE TEST: Connect via Nango → revoke at source → verify next
delegated fetch fails with no cached authorization.

This is a vendor disqualification test. If Nango fails it,
we evaluate Arcade Enterprise or build custom OAuth custody.

Success criteria:
1. Connect succeeds and produces a valid connection_id
2. A proxied fetch succeeds with the viewer's token
3. After revoke at the source, the NEXT proxied fetch FAILS
4. Nango does NOT use cached credentials after revocation
"""

from __future__ import annotations

import asyncio
import httpx

from libs.config.settings import get_settings


async def run_spike() -> None:
    """Run the Nango custody verification spike."""
    settings = get_settings()

    async with httpx.AsyncClient() as client:
        # Step 1: Verify Nango is reachable
        health = await client.get(
            f"{settings.nango_base_url}/health",
            headers={"Authorization": f"Bearer {settings.nango_secret_key.get_secret_value()}"},
        )
        print(f"Nango health: {health.status_code}")

        # Step 2: Create a test connection
        # TODO: Create connection via Nango API
        # Step 3: Verify proxied fetch works
        # Step 4: Revoke at the source (manual step)
        # Step 5: Verify next proxied fetch FAILS
        # Step 6: Report pass/fail


if __name__ == "__main__":
    asyncio.run(run_spike())
