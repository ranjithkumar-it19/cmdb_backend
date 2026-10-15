from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class SoftwareProductBase(BaseModel):
    name: str
    normalized_name: str
    publisher: Optional[str] = None
    category: Optional[str] = None


class SoftwareProductResponse(SoftwareProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    installations_count: int = 0
    created_at: datetime


class SoftwareInstallationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    asset_id: str
    asset_display_name: Optional[str] = None
    product_id: str
    product_name: Optional[str] = None
    publisher: Optional[str] = None
    version: Optional[str] = None
    architecture: Optional[str] = None
    install_date: Optional[datetime] = None
    source: str
    last_seen_at: datetime
