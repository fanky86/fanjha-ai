from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import get_db
from backend.models import Artifact
from backend.utils import sha256_file, safe_relative_to

router = APIRouter(prefix="/api/artifacts", tags=["artifacts"])


@router.get("/{artifact_id}/download")
async def download_artifact(artifact_id: str, db: AsyncSession = Depends(get_db)):
    artifact = await db.get(Artifact, artifact_id)
    if artifact is None or not artifact.verified:
        raise HTTPException(404, "Artifact not found or not verified")

    try:
        resolved = safe_relative_to(settings.artifacts_dir / artifact.relative_path, settings.artifacts_dir)
    except PermissionError:
        raise HTTPException(403, "Path traversal blocked")

    if not resolved.is_file():
        raise HTTPException(404, "Artifact file missing on disk")

    # Verify checksum if recorded
    if artifact.sha256:
        actual = sha256_file(resolved)
        if actual != artifact.sha256:
            raise HTTPException(409, "Artifact checksum mismatch")

    return FileResponse(
        resolved,
        filename=artifact.name,
        media_type="application/octet-stream",
    )


@router.get("/{artifact_id}/info")
async def artifact_info(artifact_id: str, db: AsyncSession = Depends(get_db)):
    artifact = await db.get(Artifact, artifact_id)
    if artifact is None:
        raise HTTPException(404, "Artifact not found")
    return {
        "id": artifact.id,
        "name": artifact.name,
        "size_bytes": artifact.size_bytes,
        "sha256": artifact.sha256,
        "verified": artifact.verified,
    }
