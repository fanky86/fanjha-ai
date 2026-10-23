from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FANJHA_", env_file=".env", extra="ignore")

    # Server
    host: str = "127.0.0.1"
    port: int = 8765

    # Paths
    base_dir: Path = BASE_DIR
    database_url: str = f"sqlite+aiosqlite:///{BASE_DIR / 'fanjha.db'}"
    artifacts_dir: Path = BASE_DIR / "outputs"
    logs_dir: Path = BASE_DIR / "logs"
    data_dir: Path = BASE_DIR / "data"
    frontend_dist: Path = BASE_DIR / "frontend" / "dist"
    settings_file: Path = BASE_DIR / "fanjha_settings.json"

    # Limits
    max_log_entries_per_build: int = 100_000
    max_upload_bytes: int = 10 * 1024 * 1024
    max_concurrent_builds: int = 1
    rate_limit_builds_per_minute: int = 10

    # Security
    csrf_secret: str = "fanjha-local-csrf-secret-change-me-please"
    allowed_origins: list[str] = Field(
        default_factory=lambda: [
            "http://127.0.0.1:8765",
            "http://localhost:8765",
            "http://127.0.0.1:5173",
            "http://localhost:5173",
        ]
    )

    # Build defaults
    default_model_name: str = "sshleifer/tiny-gpt2"
    default_max_train_steps: int = 20
    default_batch_size: int = 2
    default_learning_rate: float = 5e-5
    default_max_seq_length: int = 128
    default_eval_steps: int = 5
    default_save_steps: int = 10

    # Runtime
    auto_build: bool = False
    build_timeout_seconds: int = 3600

    @field_validator("artifacts_dir", "logs_dir", "data_dir", mode="after")
    @classmethod
    def _ensure_absolute(cls, v: Path) -> Path:
        if not v.is_absolute():
            return BASE_DIR / v
        return v

    def ensure_directories(self) -> None:
        for path in (self.artifacts_dir, self.logs_dir, self.data_dir):
            path.mkdir(parents=True, exist_ok=True)

    def load_runtime_overrides(self) -> dict[str, Any]:
        if self.settings_file.is_file():
            try:
                return json.loads(self.settings_file.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def save_runtime_overrides(self, overrides: dict[str, Any]) -> None:
        self.settings_file.write_text(
            json.dumps(overrides, indent=2, ensure_ascii=False), encoding="utf-8"
        )


settings = Settings()
settings.ensure_directories()

# Apply runtime overrides
_runtime = settings.load_runtime_overrides()
for _k, _v in _runtime.items():
    if hasattr(settings, _k):
        try:
            setattr(settings, _k, _v)
        except Exception:
            pass
