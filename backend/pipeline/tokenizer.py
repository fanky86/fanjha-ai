from __future__ import annotations

from pathlib import Path
from typing import Callable


def train_or_load(
    processed_path: Path,
    build_dir: Path,
    model_name: str,
    emit_log: Callable[..., None],
) -> Path:
    from transformers import AutoTokenizer

    tokenizer_dir = build_dir / "tokenizer"
    tokenizer_dir.mkdir(parents=True, exist_ok=True)

    emit_log("tokenizer", f"Loading tokenizer from {model_name}")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    tokenizer.save_pretrained(tokenizer_dir)
    emit_log(
        "tokenizer",
        f"Tokenizer saved (vocab size: {tokenizer.vocab_size})",
    )
    return tokenizer_dir
