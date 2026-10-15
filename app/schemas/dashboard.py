from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class DashboardSummaryResponse(BaseModel):
    total_assets: int
    active_assets: int
    offline_assets: int
    asset_types_distribution: Dict[str, int]
    operating_systems_distribution: Dict[str, int]
    total_software_products: int
    total_software_installations: int
    total_discovery_jobs: int
    recent_jobs_count: int
    failed_jobs_count: int
    recent_changes_count: int
    recent_activities: List[Dict[str, Any]] = []


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    status: str
    ip_address: Optional[str] = None
    details: Optional[str] = None
    created_at: datetime
