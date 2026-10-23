from __future__ import annotations

import asyncio

import pytest


@pytest.mark.asyncio
async def test_create_and_get_build(client):
    r = await client.post("/api/builds", json={})
    assert r.status_code == 200
    data = r.json()
    build_id = data["build_id"]

    r = await client.get(f"/api/builds/{build_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "IDLE"
    assert body["id"] == build_id


@pytest.mark.asyncio
async def test_list_builds(client):
    await client.post("/api/builds", json={})
    r = await client.get("/api/builds")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_start_requires_csrf(client):
    r = await client.post("/api/builds", json={})
    build_id = r.json()["build_id"]
    r = await client.post(f"/api/builds/{build_id}/start")
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_start_with_csrf(client, csrf_headers):
    r = await client.post("/api/builds", json={})
    build_id = r.json()["build_id"]
    r = await client.post(f"/api/builds/{build_id}/start", headers=csrf_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True


@pytest.mark.asyncio
async def test_logs_pagination(client):
    r = await client.post("/api/builds", json={})
    build_id = r.json()["build_id"]
    r = await client.get(f"/api/builds/{build_id}/logs?cursor=0&limit=10")
    assert r.status_code == 200
    body = r.json()
    assert "logs" in body
    assert "next_cursor" in body
