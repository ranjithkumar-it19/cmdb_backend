from typing import List, Optional
from pydantic import BaseModel


class IntegrationConfigCreate(BaseModel):
    name: str
    integration_type: str = "servicenow"
    instance_url: str
    auth_type: str = "basic"
    credentials_ref: Optional[str] = None
    username: Optional[str] = None
    is_active: bool = True
    sync_direction: str = "push"


class IntegrationConfigUpdate(BaseModel):
    name: Optional[str] = None
    instance_url: Optional[str] = None
    auth_type: Optional[str] = None
    credentials_ref: Optional[str] = None
    username: Optional[str] = None
    is_active: Optional[bool] = None
    sync_direction: Optional[str] = None


class IntegrationConfigResponse(BaseModel):
    id: str
    name: str
    integration_type: str
    instance_url: str
    auth_type: str
    username: Optional[str] = None
    is_active: bool
    sync_direction: str
    last_sync_at: Optional[str] = None
    last_sync_status: Optional[str] = None
    sync_stats: Optional[str] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class IntegrationSyncLogResponse(BaseModel):
    id: str
    config_id: str
    direction: str
    status: str
    records_pushed: int
    records_pulled: int
    errors_count: int
    error_details: Optional[str] = None
    started_at: str
    completed_at: Optional[str] = None

    class Config:
        from_attributes = True
