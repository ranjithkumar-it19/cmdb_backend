from typing import Optional
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, generate_uuid, utc_now


class AssetChangeEvent(Base):
    __tablename__ = "asset_change_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    asset_id: Mapped[str] = mapped_column(String(36), ForeignKey("assets.id", ondelete="CASCADE"), index=True, nullable=False)
    field_name: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    old_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    new_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    change_source: Mapped[str] = mapped_column(String(100), default="discovery", nullable=False)
    actor_or_process: Mapped[str] = mapped_column(String(100), default="system", nullable=False)
    observation_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True, nullable=False)

    asset: Mapped["Asset"] = relationship("Asset", back_populates="change_events")


Index("idx_change_asset_field_time", AssetChangeEvent.asset_id, AssetChangeEvent.field_name, AssetChangeEvent.created_at)
