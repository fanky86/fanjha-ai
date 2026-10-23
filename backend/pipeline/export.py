from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Callable


def export_model(
    build_dir: Path,
    ckpt_dir: Path,
    tokenizer_dir: Path,
    emit_log: Callable[..., None],
) -> Path:
    export_dir = build_dir / "FANJHA_MODEL_FINAL"
    if export_dir.exists():
        shutil.rmtree(export_dir)
    export_dir.mkdir(parents=True)

    # Copy model files
    for f in ckpt_dir.iterdir():
        if f.is_file():
            shutil.copy2(f, export_dir / f.name)

    # Copy tokenizer
    for f in tokenizer_dir.iterdir():
        if f.is_file() and not (export_dir / f.name).exists():
            shutil.copy2(f, export_dir / f.name)

    # Metadata
    meta = {
        "build_id": build_dir.name,
        "artifact": "FANJHA_MODEL_FINAL",
        "files": sorted(p.name for p in export_dir.iterdir() if p.is_file()),
    }
    (export_dir / "model_metadata.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )

    emit_log("export", f"Exported model to {export_dir.name}")
    return export_dir
