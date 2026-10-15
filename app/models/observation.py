from typing import Optional
from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, generate_uuid, utc_now


class AssetObservation(Base):
    __tablename__ = "asset_observations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    source_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("discovery_sources.id", ondelete="SET NULL"), index=True, nullable=True)
    job_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("discovery_jobs.id", ondelete="SET NULL"), index=True, nullable=True)
    asset_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("assets.id", ondelete="SET NULL"), index=True, nullable=True)

    # Observed raw fields
    observed_hostname: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    observed_ip: Mapped[Optional[str]] = mapped_column(String(50), index=True, nullable=True)
    observed_macs: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list
    observed_os: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    observed_serial: Mapped[Optional[str]] = mapped_column(String(150), index=True, nullable=True)

    # Payloads
    raw_payload: Mapped[str] = mapped_column(Text, nullable=False)  # JSON payload from scanner/adapter
    normalized_payload: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON payload post-normalizer

    # Processing status & reconciliation outcome
    validation_status: Mapped[str] = mapped_column(String(50), default="valid", index=True, nullable=False)  # valid, invalid, incomplete
    reconciliation_decision: Mapped[str] = mapped_column(String(50), default="pending", index=True, nullable=False)  # created_new, updated_existing, flagged_review, ignored
    confidence_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    job: Mapped[Optional["DiscoveryJob"]] = relationship("DiscoveryJob", back_populates="observations")
    asset: Mapped[Optional["Asset"]] = relationship("Asset", back_populates="observations")
