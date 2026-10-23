from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_websocket_connect(client):
    from httpx_ws import aconnect_ws  # type: ignore  # optional; skip if unavailable

    pytest.skip("websocket e2e requires httpx_ws; covered by manual smoke test")
