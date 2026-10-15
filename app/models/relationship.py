from typing import Optional
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, String, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, generate_uuid, utc_now


class AssetRelationship(Base):
    __tablename__ = "asset_relationships"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    source_asset_id: Mapped[str] = mapped_column(String(36), ForeignKey("assets.id", ondelete="CASCADE"), index=True, nullable=False)
    target_asset_id: Mapped[str] = mapped_column(String(36), ForeignKey("assets.id", ondelete="CASCADE"), index=True, nullable=False)
    relationship_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)  # runs_on, hosted_on, connects_to, depends_on, managed_by, member_of, communicates_with
    source: Mapped[str] = mapped_column(String(100), default="manual", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    valid_to: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    source_asset: Mapped["Asset"] = relationship("Asset", foreign_keys=[source_asset_id])
    target_asset: Mapped["Asset"] = relationship("Asset", foreign_keys=[target_asset_id])

    __table_args__ = (
        CheckConstraint("source_asset_id != target_asset_id", name="ck_no_self_relationship"),
        Index("idx_rel_source_target_type", "source_asset_id", "target_asset_id", "relationship_type"),
    )
