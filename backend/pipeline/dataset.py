from __future__ import annotations

import json
from pathlib import Path
from typing import Callable


def discover(data_dir: Path, emit_log: Callable[..., None]) -> list[Path]:
    data_dir.mkdir(parents=True, exist_ok=True)
    patterns = ["*.jsonl", "*.json", "*.txt", "*.parquet", "*.csv"]
    files: list[Path] = []
    for pat in patterns:
        files.extend(sorted(data_dir.rglob(pat)))

    if not files:
        emit_log(
            "dataset",
            "No datasets found — generating synthetic sample",
            "WARNING",
        )
        sample = _generate_synthetic(data_dir)
        files = [sample]

    for f in files:
        emit_log(
            "dataset",
            f"Discovered: {f.relative_to(data_dir)} ({f.stat().st_size / 1024:.1f} KB)",
        )

    return files


def _generate_synthetic(data_dir: Path) -> Path:
    out = data_dir / "synthetic" / "sample.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.is_file() and out.stat().st_size > 0:
        return out
    topics = [
        "Artificial intelligence enables machines to learn patterns from data",
        "Machine learning models require high quality training data",
        "Neural networks consist of layers of interconnected nodes",
        "Training large language models requires significant compute",
        "The transformer architecture revolutionized natural language processing",
        "Attention mechanisms allow models to focus on relevant information",
        "Gradient descent optimizes model parameters iteratively",
        "Regularization helps prevent overfitting on training data",
    ]
    with out.open("w", encoding="utf-8") as f:
        for i in range(200):
            text = f"{topics[i % len(topics)]} (sample {i})."
            f.write(json.dumps({"text": text}) + "\n")
    return out
