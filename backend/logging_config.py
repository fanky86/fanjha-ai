from __future__ import annotations

import json
import logging
import logging.handlers
import re
import sys
from datetime import datetime, timezone
from typing import Any

_SECRET_PATTERN = re.compile(
    r"(?i)(api[_-]?key|secret|password|token|authorization|bearer)\s*[:=]\s*\S+"
)
_REDACTED = "<REDACTED>"


def redact(text: str) -> str:
    if not text:
        return text
    return _SECRET_PATTERN.sub(r"\1=" + _REDACTED, text)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "severity": record.levelname,
            "component": getattr(record, "component", record.name),
            "message": redact(record.getMessage()),
        }
        if hasattr(record, "build_id"):
            payload["build_id"] = record.build_id
        if hasattr(record, "correlation_id"):
            payload["correlation_id"] = record.correlation_id
        if record.exc_info:
            payload["stack_trace"] = redact(self.formatException(record.exc_info))
        extra = getattr(record, "extra_fields", None)
        if isinstance(extra, dict):
            for k, v in extra.items():
                payload[k] = redact(v) if isinstance(v, str) else v
        return json.dumps(payload, ensure_ascii=False, default=str)


_CONFIGURED = False


def setup_logging(level: str = "INFO") -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    _CONFIGURED = True

    from backend.config import settings

    settings.logs_dir.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(JsonFormatter())
    root.addHandler(stream)

    file_handler = logging.handlers.RotatingFileHandler(
        settings.logs_dir / "fanjha.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(JsonFormatter())
    root.addHandler(file_handler)

    logging.getLogger("uvicorn.access").setLevel("WARNING")
    logging.getLogger("sqlalchemy.engine").setLevel("WARNING")


def get_logger(component: str) -> logging.Logger:
    logger = logging.getLogger(component)
    logger.setLevel(logging.DEBUG)
    return logger
