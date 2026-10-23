from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import Build, LogEntry, Metric, Artifact
from backend.orchestrator import orchestrator
from backend.schemas import (
    BuildCreateRequest,
    BuildOut,
    BuildSummary,
    LogsPage,
    MetricOut,
    ArtifactOut,
)
from backend.security import build_rate_limit, require_csrf

router = APIRouter(prefix="/api/builds", tags=["builds"])


@router.post("", dependencies=[Depends(build_rate_limit)])
async def create_build(
    payload: BuildCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    overrides = payload.model_dump(exclude_none=True)
    cfg = overrides.pop("config", None) or {}
    cfg.update(overrides)
    build = await orchestrator.create_build(cfg)
    return {"build_id": build.id, "status": build.status}


@router.get("", response_model=list[BuildSummary])
async def list_builds(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Build).order_by(desc(Build.id)).limit(limit)
    )
    return result.scalars().all()


@router.get("/{build_id}", response_model=BuildOut)
async def get_build(build_id: str, db: AsyncSession = Depends(get_db)):
    build = await db.get(Build, build_id)
    if build is None:
        raise HTTPException(404, "Build not found")
    return build


@router.post("/{build_id}/start", dependencies=[Depends(require_csrf)])
async def start_build(build_id: str):
    try:
        await orchestrator.start_build(build_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    except RuntimeError as exc:
        raise HTTPException(400, str(exc))
    return {"ok": True}


@router.post("/{build_id}/cancel", dependencies=[Depends(require_csrf)])
async def cancel_build(build_id: str):
    ok = await orchestrator.cancel_build(build_id)
    if not ok:
        raise HTTPException(400, "Build is not running")
    return {"ok": True}


@router.post("/{build_id}/resume", dependencies=[Depends(require_csrf)])
async def resume_build(build_id: str):
    try:
        await orchestrator.resume_build(build_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    except RuntimeError as exc:
        raise HTTPException(400, str(exc))
    return {"ok": True}


@router.post("/{build_id}/retry", dependencies=[Depends(require_csrf)])
async def retry_build(build_id: str):
    try:
        await orchestrator.retry_build(build_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    except RuntimeError as exc:
        raise HTTPException(400, str(exc))
    return {"ok": True}


@router.get("/{build_id}/logs", response_model=LogsPage)
async def get_logs(
    build_id: str,
    cursor: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=1000),
    severity: str | None = None,
    component: str | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(LogEntry).where(LogEntry.build_id == build_id)
    if severity:
        q = q.where(LogEntry.severity == severity.upper())
    if component:
        q = q.where(LogEntry.component == component)
    if search:
        q = q.where(LogEntry.message.ilike(f"%{search}%"))
    q = q.order_by(LogEntry.id).offset(cursor).limit(limit)
    result = await db.execute(q)
    logs = result.scalars().all()

    total_q = select(func.count(LogEntry.id)).where(LogEntry.build_id == build_id)
    total = (await db.execute(total_q)).scalar() or 0

    return {"logs": logs, "next_cursor": cursor + len(logs), "total": total}


@router.get("/{build_id}/metrics", response_model=list[MetricOut])
async def get_metrics(
    build_id: str,
    limit: int = Query(1000, ge=1, le=10000),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Metric)
        .where(Metric.build_id == build_id)
        .order_by(Metric.id)
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/{build_id}/artifacts", response_model=list[ArtifactOut])
async def get_artifacts(build_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Artifact)
        .where(Artifact.build_id == build_id)
        .order_by(Artifact.created_at)
    )
    return result.scalars().all()
