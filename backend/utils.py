from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable


def sha256_file(path: Path, chunk: int = 1 << 16) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def human_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024  # type: ignore[assignment]
    return f"{n:.1f} PB"


def safe_relative_to(path: Path, root: Path) -> Path:
    """Raise if path is not inside root."""
    resolved = path.resolve()
    root_resolved = root.resolve()
    try:
        resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise PermissionError(f"Path {resolved} escapes root {root_resolved}") from exc
    return resolved


def tail_file(path: Path, lines: int = 200) -> list[str]:
    if not path.is_file():
        return []
    with path.open("rb") as f:
        f.seek(0, os.SEEK_END)
        end = f.tell()
        size = min(end, 64 * 1024)
        f.seek(end - size)
        data = f.read().decode("utf-8", errors="replace")
    return data.splitlines()[-lines:]


def run_subprocess_sync(
    cmd: list[str],
    cwd: Path | None = None,
    timeout: int = 60,
) -> tuple[int, str, str]:
    """Run subprocess synchronously, capturing output. Never uses shell=True."""
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as exc:
        return -1, exc.stdout or "", (exc.stderr or "") + f"\n[timeout after {timeout}s]"


def python_executable() -> str:
    return sys.executable


def copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def iter_files(root: Path) -> Iterable[Path]:
    for entry in root.rglob("*"):
        if entry.is_file():
            yield entry
