from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import String, Integer, DateTime, Boolean, Text, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON
from app.db.session import Base


def now():
    return datetime.now(timezone.utc)


class MonitorTask(Base):
    __tablename__ = "monitor_tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    platforms: Mapped[list[str]] = mapped_column(JSON, default=list)
    content_types: Mapped[list[str]] = mapped_column(JSON, default=lambda: ["video", "live"])
    include_keywords: Mapped[list[str]] = mapped_column(JSON, default=list)
    exclude_keywords: Mapped[list[str]] = mapped_column(JSON, default=list)
    interval_seconds: Mapped[int] = mapped_column(Integer, default=300)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    profile: Mapped["TaskProfile | None"] = relationship(
        back_populates="task", cascade="all, delete-orphan", uselist=False
    )


class TaskProfile(Base):
    """Extended task configuration kept in a separate table for backwards-compatible upgrades."""

    __tablename__ = "task_profiles"
    __table_args__ = (UniqueConstraint("task_id", name="uq_task_profile_task_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("monitor_tasks.id"), index=True)
    topic_template: Mapped[str] = mapped_column(String(80), default="custom")
    regions: Mapped[list[str]] = mapped_column(JSON, default=list)
    keyword_match_mode: Mapped[str] = mapped_column(String(20), default="any")
    time_range_hours: Mapped[int] = mapped_column(Integer, default=24)
    sort_by: Mapped[str] = mapped_column(String(20), default="latest")
    result_limit: Mapped[int] = mapped_column(Integer, default=50)
    collect_comments: Mapped[bool] = mapped_column(Boolean, default=True)
    expand_related: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_audit: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_capture: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_push: Mapped[bool] = mapped_column(Boolean, default=False)
    push_after_review: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    task: Mapped[MonitorTask] = relationship(back_populates="profile")


class Content(Base):
    __tablename__ = "contents"
    __table_args__ = (UniqueConstraint("platform", "platform_content_id", name="uq_content_platform_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    platform: Mapped[str] = mapped_column(String(32), index=True)
    platform_content_id: Mapped[str] = mapped_column(String(256))
    content_type: Mapped[str] = mapped_column(String(32), index=True)
    title: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[str] = mapped_column(Text, default="")
    source_url: Mapped[str] = mapped_column(Text, default="")
    media_url: Mapped[str] = mapped_column(Text, default="")
    stream_url: Mapped[str] = mapped_column(Text, default="")
    cover_url: Mapped[str] = mapped_column(Text, default="")
    author_alias: Mapped[str] = mapped_column(String(80), default="anonymous")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    matched_keywords: Mapped[list[str]] = mapped_column(JSON, default=list)
    filter_status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    filter_score: Mapped[float] = mapped_column(Float, default=0)
    filter_reasons: Mapped[list[str]] = mapped_column(JSON, default=list)
    risk_status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    raw_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    comments: Mapped[list["Comment"]] = relationship(back_populates="content", cascade="all, delete-orphan")


class Comment(Base):
    __tablename__ = "comments"
    __table_args__ = (UniqueConstraint("platform", "platform_comment_id_hash", name="uq_comment_platform_hash"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    content_id: Mapped[int] = mapped_column(ForeignKey("contents.id"), index=True)
    platform: Mapped[str] = mapped_column(String(32))
    platform_comment_id_hash: Mapped[str] = mapped_column(String(64))
    author_alias: Mapped[str] = mapped_column(String(80), default="anonymous")
    text: Mapped[str] = mapped_column(Text)
    like_count: Mapped[int] = mapped_column(Integer, default=0)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    filter_status: Mapped[str] = mapped_column(String(32), default="pending")
    risk_status: Mapped[str] = mapped_column(String(32), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    content: Mapped[Content] = relationship(back_populates="comments")


class LiveMessage(Base):
    __tablename__ = "live_messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    content_id: Mapped[int] = mapped_column(ForeignKey("contents.id"), index=True)
    message_type: Mapped[str] = mapped_column(String(32), default="comment")
    author_alias: Mapped[str] = mapped_column(String(80), default="anonymous")
    text: Mapped[str] = mapped_column(Text, default="")
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    raw_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class ExpansionLead(Base):
    """Content-level expansion lead. No real-world identity or political profile is stored."""

    __tablename__ = "expansion_leads"
    id: Mapped[int] = mapped_column(primary_key=True)
    source_content_id: Mapped[int] = mapped_column(ForeignKey("contents.id"), index=True)
    lead_type: Mapped[str] = mapped_column(String(40), index=True)
    label: Mapped[str] = mapped_column(String(300))
    evidence_count: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(32), default="new", index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class LiveSession(Base):
    __tablename__ = "live_sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    content_id: Mapped[int] = mapped_column(ForeignKey("contents.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="running", index=True)
    segment_seconds: Mapped[int] = mapped_column(Integer, default=120)
    next_segment_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    stopped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str] = mapped_column(Text, default="")


class AuditResult(Base):
    __tablename__ = "audit_results"
    id: Mapped[int] = mapped_column(primary_key=True)
    content_id: Mapped[int] = mapped_column(ForeignKey("contents.id"), index=True)
    modality: Mapped[str] = mapped_column(String(32), index=True)
    detector_name: Mapped[str] = mapped_column(String(100), default="external-detector")
    detector_version: Mapped[str] = mapped_column(String(50), default="unknown")
    status: Mapped[str] = mapped_column(String(32), default="unknown")
    labels: Mapped[list[str]] = mapped_column(JSON, default=list)
    risk_words: Mapped[list[str]] = mapped_column(JSON, default=list)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    response: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class EvidenceFile(Base):
    __tablename__ = "evidence_files"
    id: Mapped[int] = mapped_column(primary_key=True)
    content_id: Mapped[int] = mapped_column(ForeignKey("contents.id"), index=True)
    file_type: Mapped[str] = mapped_column(String(32))
    file_path: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64))
    source_url: Mapped[str] = mapped_column(Text, default="")
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    processing_history: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)


class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_type: Mapped[str] = mapped_column(String(50), index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    run_after: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class PushRecord(Base):
    __tablename__ = "push_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    content_id: Mapped[int] = mapped_column(ForeignKey("contents.id"), index=True)
    target: Mapped[str] = mapped_column(String(200))
    payload_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="pending")
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str] = mapped_column(Text, default="")
    ack_id: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
