from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

BuildStatus = Literal[
    "IDLE",
    "PREPARING",
    "COLLECTING_DATA",
    "PREPROCESSING",
    "TOKENIZING",
    "TRAINING",
    "EVALUATING",
    "EXPORTING",
    "VERIFYING",
    "SUCCESS",
    "WARNING",
    "FAILED",
    "CANCELLED",
]


class BuildCreateRequest(BaseModel):
    model_name: str | None = None
    max_train_steps: int | None = Field(default=None, ge=1, le=100_000)
    batch_size: int | None = Field(default=None, ge=1, le=64)
    learning_rate: float | None = Field(default=None, gt=0, le=1.0)
    max_seq_length: int | None = Field(default=None, ge=8, le=4096)
    config: dict[str, Any] | None = None


class BuildOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: BuildStatus
    active_stage: str | None
    overall_progress: float
    config: dict[str, Any]
    started_at: datetime | None
    finished_at: datetime | None
    duration_seconds: float | None
    error_summary: str | None
    checkpoint_path: str | None
    correlation_id: str
    current_epoch: int | None
    current_step: int | None
    is_resumed: bool


class BuildSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: BuildStatus
    overall_progress: float
    started_at: datetime | None
    finished_at: datetime | None
    duration_seconds: float | None
    error_summary: str | None


class LogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    timestamp: datetime
    severity: str
    component: str
    message: str
    stack_trace: str | None


class LogsPage(BaseModel):
    logs: list[LogOut]
    next_cursor: int
    total: int | None = None


class MetricOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    timestamp: datetime
    epoch: int | None
    global_step: int | None
    train_loss: float | None
    val_loss: float | None
    perplexity: float | None
    learning_rate: float | None
    throughput_tokens_per_sec: float | None


class ArtifactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    size_bytes: int
    sha256: str
    verified: bool
    artifact_type: str
    created_at: datetime


class SystemResourcesOut(BaseModel):
    cpu_percent: float
    cpu_count: int
    ram_used: int
    ram_available: int
    ram_total: int
    disk_used: int
    disk_free: int
    disk_total: int
    process_ram_used: int | None = None
    gpu: dict[str, Any] | str


class DatasetInfo(BaseModel):
    path: str
    size_bytes: int
    documents: int | None
    estimated_tokens: int | None
    language: str | None = None
    source: str | None = None
    license: str | None = None


class SettingsPayload(BaseModel):
    default_model_name: str | None = None
    default_max_train_steps: int | None = Field(default=None, ge=1, le=100_000)
    default_batch_size: int | None = Field(default=None, ge=1, le=64)
    default_learning_rate: float | None = Field(default=None, gt=0, le=1.0)
    default_max_seq_length: int | None = Field(default=None, ge=8, le=4096)
