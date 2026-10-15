"""
ServiceNow CMDB Integration Connector.

Provides bidirectional sync between Atlas Discovery CMDB and ServiceNow CMDB.
Supports mapping to cmdb_ci, cmdb_ci_server, cmdb_ci_network_adapter tables.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import DateTime, String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin, generate_uuid


class IntegrationConfig(Base, TimestampMixin):
    """Stores configuration for external ITSM integrations (ServiceNow, etc.)."""
    __tablename__ = "integration_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    integration_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)  # servicenow, jira, etc.
    instance_url: Mapped[str] = mapped_column(String(500), nullable=False)
    auth_type: Mapped[str] = mapped_column(String(50), default="basic", nullable=False)  # basic, oauth, token
    credentials_ref: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sync_direction: Mapped[str] = mapped_column(String(50), default="push", nullable=False)  # push, pull, bidirectional
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    sync_stats: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON: {pushed, pulled, errors}


class IntegrationSyncLog(Base):
    """Tracks individual sync operations for auditing."""
    __tablename__ = "integration_sync_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    config_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    direction: Mapped[str] = mapped_column(String(20), nullable=False)  # push, pull
    status: Mapped[str] = mapped_column(String(50), nullable=False)  # success, partial, failed
    records_pushed: Mapped[int] = mapped_column(default=0, nullable=False)
    records_pulled: Mapped[int] = mapped_column(default=0, nullable=False)
    errors_count: Mapped[int] = mapped_column(default=0, nullable=False)
    error_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
