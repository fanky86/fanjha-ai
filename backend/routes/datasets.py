from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from backend.config import settings
from backend.schemas import DatasetInfo

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


def _count_lines(path: Path) -> int:
    try:
        with path.open("rb") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


@router.get("", response_model=list[DatasetInfo])
async def list_datasets():
    results: list[DatasetInfo] = []
    for pat in ("*.jsonl", "*.json", "*.txt", "*.csv", "*.parquet"):
        for f in settings.data_dir.rglob(pat):
            if not f.is_file():
                continue
            documents = _count_lines(f) if f.suffix in (".jsonl", ".txt") else None
            estimated_tokens = documents * 60 if documents else None
            results.append(
                DatasetInfo(
                    path=str(f.relative_to(settings.data_dir)),
                    size_bytes=f.stat().st_size,
                    documents=documents,
                    estimated_tokens=estimated_tokens,
                )
            )
    return sorted(results, key=lambda d: d.path)


@router.get("/preview")
async def preview(path: str, limit: int = 5):
    if limit < 1 or limit > 50:
        raise HTTPException(400, "limit must be between 1 and 50")
    target = (settings.data_dir / path).resolve()
    try:
        target.relative_to(settings.data_dir.resolve())
    except ValueError:
        raise HTTPException(403, "Path escapes data directory")

    if not target.is_file():
        raise HTTPException(404, "File not found")

    preview_lines: list[str] = []
    with target.open(encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f):
            if i >= limit:
                break
            try:
                obj = json.loads(line)
                preview_lines.append(str(obj.get("text", obj))[:500])
            except json.JSONDecodeError:
                preview_lines.append(line.strip()[:500])
    return {"path": path, "preview": preview_lines}
