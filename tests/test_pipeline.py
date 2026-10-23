from __future__ import annotations

import json
from pathlib import Path

import pytest


def test_pipeline_smoke(tmp_path):
    """Run the pipeline synchronously with a tiny synthetic dataset.

    This test does NOT require network access if transformers/torch caches are warm.
    If not cached, it will download sshleifer/tiny-gpt2 (~4MB).
    """
    try:
        import torch  # noqa: F401
        import transformers  # noqa: F401
    except ImportError:
        pytest.skip("torch / transformers not installed")

    from backend.pipeline import run_pipeline

    artifacts = tmp_path / "outputs"
    data = tmp_path / "data"
    artifacts.mkdir()
    data.mkdir()

    # Write synthetic dataset
    sample = data / "sample.jsonl"
    with sample.open("w", encoding="utf-8") as f:
        for i in range(20):
            f.write(json.dumps({"text": f"Sample training text number {i}."}) + "\n")

    events: list[dict] = []

    def log(component, message, severity="INFO", stack_trace=None):
        events.append({"type": "log", "component": component, "message": message})

    def status(stage, progress, detail=None):
        events.append({"type": "status", "stage": stage, "progress": progress})

    def metric(**kw):
        events.append({"type": "metric", **kw})

    def artifact(**kw):
        events.append({"type": "artifact", **kw})

    def checkpoint(path):
        events.append({"type": "checkpoint", "path": path})

    run_pipeline(
        build_id="test-build",
        artifacts_dir=artifacts,
        data_dir=data,
        model_name="sshleifer/tiny-gpt2",
        max_steps=2,
        batch_size=1,
        learning_rate=5e-5,
        max_seq_length=32,
        eval_steps=1,
        save_steps=1,
        resume_from_checkpoint=None,
        emit_log=log,
        emit_status=status,
        emit_metric=metric,
        emit_artifact=artifact,
        emit_checkpoint=checkpoint,
        should_stop=lambda: False,
    )

    # Verify final artifact exists
    final = artifacts / "test-build" / "FANJHA_MODEL_FINAL.zip"
    assert final.is_file(), f"Final ZIP missing at {final}"

    # Verify manifest
    manifest = artifacts / "test-build" / "artifact_manifest.json"
    assert manifest.is_file()
    data_json = json.loads(manifest.read_text())
    assert "zip_sha256" in data_json
