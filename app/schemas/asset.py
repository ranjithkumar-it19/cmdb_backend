from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class AssetIdentifierSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    identifier_type: str
    identifier_value: str
    raw_value: Optional[str] = None
    source: str
    confidence: float
    is_primary: bool


class AssetBase(BaseModel):
    display_name: str
    asset_tag: Optional[str] = None
    primary_hostname: Optional[str] = None
    asset_type: str = "unknown"
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    cpu_info: Optional[str] = None
    memory_gb: Optional[float] = None
    storage_gb: Optional[float] = None
    operating_system: Optional[str] = None
    operating_system_version: Optional[str] = None
    architecture: Optional[str] = None
    domain_or_workgroup: Optional[str] = None
    environment: str = "production"
    location: Optional[str] = None
    owner: Optional[str] = None
    primary_ip: Optional[str] = None
    mac_addresses: Optional[str] = None
    status: str = "active"


class AssetCreate(AssetBase):
    pass


class AssetUpdate(BaseModel):
    display_name: Optional[str] = None
    asset_tag: Optional[str] = None
    primary_hostname: Optional[str] = None
    asset_type: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    cpu_info: Optional[str] = None
    memory_gb: Optional[float] = None
    storage_gb: Optional[float] = None
    operating_system: Optional[str] = None
    operating_system_version: Optional[str] = None
    architecture: Optional[str] = None
    domain_or_workgroup: Optional[str] = None
    environment: Optional[str] = None
    location: Optional[str] = None
    owner: Optional[str] = None
    primary_ip: Optional[str] = None
    mac_addresses: Optional[str] = None
    status: Optional[str] = None


class AssetResponse(AssetBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: Optional[str] = None
    confidence_score: float
    first_discovered_at: Optional[datetime] = None
    last_discovered_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    identifiers: List[AssetIdentifierSchema] = []


class PaginatedAssetsResponse(BaseModel):
    items: List[AssetResponse]
    total: int
    page: int
    page_size: int
    pages: int


class AssetChangeEventSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    asset_id: str
    field_name: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    change_source: str
    actor_or_process: str
    created_at: datetime


class AssetDetailResponse(AssetResponse):
    change_events: List[AssetChangeEventSchema] = []
