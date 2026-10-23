"""Worker subprocess: runs the full pipeline and emits JSON-line events."""
from __future__ import annotations

import argparse
import json
import signal
import sys
from pathlib import Path
from typing import Any

_shutdown = {"requested": False}


def _handle_signal(signum, frame):  # noqa: ANN001
    _shutdown["requested"] = True
    try:
        print(
            json.dumps(
                {
                    "type": "log",
                    "severity": "WARNING",
                    "component": "worker",
                    "message": f"Received signal {signum}, attempting graceful shutdown",
                }
            ),
            flush=True,
        )
    except Exception:
        pass


def emit(event: dict[str, Any]) -> None:
    try:
        print(json.dumps(event, ensure_ascii=False, default=str), flush=True)
    except Exception:
        pass


def log(component: str, message: str, severity: str = "INFO", stack_trace: str | None = None) -> None:
    emit(
        {
            "type": "log",
            "severity": severity,
            "component": component,
            "message": message,
            "stack_trace": stack_trace,
        }
    )


def status(stage: str, progress: float, detail: str | None = None) -> None:
    emit(
        {
            "type": "status",
            "stage": stage,
            "status": stage,
            "overall_progress": progress,
            "detail": detail,
        }
    )


def metric(**kwargs: Any) -> None:
    emit({"type": "metric", **kwargs})


def artifact(**kwargs: Any) -> None:
    emit({"type": "artifact", **kwargs})


def checkpoint(path: str) -> None:
    emit({"type": "checkpoint", "path": path})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-id", required=True)
    parser.add_argument("--artifacts-dir", required=True)
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--model-name", default="sshleifer/tiny-gpt2")
    parser.add_argument("--max-steps", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--learning-rate", type=float, default=5e-5)
    parser.add_argument("--max-seq-length", type=int, default=128)
    parser.add_argument("--eval-steps", type=int, default=5)
    parser.add_argument("--save-steps", type=int, default=10)
    parser.add_argument("--resume-from-checkpoint", default=None)
    args = parser.parse_args()

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    try:
        from backend.pipeline import run_pipeline

        run_pipeline(
            build_id=args.build_id,
            artifacts_dir=Path(args.artifacts_dir),
            data_dir=Path(args.data_dir),
            model_name=args.model_name,
            max_steps=args.max_steps,
            batch_size=args.batch_size,
            learning_rate=args.learning_rate,
            max_seq_length=args.max_seq_length,
            eval_steps=args.eval_steps,
            save_steps=args.save_steps,
            resume_from_checkpoint=args.resume_from_checkpoint,
            emit_log=log,
            emit_status=status,
            emit_metric=metric,
            emit_artifact=artifact,
            emit_checkpoint=checkpoint,
            should_stop=lambda: _shutdown["requested"],
        )
        return 0
    except Exception as exc:  # noqa: BLE001
        import traceback

        log(
            "worker",
            f"Pipeline failed: {exc}",
            "CRITICAL",
            traceback.format_exc(),
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
