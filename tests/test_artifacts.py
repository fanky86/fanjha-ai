from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from backend.config import settings


@pytest.mark.asyncio
async def test_artifact_download_rejects_missing(client):
    r = await client.get("/api/artifacts/nonexistent/download")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_safe_relative_blocks_traversal():
    from backend.utils import safe_relative_to

    with pytest.raises(PermissionError):
        safe_relative_to(settings.artifacts_dir / ".." / "etc" / "passwd", settings.artifacts_dir)


@pytest.mark.asyncio
async def test_download_verified_artifact(client, csrf_headers, tmp_path):
    from backend.database import async_session_factory
    from backend.models import Artifact, Build

    # Create build row
    async with async_session_factory() as db:
        build = Build(status="SUCCESS", config={})
        db.add(build)
        await db.commit()
        await db.refresh(build)
        build_id = build.id

    # Create real file
    target = settings.artifacts_dir / build_id / "test.bin"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"hello world")
    h = hashlib.sha256(b"hello world").hexdigest()

    async with async_session_factory() as db:
        art = Artifact(
            build_id=build_id,
            name="test.bin",
            relative_path=str(target.relative_to(settings.artifacts_dir)),
            size_bytes=11,
            sha256=h,
            verified=True,
            artifact_type="file",
        )
        db.add(art)
        await db.commit()
        await db.refresh(art)
        art_id = art.id

    r = await client.get(f"/api/artifacts/{art_id}/download")
    assert r.status_code == 200
    assert r.content == b"hello world"
