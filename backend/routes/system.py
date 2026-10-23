from __future__ import annotations

import os
import shutil

import psutil
from fastapi import APIRouter

from backend.schemas import SystemResourcesOut, SettingsPayload
from backend.security import get_csrf_token
from backend.config import settings as app_settings

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/csrf")
async def csrf():
    return {"token": get_csrf_token()}


@router.get("/resources", response_model=SystemResourcesOut)
async def resources():
    vm = psutil.virtual_memory()
    disk = shutil.disk_usage("/")
    proc_ram: int | None = None
    try:
        proc = psutil.Process(os.getpid())
        proc_ram = proc.memory_info().rss
    except Exception:
        pass

    gpu: dict | str = "unavailable"
    try:
        import torch

        if torch.cuda.is_available():
            gpu = {
                "name": torch.cuda.get_device_name(0),
                "vram_total": torch.cuda.get_device_properties(0).total_memory,
                "vram_allocated": torch.cuda.memory_allocated(0),
            }
    except Exception:
        pass

    return {
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "cpu_count": os.cpu_count() or 1,
        "ram_used": vm.used,
        "ram_available": vm.available,
        "ram_total": vm.total,
        "disk_used": disk.used,
        "disk_free": disk.free,
        "disk_total": disk.total,
        "process_ram_used": proc_ram,
        "gpu": gpu,
    }


@router.get("/settings")
async def get_settings():
    return {
        "default_model_name": app_settings.default_model_name,
        "default_max_train_steps": app_settings.default_max_train_steps,
        "default_batch_size": app_settings.default_batch_size,
        "default_learning_rate": app_settings.default_learning_rate,
        "default_max_seq_length": app_settings.default_max_seq_length,
    }


@router.post("/settings")
async def update_settings(payload: SettingsPayload):
    updates = payload.model_dump(exclude_none=True)
    for k, v in updates.items():
        setattr(app_settings, k, v)
    app_settings.save_runtime_overrides(updates)
    return {"ok": True, "updated": updates}
