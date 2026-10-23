from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = {}
        self._lock = asyncio.Lock()
        self._heartbeat_task: asyncio.Task | None = None

    async def connect(self, build_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.setdefault(build_id, set()).add(websocket)
        self._ensure_heartbeat()

    async def disconnect(self, build_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            conns = self._connections.get(build_id)
            if conns:
                conns.discard(websocket)
                if not conns:
                    self._connections.pop(build_id, None)

    async def broadcast(self, build_id: str, event: dict[str, Any]) -> None:
        async with self._lock:
            conns = list(self._connections.get(build_id, set()))
        if not conns:
            return
        payload = json.dumps(event, default=str, ensure_ascii=False)
        dead: list[WebSocket] = []
        for ws in conns:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        if dead:
            async with self._lock:
                bucket = self._connections.get(build_id)
                if bucket is not None:
                    for ws in dead:
                        bucket.discard(ws)
                    if not bucket:
                        self._connections.pop(build_id, None)

    def _ensure_heartbeat(self) -> None:
        if self._heartbeat_task is None or self._heartbeat_task.done():
            try:
                self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            except RuntimeError:
                self._heartbeat_task = None

    async def _heartbeat_loop(self) -> None:
        while True:
            await asyncio.sleep(20)
            async with self._lock:
                if not self._connections:
                    return
                buckets = {bid: list(ws_set) for bid, ws_set in self._connections.items()}
            for build_id, sockets in buckets.items():
                payload = json.dumps({"event": "ping", "build_id": build_id})
                dead: list[WebSocket] = []
                for ws in sockets:
                    try:
                        await ws.send_text(payload)
                    except Exception:
                        dead.append(ws)
                if dead:
                    async with self._lock:
                        bucket = self._connections.get(build_id)
                        if bucket is not None:
                            for ws in dead:
                                bucket.discard(ws)
                            if not bucket:
                                self._connections.pop(build_id, None)

    def active_builds(self) -> list[str]:
        return list(self._connections.keys())


manager = ConnectionManager()
