from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_resume_requires_terminal_status(client, csrf_headers):
    r = await client.post("/api/builds", json={})
    build_id = r.json()["build_id"]
    r = await client.post(f"/api/builds/{build_id}/resume", headers=csrf_headers)
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_cancel_idle(client, csrf_headers):
    r = await client.post("/api/builds", json={})
    build_id = r.json()["build_id"]
    r = await client.post(f"/api/builds/{build_id}/cancel", headers=csrf_headers)
    assert r.status_code == 200
