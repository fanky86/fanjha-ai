from __future__ import annotations

import asyncio
import json
import os
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.config import settings
from backend.database import async_session_factory
from backend.logging_config import get_logger
from backend.models import Build, LogEntry, Metric, Artifact, StageEvent, utcnow
from backend.websocket_manager import manager

logger = get_logger("orchestrator")


class BuildOrchestrator:
    """Owns build lifecycle and worker subprocess management."""

    def __init__(self) -> None:
        self._processes: dict[str, asyncio.subprocess.Process] = {}
        self._tasks: dict[str, asyncio.Task] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()

    # ------------------------------------------------------------------ create

    async def create_build(self, overrides: dict[str, Any] | None = None) -> Build:
        cfg = {
            "model_name": settings.default_model_name,
            "max_train_steps": settings.default_max_train_steps,
            "batch_size": settings.default_batch_size,
            "learning_rate": settings.default_learning_rate,
            "max_seq_length": settings.default_max_seq_length,
            "eval_steps": settings.default_eval_steps,
            "save_steps": settings.default_save_steps,
        }
        if overrides:
            for k, v in overrides.items():
                if v is not None:
                    cfg[k] = v

        async with async_session_factory() as db:
            build = Build(status="IDLE", config=cfg)
            db.add(build)
            await db.commit()
            await db.refresh(build)
            logger.info(
                "Build created",
                extra={"build_id": build.id, "component": "orchestrator"},
            )
            return build

    # ----------------------------------------------------------------- start

    async def start_build(self, build_id: str) -> None:
        async with self._get_lock(build_id):
            async with async_session_factory() as db:
                build = await db.get(Build, build_id)
                if build is None:
                    raise ValueError("Build not found")
                if build.status in ("PREPARING", "TRAINING", "EVALUATING", "EXPORTING", "VERIFYING"):
                    raise RuntimeError(f"Build already running in status {build.status}")
                if build.status == "SUCCESS":
                    raise RuntimeError("Build already succeeded")
                build.status = "PREPARING"
                build.started_at = utcnow()
                build.finished_at = None
                build.duration_seconds = None
                build.error_summary = None
                await db.commit()

            await self._emit_status(build_id, "PREPARING")
            task = asyncio.create_task(self._run_pipeline(build_id, resume=False))
            self._tasks[build_id] = task
            task.add_done_callback(lambda _t: self._tasks.pop(build_id, None))

    async def resume_build(self, build_id: str) -> None:
        async with self._get_lock(build_id):
            async with async_session_factory() as db:
                build = await db.get(Build, build_id)
                if build is None:
                    raise ValueError("Build not found")
                if build.status not in ("FAILED", "CANCELLED", "WARNING"):
                    raise RuntimeError(f"Build cannot be resumed from status {build.status}")

                # Verify checkpoint compatibility
                ckpt = build.checkpoint_path
                if ckpt:
                    ckpt_path = Path(ckpt)
                    if not ckpt_path.exists():
                        raise RuntimeError(f"Checkpoint missing: {ckpt}")
                build.status = "PREPARING"
                build.error_summary = None
                build.is_resumed = True
                await db.commit()

            await self._emit_status(build_id, "PREPARING")
            task = asyncio.create_task(self._run_pipeline(build_id, resume=True))
            self._tasks[build_id] = task
            task.add_done_callback(lambda _t: self._tasks.pop(build_id, None))

    async def retry_build(self, build_id: str) -> None:
        """Retry from last checkpoint if present, otherwise full restart."""
        await self.resume_build(build_id)

    # ------------------------------------------------------------------ run

    async def _run_pipeline(self, build_id: str, resume: bool) -> None:
        async with async_session_factory() as db:
            build = await db.get(Build, build_id)
            if build is None:
                return
            cfg = build.config or {}
            ckpt = build.checkpoint_path if resume else None

        build_output_dir = settings.artifacts_dir / build_id
        build_output_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            sys.executable,
            "-m",
            "backend.worker",
            "--build-id",
            build_id,
            "--artifacts-dir",
            str(settings.artifacts_dir),
            "--data-dir",
            str(settings.data_dir),
            "--model-name",
            str(cfg.get("model_name", settings.default_model_name)),
            "--max-steps",
            str(cfg.get("max_train_steps", settings.default_max_train_steps)),
            "--batch-size",
            str(cfg.get("batch_size", settings.default_batch_size)),
            "--learning-rate",
            str(cfg.get("learning_rate", settings.default_learning_rate)),
            "--max-seq-length",
            str(cfg.get("max_seq_length", settings.default_max_seq_length)),
            "--eval-steps",
            str(cfg.get("eval_steps", settings.default_eval_steps)),
            "--save-steps",
            str(cfg.get("save_steps", settings.default_save_steps)),
        ]
        if ckpt:
            cmd.extend(["--resume-from-checkpoint", str(ckpt)])

        env = {
            **os.environ,
            "PYTHONUNBUFFERED": "1",
            "TOKENIZERS_PARALLELISM": "false",
        }

        logger.info(
            f"Spawning worker: {' '.join(cmd)}",
            extra={"build_id": build_id, "component": "orchestrator"},
        )

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                preexec_fn=os.setsid if hasattr(os, "setsid") else None,
            )
        except Exception as exc:
            await self._mark_failed(build_id, f"Failed to spawn worker: {exc}")
            return

        self._processes[build_id] = process
        async with async_session_factory() as db:
            build = await db.get(Build, build_id)
            if build:
                build.worker_pid = process.pid
                await db.commit()

        stdout_task = asyncio.create_task(
            self._consume_stream(build_id, process.stdout, "stdout")
        )
        stderr_task = asyncio.create_task(
            self._consume_stream(build_id, process.stderr, "stderr")
        )

        try:
            returncode = await asyncio.wait_for(
                process.wait(),
                timeout=settings.build_timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.warning(
                "Build timed out, terminating worker",
                extra={"build_id": build_id, "component": "orchestrator"},
            )
            await self._kill_process(process)
            await self._mark_failed(build_id, "Build timed out")
            returncode = -1
        finally:
            await asyncio.gather(stdout_task, stderr_task, return_exceptions=True)
            self._processes.pop(build_id, None)

        async with async_session_factory() as db:
            build = await db.get(Build, build_id)
            if build is None:
                return
            build.finished_at = utcnow()
            if build.started_at:
                build.duration_seconds = (
                    build.finished_at - build.started_at
                ).total_seconds()

            if returncode == 0 and build.status not in ("FAILED", "CANCELLED"):
                build.status = "SUCCESS"
                build.overall_progress = 100.0
            elif returncode in (-signal.SIGTERM, -15, 143):
                build.status = "CANCELLED"
            else:
                build.status = "FAILED"
                if not build.error_summary:
                    build.error_summary = f"Worker exited with code {returncode}"
            await db.commit()

        await self._emit_status(build_id, build.status)

    # ------------------------------------------------------------- consume

    async def _consume_stream(
        self, build_id: str, stream: asyncio.StreamReader | None, source: str
    ) -> None:
        if stream is None:
            return
        while True:
            try:
                line = await stream.readline()
            except Exception:
                break
            if not line:
                break
            text = line.decode("utf-8", errors="replace").rstrip()
            if not text:
                continue
            try:
                event = json.loads(text)
                if not isinstance(event, dict):
                    raise ValueError("non-dict event")
            except Exception:
                event = {
                    "type": "log",
                    "severity": "INFO" if source == "stdout" else "ERROR",
                    "component": f"worker-{source}",
                    "message": text,
                }
            try:
                await self._handle_event(build_id, event)
            except Exception as exc:
                logger.error(
                    f"Failed to handle event: {exc}",
                    extra={"build_id": build_id, "component": "orchestrator"},
                )

    async def _handle_event(self, build_id: str, event: dict[str, Any]) -> None:
        etype = event.get("type", "log")

        if etype == "log":
            severity = str(event.get("severity", "INFO")).upper()
            async with async_session_factory() as db:
                entry = LogEntry(
                    build_id=build_id,
                    severity=severity,
                    component=str(event.get("component", "worker")),
                    message=str(event.get("message", "")),
                    stack_trace=event.get("stack_trace"),
                )
                db.add(entry)
                await db.commit()
            await manager.broadcast(
                build_id,
                {
                    "event": "log",
                    "build_id": build_id,
                    "severity": severity,
                    "component": event.get("component", "worker"),
                    "message": event.get("message", ""),
                    "stack_trace": event.get("stack_trace"),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

        elif etype == "metric":
            async with async_session_factory() as db:
                metric = Metric(
                    build_id=build_id,
                    epoch=event.get("epoch"),
                    global_step=event.get("global_step"),
                    train_loss=event.get("train_loss"),
                    val_loss=event.get("val_loss"),
                    perplexity=event.get("perplexity"),
                    learning_rate=event.get("learning_rate"),
                    throughput_tokens_per_sec=event.get("throughput_tokens_per_sec"),
                )
                db.add(metric)
                build = await db.get(Build, build_id)
                if build:
                    if event.get("overall_progress") is not None:
                        build.overall_progress = float(event["overall_progress"])
                    if event.get("global_step") is not None:
                        build.current_step = int(event["global_step"])
                    if event.get("epoch") is not None:
                        build.current_epoch = int(event["epoch"])
                await db.commit()
            await manager.broadcast(
                build_id,
                {
                    "event": "metric",
                    "build_id": build_id,
                    **{k: v for k, v in event.items() if k != "type"},
                },
            )

        elif etype == "status":
            stage = event.get("stage") or event.get("status")
            progress = float(event.get("overall_progress", 0.0))
            async with async_session_factory() as db:
                build = await db.get(Build, build_id)
                if build:
                    if stage:
                        build.status = str(stage)
                        build.active_stage = str(stage)
                    build.overall_progress = progress
                db.add(
                    StageEvent(
                        build_id=build_id,
                        stage=str(stage or ""),
                        status=str(event.get("status", "running")),
                        progress=progress,
                    )
                )
                await db.commit()
            await manager.broadcast(
                build_id,
                {
                    "event": "status",
                    "build_id": build_id,
                    "status": stage,
                    "stage": stage,
                    "overall_progress": progress,
                },
            )

        elif etype == "artifact":
            async with async_session_factory() as db:
                artifact = Artifact(
                    build_id=build_id,
                    name=str(event.get("name", "unknown")),
                    relative_path=str(event.get("relative_path", "")),
                    size_bytes=int(event.get("size_bytes", 0)),
                    sha256=str(event.get("sha256", "")),
                    verified=bool(event.get("verified", False)),
                    artifact_type=str(event.get("artifact_type", "file")),
                )
                db.add(artifact)
                await db.commit()
                await db.refresh(artifact)
            await manager.broadcast(
                build_id,
                {
                    "event": "artifact",
                    "build_id": build_id,
                    "artifact_id": artifact.id,
                    "name": artifact.name,
                    "size_bytes": artifact.size_bytes,
                    "sha256": artifact.sha256,
                    "verified": artifact.verified,
                },
            )

        elif etype == "checkpoint":
            path = event.get("path")
            if path:
                async with async_session_factory() as db:
                    build = await db.get(Build, build_id)
                    if build:
                        build.checkpoint_path = str(path)
                        await db.commit()

    # ---------------------------------------------------------------- cancel

    async def cancel_build(self, build_id: str) -> bool:
        process = self._processes.get(build_id)
        if process is None or process.returncode is not None:
            async with async_session_factory() as db:
                build = await db.get(Build, build_id)
                if build and build.status in ("IDLE", "PREPARING"):
                    build.status = "CANCELLED"
                    build.finished_at = utcnow()
                    await db.commit()
                    await self._emit_status(build_id, "CANCELLED")
                    return True
            return False

        try:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        except Exception:
            try:
                process.terminate()
            except Exception:
                pass

        try:
            await asyncio.wait_for(process.wait(), timeout=15)
        except asyncio.TimeoutError:
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            except Exception:
                process.kill()

        async with async_session_factory() as db:
            build = await db.get(Build, build_id)
            if build:
                build.status = "CANCELLED"
                build.finished_at = utcnow()
                await db.commit()
        await self._emit_status(build_id, "CANCELLED")
        return True

    # ---------------------------------------------------------------- helpers

    async def _kill_process(self, process: asyncio.subprocess.Process) -> None:
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        except Exception:
            try:
                process.terminate()
            except Exception:
                pass
        try:
            await asyncio.wait_for(process.wait(), timeout=10)
        except asyncio.TimeoutError:
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            except Exception:
                process.kill()

    async def _mark_failed(self, build_id: str, reason: str) -> None:
        async with async_session_factory() as db:
            build = await db.get(Build, build_id)
            if build:
                build.status = "FAILED"
                build.finished_at = utcnow()
                build.error_summary = reason
                await db.commit()
        await self._emit_status(build_id, "FAILED")
        await manager.broadcast(
            build_id,
            {
                "event": "log",
                "build_id": build_id,
                "severity": "ERROR",
                "component": "orchestrator",
                "message": reason,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    async def _emit_status(self, build_id: str, status: str) -> None:
        await manager.broadcast(
            build_id,
            {"event": "status", "build_id": build_id, "status": status},
        )

    def _get_lock(self, build_id: str) -> asyncio.Lock:
        if build_id not in self._locks:
            self._locks[build_id] = asyncio.Lock()
        return self._locks[build_id]

    def running_builds(self) -> list[str]:
        return [bid for bid, p in self._processes.items() if p.returncode is None]


orchestrator = BuildOrchestrator()
