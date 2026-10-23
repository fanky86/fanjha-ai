from __future__ import annotations

from pathlib import Path
from typing import Callable


def initialize(model_name: str, build_dir: Path, emit_log: Callable[..., None]) -> Path:
    from transformers import AutoModelForCausalLM

    model_dir = build_dir / "model_init"
    model_dir.mkdir(parents=True, exist_ok=True)

    emit_log("model", f"Loading model {model_name}")
    model = AutoModelForCausalLM.from_pretrained(model_name)
    total_params = sum(p.numel() for p in model.parameters())
    emit_log("model", f"Model loaded with {total_params:,} parameters")

    model.save_pretrained(model_dir)
    emit_log("model", f"Model saved to {model_dir}")
    return model_dir
