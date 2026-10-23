from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_rate_limit(client):
    for _ in range(5):
        r = await client.post("/api/builds", json={})
        assert r.status_code == 200


@pytest.mark.asyncio
async def test_csrf_endpoint(client):
    r = await client.get("/api/system/csrf")
    assert r.status_code == 200
    assert "token" in r.json()


@pytest.mark.asyncio
async def test_settings_update(client, csrf_headers):
    r = await client.post(
        "/api/system/settings",
        json={"default_max_train_steps": 5},
        headers=csrf_headers,
    )
    assert r.status_code == 200
    r = await client.get("/api/system/settings")
    assert r.json()["default_max_train_steps"] == 5
