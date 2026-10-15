from typing import List, Optional
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, generate_uuid, utc_now


class SoftwareProduct(Base):
    __tablename__ = "software_products"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    publisher: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    installations: Mapped[List["SoftwareInstallation"]] = relationship("SoftwareInstallation", back_populates="product", cascade="all, delete-orphan")


class SoftwareInstallation(Base):
    __tablename__ = "software_installations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    asset_id: Mapped[str] = mapped_column(String(36), ForeignKey("assets.id", ondelete="CASCADE"), index=True, nullable=False)
    product_id: Mapped[str] = mapped_column(String(36), ForeignKey("software_products.id", ondelete="CASCADE"), index=True, nullable=False)
    version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    architecture: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    install_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    install_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    source: Mapped[str] = mapped_column(String(100), default="discovery", nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    asset: Mapped["Asset"] = relationship("Asset", back_populates="software_installations")
    product: Mapped["SoftwareProduct"] = relationship("SoftwareProduct", back_populates="installations")


Index("idx_software_asset_product", SoftwareInstallation.asset_id, SoftwareInstallation.product_id)
