from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Callable


def preprocess(files: list[Path], build_dir: Path, emit_log: Callable[..., None]) -> Path:
    build_dir.mkdir(parents=True, exist_ok=True)
    out_path = build_dir / "processed.jsonl"
    count = 0
    skipped = 0

    with out_path.open("w", encoding="utf-8") as fout:
        for path in files:
            try:
                count += _process_file(path, fout)
            except Exception as exc:  # noqa: BLE001
                emit_log(
                    "preprocessing",
                    f"Failed to process {path.name}: {exc}",
                    "ERROR",
                )
                skipped += 1
                continue

    emit_log(
        "preprocessing",
        f"Wrote {count} documents ({skipped} skipped) to {out_path.name}",
    )
    if count == 0:
        raise RuntimeError("No documents produced by preprocessing")
    return out_path


def _process_file(path: Path, fout) -> int:  # noqa: ANN001
    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        return _process_jsonl(path, fout)
    if suffix == ".json":
        return _process_json(path, fout)
    if suffix == ".txt":
        return _process_txt(path, fout)
    if suffix == ".csv":
        return _process_csv(path, fout)
    if suffix == ".parquet":
        return _process_parquet(path, fout)
    return 0


def _process_jsonl(path: Path, fout) -> int:  # noqa: ANN001
    count = 0
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                text = line
            else:
                text = obj.get("text") or obj.get("content") or obj.get("document")
                if text is None:
                    continue
            if text and isinstance(text, str):
                fout.write(json.dumps({"text": text}) + "\n")
                count += 1
    return count


def _process_json(path: Path, fout) -> int:  # noqa: ANN001
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        count = 0
        for item in data:
            if isinstance(item, str):
                text = item
            elif isinstance(item, dict):
                text = item.get("text") or item.get("content")
            else:
                continue
            if text:
                fout.write(json.dumps({"text": str(text)}) + "\n")
                count += 1
        return count
    if isinstance(data, dict):
        text = data.get("text") or data.get("content")
        if text:
            fout.write(json.dumps({"text": str(text)}) + "\n")
            return 1
    return 0


def _process_txt(path: Path, fout) -> int:  # noqa: ANN001
    count = 0
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                fout.write(json.dumps({"text": line}) + "\n")
                count += 1
    return count


def _process_csv(path: Path, fout) -> int:  # noqa: ANN001
    count = 0
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = row.get("text") or row.get("content")
            if text:
                fout.write(json.dumps({"text": text}) + "\n")
                count += 1
    return count


def _process_parquet(path: Path, fout) -> int:  # noqa: ANN001
    try:
        import pyarrow.parquet as pq
    except ImportError:
        raise RuntimeError("pyarrow required for parquet datasets")
    count = 0
    table = pq.read_table(path)
    for col in ("text", "content"):
        if col in table.column_names:
            for value in table.column(col).to_pylist():
                if value:
                    fout.write(json.dumps({"text": value}) + "\n")
                    count += 1
            break
    return count
