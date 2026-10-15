from typing import List, Optional
from pydantic import BaseModel


class BusinessServiceCreate(BaseModel):
    name: str
    description: Optional[str] = None
    criticality: str = "medium"
    sla_tier: str = "standard"
    environment: str = "production"
    owner: Optional[str] = None
    team: Optional[str] = None
    contact_email: Optional[str] = None
    status: str = "active"


class BusinessServiceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    criticality: Optional[str] = None
    sla_tier: Optional[str] = None
    environment: Optional[str] = None
    owner: Optional[str] = None
    team: Optional[str] = None
    contact_email: Optional[str] = None
    status: Optional[str] = None


class BusinessServiceAssetLink(BaseModel):
    asset_id: str
    role: str = "supports"
    is_primary: bool = False


class BusinessServiceAssetResponse(BaseModel):
    id: str
    asset_id: str
    role: str
    is_primary: bool
    asset_display_name: Optional[str] = None
    asset_type: Optional[str] = None
    asset_status: Optional[str] = None

    class Config:
        from_attributes = True


class BusinessServiceResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    criticality: str
    sla_tier: str
    environment: str
    owner: Optional[str] = None
    team: Optional[str] = None
    contact_email: Optional[str] = None
    status: str
    asset_count: int = 0
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True
