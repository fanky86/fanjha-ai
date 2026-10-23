from __future__ import annotations

import traceback
from pathlib import Path
from typing import Callable

EmitLog = Callable[..., None]
EmitStatus = Callable[..., None]
EmitMetric = Callable[..., None]
EmitArtifact = Callable[..., None]
EmitCheckpoint = Callable[[str], None]
ShouldStop = Callable[[], bool]


class PipelineCancelled(RuntimeError):
    pass


STAGE_ORDER = [
    "PREPARING",
    "COLLECTING_DATA",
    "PREPROCESSING",
    "TOKENIZING",
    "TRAINING",
    "EVALUATING",
    "EXPORTING",
    "VERIFYING",
    "SUCCESS",
]

STAGE_PROGRESS = {
    "PREPARING": 2.0,
    "COLLECTING_DATA": 8.0,
    "PREPROCESSING": 16.0,
    "TOKENIZING": 24.0,
    "TRAINING": 30.0,
    "EVALUATING": 80.0,
    "EXPORTING": 88.0,
    "VERIFYING": 94.0,
    "SUCCESS": 100.0,
}


def run_pipeline(
    *,
    build_id: str,
    artifacts_dir: Path,
    data_dir: Path,
    model_name: str,
    max_steps: int,
    batch_size: int,
    learning_rate: float,
    max_seq_length: int,
    eval_steps: int,
    save_steps: int,
    resume_from_checkpoint: str | None,
    emit_log: EmitLog,
    emit_status: EmitStatus,
    emit_metric: EmitMetric,
    emit_artifact: EmitArtifact,
    emit_checkpoint: EmitCheckpoint,
    should_stop: ShouldStop,
) -> None:
    from backend.pipeline import (
        environment,
        dataset,
        preprocessing,
        tokenizer,
        model,
        training,
        evaluation,
        export,
        verify,
    )

    build_dir = artifacts_dir / build_id
    build_dir.mkdir(parents=True, exist_ok=True)

    def _stopped() -> None:
        if should_stop():
            raise PipelineCancelled("Build cancelled by user")

    # Stage: environment
    emit_status("PREPARING", STAGE_PROGRESS["PREPARING"])
    try:
        environment.validate(emit_log)
    except Exception:
        emit_log("environment", "Environment validation failed", "CRITICAL", traceback.format_exc())
        raise
    _stopped()

    # Stage: collect
    emit_status("COLLECTING_DATA", STAGE_PROGRESS["COLLECTING_DATA"])
    files = dataset.discover(data_dir, emit_log)
    _stopped()

    # Stage: preprocess
    emit_status("PREPROCESSING", STAGE_PROGRESS["PREPROCESSING"])
    processed_path = preprocessing.preprocess(files, build_dir, emit_log)
    _stopped()

    # Stage: tokenizer
    emit_status("TOKENIZING", STAGE_PROGRESS["TOKENIZING"])
    tokenizer_dir = tokenizer.train_or_load(processed_path, build_dir, model_name, emit_log)
    _stopped()

    # Stage: model init
    model_dir = model.initialize(model_name, build_dir, emit_log)
    _stopped()

    # Stage: training
    emit_status("TRAINING", STAGE_PROGRESS["TRAINING"])
    ckpt_dir = training.train(
        model_dir=model_dir,
        tokenizer_dir=tokenizer_dir,
        dataset_path=processed_path,
        output_dir=build_dir / "checkpoints",
        max_steps=max_steps,
        batch_size=batch_size,
        learning_rate=learning_rate,
        max_seq_length=max_seq_length,
        eval_steps=eval_steps,
        save_steps=save_steps,
        resume_from_checkpoint=resume_from_checkpoint,
        emit_log=emit_log,
        emit_metric=emit_metric,
        emit_status=emit_status,
        emit_checkpoint=emit_checkpoint,
        should_stop=should_stop,
    )

    # Stage: evaluate
    emit_status("EVALUATING", STAGE_PROGRESS["EVALUATING"])
    eval_report = evaluation.evaluate(build_dir, ckpt_dir, tokenizer_dir, processed_path, emit_log)

    # Stage: export
    emit_status("EXPORTING", STAGE_PROGRESS["EXPORTING"])
    export_dir = export.export_model(build_dir, ckpt_dir, tokenizer_dir, emit_log)

    # Stage: verify + package
    emit_status("VERIFYING", STAGE_PROGRESS["VERIFYING"])
    zip_path = verify.verify_and_package(build_dir, export_dir, eval_report, emit_log, emit_artifact)

    # Emit each artifact entry
    for f in verify.list_artifacts(build_dir):
        rel = f.relative_to(artifacts_dir)
        emit_artifact(
            name=f.name,
            relative_path=str(rel),
            size_bytes=f.stat().st_size,
            sha256=verify.sha256_file(f),
            verified=True,
            artifact_type="zip" if f.suffix == ".zip" else "file",
        )

    emit_status("SUCCESS", STAGE_PROGRESS["SUCCESS"])
