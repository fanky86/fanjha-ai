from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Index,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class Build(Base):
    __tablename__ = "builds"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    status: Mapped[str] = mapped_column(String(32), default="IDLE", index=True)
    active_stage: Mapped[str | None] = mapped_column(String(64), nullable=True)
    overall_progress: Mapped[float] = mapped_column(Float, default=0.0)
    config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    checkpoint_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    correlation_id: Mapped[str] = mapped_column(String(36), default=new_uuid, index=True)
    worker_pid: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_resumed: Mapped[bool] = mapped_column(Boolean, default=False)
    current_epoch: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_step: Mapped[int | None] = mapped_column(Integer, nullable=True)

    logs: Mapped[list["LogEntry"]] = relationship(
        back_populates="build", cascade="all, delete-orphan", lazy="selectin"
    )
    metrics: Mapped[list["Metric"]] = relationship(
        back_populates="build", cascade="all, delete-orphan", lazy="selectin"
    )
    artifacts: Mapped[list["Artifact"]] = relationship(
        back_populates="build", cascade="all, delete-orphan", lazy="selectin"
    )
    stage_events: Mapped[list["StageEvent"]] = relationship(
        back_populates="build", cascade="all, delete-orphan", lazy="selectin"
    )


class LogEntry(Base):
    __tablename__ = "logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    build_id: Mapped[str] = mapped_column(ForeignKey("builds.id", ondelete="CASCADE"), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    severity: Mapped[str] = mapped_column(String(16), default="INFO", index=True)
    component: Mapped[str] = mapped_column(String(64), default="orchestrator", index=True)
    message: Mapped[str] = mapped_column(Text)
    stack_trace: Mapped[str | None] = mapped_column(Text, nullable=True)

    build: Mapped[Build] = relationship(back_populates="logs")

    __table_args__ = (
        Index("ix_logs_build_ts", "build_id", "timestamp"),
    )


class Metric(Base):
    __tablename__ = "metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    build_id: Mapped[str] = mapped_column(ForeignKey("builds.id", ondelete="CASCADE"), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    epoch: Mapped[int | None] = mapped_column(Integer, nullable=True)
    global_step: Mapped[int | None] = mapped_column(Integer, nullable=True)
    train_loss: Mapped[float | None] = mapped_column(Float, nullable=True)
    val_loss: Mapped[float | None] = mapped_column(Float, nullable=True)
    perplexity: Mapped[float | None] = mapped_column(Float, nullable=True)
    learning_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    throughput_tokens_per_sec: Mapped[float | None] = mapped_column(Float, nullable=True)

    build: Mapped[Build] = relationship(back_populates="metrics")


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    build_id: Mapped[str] = mapped_column(ForeignKey("builds.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    relative_path: Mapped[str] = mapped_column(Text)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    sha256: Mapped[str] = mapped_column(String(64), default="")
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    artifact_type: Mapped[str] = mapped_column(String(64), default="file")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    build: Mapped[Build] = relationship(back_populates="artifacts")


class StageEvent(Base):
    __tablename__ = "stage_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    build_id: Mapped[str] = mapped_column(ForeignKey("builds.id", ondelete="CASCADE"), index=True)
    stage: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32))
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    build: Mapped[Build] = relationship(back_populates="stage_events")
