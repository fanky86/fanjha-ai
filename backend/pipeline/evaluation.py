from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Callable


def evaluate(
    build_dir: Path,
    ckpt_dir: Path,
    tokenizer_dir: Path,
    processed_path: Path,
    emit_log: Callable[..., None],
) -> dict:
    import torch
    from datasets import load_dataset
    from transformers import AutoModelForCausalLM, AutoTokenizer

    if not ckpt_dir.exists():
        raise RuntimeError(f"Checkpoint missing: {ckpt_dir}")

    emit_log("evaluation", "Running validation pass")

    tokenizer = AutoTokenizer.from_pretrained(tokenizer_dir)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(ckpt_dir)
    model.eval()

    try:
        ds = load_dataset("json", data_files=str(processed_path), split="train")
        sample = ds.select(range(min(8, len(ds))))
        losses = []
        with torch.no_grad():
            for row in sample:
                enc = tokenizer(
                    row["text"],
                    return_tensors="pt",
                    truncation=True,
                    max_length=128,
                )
                input_ids = enc["input_ids"]
                if input_ids.size(1) < 2:
                    continue
                outputs = model(input_ids, labels=input_ids)
                losses.append(float(outputs.loss))
        eval_loss = sum(losses) / len(losses) if losses else None
        perplexity = math.exp(eval_loss) if eval_loss is not None and eval_loss < 20 else None
    except Exception as exc:  # noqa: BLE001
        emit_log("evaluation", f"Eval error: {exc}", "WARNING")
        eval_loss = None
        perplexity = None

    report = {
        "eval_loss": eval_loss,
        "perplexity": perplexity,
        "note": "Smoke evaluation on up to 8 samples",
    }
    report_path = build_dir / "evaluation_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    emit_log("evaluation", f"Report written to {report_path.name}")
    return report
