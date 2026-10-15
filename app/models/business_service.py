from typing import List, Optional
from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, generate_uuid


class BusinessService(Base, TimestampMixin):
    """Represents a business service (e.g., Customer Portal, Core Payment Engine)."""
    __tablename__ = "business_services"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Classification
    criticality: Mapped[str] = mapped_column(String(50), default="medium", index=True, nullable=False)  # critical, high, medium, low
    sla_tier: Mapped[str] = mapped_column(String(50), default="standard", nullable=False)  # platinum, gold, silver, standard
    environment: Mapped[str] = mapped_column(String(50), default="production", index=True, nullable=False)

    # Ownership
    owner: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    team: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    contact_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Status
    status: Mapped[str] = mapped_column(String(50), default="active", index=True, nullable=False)  # active, degraded, maintenance, retired

    # Relationships
    asset_links: Mapped[List["BusinessServiceAsset"]] = relationship(
        "BusinessServiceAsset", back_populates="service", cascade="all, delete-orphan", lazy="selectin"
    )


class BusinessServiceAsset(Base):
    """Junction table linking business services to assets with a role descriptor."""
    __tablename__ = "business_service_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    service_id: Mapped[str] = mapped_column(String(36), ForeignKey("business_services.id", ondelete="CASCADE"), index=True, nullable=False)
    asset_id: Mapped[str] = mapped_column(String(36), ForeignKey("assets.id", ondelete="CASCADE"), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(100), default="supports", nullable=False)  # supports, hosts, depends_on, monitors
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    service: Mapped["BusinessService"] = relationship("BusinessService", back_populates="asset_links")
    asset = relationship("Asset")


Index("idx_bsa_service_asset", BusinessServiceAsset.service_id, BusinessServiceAsset.asset_id, unique=True)
