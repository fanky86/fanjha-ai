from __future__ import annotations

import os
import platform
import shutil
import sys
from typing import Callable


def validate(emit_log: Callable[..., None]) -> None:
    emit_log("environment", f"Python: {sys.version.split()[0]}")
    emit_log("environment", f"Platform: {platform.platform()}")
    emit_log("environment", f"CPU count: {os.cpu_count()}")

    # Disk check
    total, used, free = shutil.disk_usage("/")
    emit_log(
        "environment",
        f"Disk free: {free / 1e9:.1f} GB / {total / 1e9:.1f} GB",
    )
    if free < 500 * 1024 * 1024:
        emit_log("environment", "Low disk space (<500MB free)", "WARNING")

    # Torch
    try:
        import torch  # noqa: F401

        emit_log("environment", f"torch {torch.__version__}")
        if torch.cuda.is_available():
            emit_log(
                "environment",
                f"CUDA available: {torch.cuda.get_device_name(0)}",
            )
        else:
            emit_log("environment", "CUDA not available, using CPU", "WARNING")
    except ImportError:
        emit_log("environment", "torch not installed", "ERROR")
        raise RuntimeError("torch is required")

    # Transformers
    try:
        import transformers

        emit_log("environment", f"transformers {transformers.__version__}")
    except ImportError:
        emit_log("environment", "transformers not installed", "ERROR")
        raise RuntimeError("transformers is required")

    # Datasets
    try:
        import datasets

        emit_log("environment", f"datasets {datasets.__version__}")
    except ImportError:
        emit_log("environment", "datasets not installed", "WARNING")
