from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class DiscoverySourceBase(BaseModel):
    name: str
    source_type: str
    description: Optional[str] = None
    scope_definition: str
    credentials_ref: Optional[str] = None
    is_active: bool = True
    schedule_cron: Optional[str] = None


class DiscoverySourceCreate(DiscoverySourceBase):
    pass


class DiscoverySourceResponse(DiscoverySourceBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class DiscoveryJobTargetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job_id: str
    target: str
    status: str
    attempts: int
    error_message: Optional[str] = None
    duration_seconds: Optional[float] = None
    created_at: datetime


class DiscoveryJobEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job_id: str
    target: Optional[str] = None
    event_type: str
    message: str
    timestamp: datetime


class DiscoveryJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_id: str
    status: str
    total_targets: int
    processed_targets: int
    successful_targets: int
    failed_targets: int
    error_summary: Optional[str] = None
    initiated_by_user_id: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    source: Optional[DiscoverySourceResponse] = None


class DiscoveryJobCreate(BaseModel):
    source_id: str
    targets: Optional[List[str]] = None
