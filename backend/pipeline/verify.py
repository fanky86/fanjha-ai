from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from typing import Callable


def sha256_file(path: Path, chunk: int = 1 << 16) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def verify_and_package(
    build_dir: Path,
    export_dir: Path,
    eval_report: dict,
    emit_log: Callable[..., None],
    emit_artifact: Callable[..., None],
) -> Path:
    if not export_dir.is_dir() or not any(export_dir.iterdir()):
        raise RuntimeError("Export directory is empty — cannot package")

    required = ["config.json"]
    for req in required:
        if not (export_dir / req).exists():
            emit_log(
                "verify",
                f"Missing {req} in export (non-fatal for smoke models)",
                "WARNING",
            )

    zip_path = build_dir / "FANJHA_MODEL_FINAL.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in export_dir.rglob("*"):
            if f.is_file():
                zf.write(f, f.relative_to(build_dir))
        # include eval report
        eval_path = build_dir / "evaluation_report.json"
        if eval_path.exists():
            zf.write(eval_path, "evaluation_report.json")

    checksum = sha256_file(zip_path)
    manifest = {
        "zip_sha256": checksum,
        "zip_size": zip_path.stat().st_size,
        "eval": eval_report,
    }
    (build_dir / "artifact_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    emit_log(
        "verify",
        f"ZIP created: {zip_path.name} ({zip_path.stat().st_size} bytes) sha256={checksum[:16]}…",
    )
    return zip_path


def list_artifacts(build_dir: Path) -> list[Path]:
    out: list[Path] = []
    for name in ("FANJHA_MODEL_FINAL.zip", "evaluation_report.json", "artifact_manifest.json"):
        p = build_dir / name
        if p.is_file():
            out.append(p)
    return out
