from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.config import settings
from backend.database import init_db
from backend.logging_config import setup_logging, get_logger
from backend.routes import artifacts, builds, datasets, system
from backend.websocket_manager import manager

setup_logging()
logger = get_logger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info("FANJHA backend started", extra={"component": "api"})
    yield
    logger.info("FANJHA backend shutting down", extra={"component": "api"})


app = FastAPI(title="FANJHA AI Model Factory", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(builds.router)
app.include_router(system.router)
app.include_router(artifacts.router)
app.include_router(datasets.router)


@app.websocket("/api/builds/{build_id}/stream")
async def websocket_stream(websocket: WebSocket, build_id: str):
    await manager.connect(build_id, websocket)
    try:
        # initial snapshot
        from backend.database import async_session_factory
        from backend.models import Build

        async with async_session_factory() as db:
            build = await db.get(Build, build_id)
            if build:
                await websocket.send_json(
                    {
                        "event": "snapshot",
                        "build": {
                            "id": build.id,
                            "status": build.status,
                            "active_stage": build.active_stage,
                            "overall_progress": build.overall_progress,
                            "started_at": str(build.started_at) if build.started_at else None,
                        },
                    }
                )
        while True:
            msg = await websocket.receive_text()
            if msg == "ping":
                await websocket.send_text('{"event":"pong"}')
    except WebSocketDisconnect:
        pass
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"WS error: {exc}", extra={"build_id": build_id})
    finally:
        await manager.disconnect(build_id, websocket)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc: StarletteHTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


# Serve static frontend if built
FRONTEND_DIST = settings.frontend_dist
if FRONTEND_DIST.is_dir():
    assets = FRONTEND_DIST / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{full_path:path}")
    async def spa(full_path: str):
        # Don't shadow API routes
        if full_path.startswith("api/"):
            return JSONResponse(status_code=404, content={"detail": "Not found"})
        candidate = FRONTEND_DIST / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        index = FRONTEND_DIST / "index.html"
        if index.is_file():
            return FileResponse(index)
        return JSONResponse(status_code=404, content={"detail": "Frontend not built"})
