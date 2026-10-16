from typing import List, Optional
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, generate_uuid


class Asset(Base, TimestampMixin):
    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(36), index=True, nullable=True)

    # Core identification
    asset_tag: Mapped[Optional[str]] = mapped_column(String(100), unique=True, index=True, nullable=True)
    primary_hostname: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    display_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    asset_type: Mapped[str] = mapped_column(String(50), default="unknown", index=True, nullable=False)

    # Hardware specs
    manufacturer: Mapped[Optional[str]] = mapped_column(String(150), index=True, nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(150), index=True, nullable=True)
    serial_number: Mapped[Optional[str]] = mapped_column(String(150), index=True, nullable=True)
    cpu_info: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    memory_gb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    storage_gb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # OS & Environment
    operating_system: Mapped[Optional[str]] = mapped_column(String(100), index=True, nullable=True)
    operating_system_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    architecture: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    domain_or_workgroup: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    environment: Mapped[str] = mapped_column(String(50), default="production", index=True, nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(150), index=True, nullable=True)
    owner: Mapped[Optional[str]] = mapped_column(String(150), index=True, nullable=True)

    # Network
    primary_ip: Mapped[Optional[str]] = mapped_column(String(50), index=True, nullable=True)
    mac_addresses: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON or comma-separated

    # Status & Life-cycle
    status: Mapped[str] = mapped_column(String(50), default="active", index=True, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    department: Mapped[Optional[str]] = mapped_column(String(100), default="IT", index=True, nullable=True)
    lifecycle_status: Mapped[Optional[str]] = mapped_column(String(50), default="supported", index=True, nullable=True)
    is_server: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    first_discovered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_discovered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True, nullable=True)

    # Relationships
    identifiers: Mapped[List["AssetIdentifier"]] = relationship(
        "AssetIdentifier", back_populates="asset", cascade="all, delete-orphan", lazy="selectin"
    )
    change_events: Mapped[List["AssetChangeEvent"]] = relationship(
        "AssetChangeEvent", back_populates="asset", cascade="all, delete-orphan"
    )
    software_installations: Mapped[List["SoftwareInstallation"]] = relationship(
        "SoftwareInstallation", back_populates="asset", cascade="all, delete-orphan"
    )
    observations: Mapped[List["AssetObservation"]] = relationship(
        "AssetObservation", back_populates="asset"
    )


class AssetIdentifier(Base):
    __tablename__ = "asset_identifiers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    asset_id: Mapped[str] = mapped_column(String(36), ForeignKey("assets.id", ondelete="CASCADE"), index=True, nullable=False)
    identifier_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    identifier_value: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    raw_value: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    asset: Mapped["Asset"] = relationship("Asset", back_populates="identifiers")


# Indexes for rapid candidate matching during reconciliation
Index("idx_identifier_type_val", AssetIdentifier.identifier_type, AssetIdentifier.identifier_value)
Index("idx_asset_hostname_lower", Asset.primary_hostname)
Index("idx_asset_serial_lower", Asset.serial_number)
