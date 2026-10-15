from typing import List, Optional
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, generate_uuid, utc_now


class DiscoverySource(Base, TimestampMixin):
    __tablename__ = "discovery_sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)  # csv, windows_winrm, linux_ssh, snmp, mock
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    scope_definition: Mapped[str] = mapped_column(Text, nullable=False)  # JSON list of CIDRs, IPs, or Hostnames
    credentials_ref: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Secret vault reference or masked label
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    schedule_cron: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    jobs: Mapped[List["DiscoveryJob"]] = relationship("DiscoveryJob", back_populates="source", cascade="all, delete-orphan")


class DiscoveryJob(Base):
    __tablename__ = "discovery_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    source_id: Mapped[str] = mapped_column(String(36), ForeignKey("discovery_sources.id", ondelete="CASCADE"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="queued", index=True, nullable=False)  # queued, running, succeeded, partially_succeeded, failed, cancelled
    total_targets: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    processed_targets: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    successful_targets: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_targets: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    initiated_by_user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    source: Mapped["DiscoverySource"] = relationship("DiscoverySource", back_populates="jobs")
    targets: Mapped[List["DiscoveryJobTarget"]] = relationship("DiscoveryJobTarget", back_populates="job", cascade="all, delete-orphan")
    events: Mapped[List["DiscoveryJobEvent"]] = relationship("DiscoveryJobEvent", back_populates="job", cascade="all, delete-orphan")
    observations: Mapped[List["AssetObservation"]] = relationship("AssetObservation", back_populates="job")


class DiscoveryJobTarget(Base):
    __tablename__ = "discovery_job_targets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("discovery_jobs.id", ondelete="CASCADE"), index=True, nullable=False)
    target: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", index=True, nullable=False)  # pending, in_progress, succeeded, failed, skipped
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    job: Mapped["DiscoveryJob"] = relationship("DiscoveryJob", back_populates="targets")


class DiscoveryJobEvent(Base):
    __tablename__ = "discovery_job_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("discovery_jobs.id", ondelete="CASCADE"), index=True, nullable=False)
    target: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    event_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)  # info, warning, error, metric
    message: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON structured extra data
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    job: Mapped["DiscoveryJob"] = relationship("DiscoveryJob", back_populates="events")
