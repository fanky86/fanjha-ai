from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

from backend.pipeline import PipelineCancelled


def train(
    *,
    model_dir: Path,
    tokenizer_dir: Path,
    dataset_path: Path,
    output_dir: Path,
    max_steps: int,
    batch_size: int,
    learning_rate: float,
    max_seq_length: int,
    eval_steps: int,
    save_steps: int,
    resume_from_checkpoint: str | None,
    emit_log: Callable[..., None],
    emit_metric: Callable[..., None],
    emit_status: Callable[..., None],
    emit_checkpoint: Callable[[str], None],
    should_stop: Callable[[], bool],
) -> Path:
    import torch
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        DataCollatorForLanguageModeling,
        Trainer,
        TrainerCallback,
        TrainingArguments,
    )
    from datasets import load_dataset

    output_dir.mkdir(parents=True, exist_ok=True)

    tokenizer = AutoTokenizer.from_pretrained(tokenizer_dir)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    emit_log("training", f"Loading dataset from {dataset_path.name}")
    raw = load_dataset("json", data_files=str(dataset_path), split="train")
    emit_log("training", f"Loaded {len(raw)} documents")

    def tokenize(batch):
        return tokenizer(
            batch["text"],
            truncation=True,
            padding="max_length",
            max_length=max_seq_length,
        )

    tokenized = raw.map(tokenize, batched=True, remove_columns=["text"])

    if len(tokenized) >= 4:
        split = tokenized.train_test_split(test_size=0.1, seed=42)
        train_ds = split["train"]
        eval_ds = split["test"]
    else:
        train_ds = tokenized
        eval_ds = tokenized

    emit_log(
        "training",
        f"Train: {len(train_ds)} / Eval: {len(eval_ds)} samples",
    )

    model = AutoModelForCausalLM.from_pretrained(model_dir)
    total_params = sum(p.numel() for p in model.parameters())
    emit_log("training", f"Model parameters: {total_params:,}")

    class ProgressCallback(TrainerCallback):
        def on_log(self, args, state, control, logs=None, **kwargs):  # noqa: ANN001
            if should_stop():
                control.should_training_stop = True
                return
            logs = logs or {}
            train_loss = logs.get("loss")
            val_loss = logs.get("eval_loss")
            lr = logs.get("learning_rate")
            if train_loss is not None or val_loss is not None:
                perplexity = None
                if val_loss is not None:
                    try:
                        perplexity = float(torch.exp(torch.tensor(val_loss)))
                    except Exception:
                        perplexity = None
                emit_metric(
                    epoch=state.epoch,
                    global_step=state.global_step,
                    train_loss=float(train_loss) if train_loss is not None else None,
                    val_loss=float(val_loss) if val_loss is not None else None,
                    perplexity=perplexity,
                    learning_rate=float(lr) if lr is not None else None,
                    overall_progress=30.0
                    + (state.global_step / max(1, max_steps)) * 45.0,
                )

        def on_save(self, args, state, control, **kwargs):  # noqa: ANN001
            ckpt = Path(args.output_dir) / f"checkpoint-{state.global_step}"
            if ckpt.exists():
                emit_checkpoint(str(ckpt))
                emit_log("checkpoint", f"Saved checkpoint-{state.global_step}")

    device = "cuda" if torch.cuda.is_available() else "cpu"

    args = TrainingArguments(
        output_dir=str(output_dir),
        max_steps=max_steps,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        learning_rate=learning_rate,
        logging_steps=1,
        eval_strategy="steps",
        eval_steps=max(1, eval_steps),
        save_steps=max(1, save_steps),
        save_total_limit=2,
        report_to="none",
        remove_unused_columns=False,
        use_cpu=(device == "cpu"),
        dataloader_pin_memory=False,
        disable_tqdm=True,
    )

    collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        tokenizer=tokenizer,
        data_collator=collator,
        callbacks=[ProgressCallback()],
    )

    start = time.time()
    emit_log("training", f"Starting training (max_steps={max_steps}, device={device})")

    try:
        if resume_from_checkpoint and Path(resume_from_checkpoint).exists():
            emit_log("training", f"Resuming from {resume_from_checkpoint}")
            trainer.train(resume_from_checkpoint=resume_from_checkpoint)
        else:
            trainer.train()
    except Exception as exc:  # noqa: BLE001
        emit_log("training", f"Training error: {exc}", "ERROR")
        # Save whatever we have
        try:
            partial = output_dir / "final"
            trainer.save_model(str(partial))
            emit_checkpoint(str(partial))
        except Exception:
            pass
        raise

    if should_stop():
        raise PipelineCancelled("Training cancelled")

    duration = time.time() - start
    final_dir = output_dir / "final"
    final_dir.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(final_dir))
    tokenizer.save_pretrained(str(final_dir))
    emit_checkpoint(str(final_dir))

    final_metrics = trainer.state.log_history[-1] if trainer.state.log_history else {}
    emit_metric(
        epoch=trainer.state.epoch,
        global_step=trainer.state.global_step,
        train_loss=final_metrics.get("loss"),
        val_loss=final_metrics.get("eval_loss"),
        learning_rate=final_metrics.get("learning_rate"),
        overall_progress=78.0,
    )

    emit_log(
        "training",
        f"Training finished in {duration:.1f}s — checkpoint at {final_dir}",
    )
    return final_dir
