from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class VulnerabilityItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    cve_id: str
    title: str
    description: Optional[str] = None
    risk_score: float
    severity: str
    patch_available: bool
    exploited_in_wild: bool
    vendor: str
    affected_product: str
    affected_assets_count: int
    is_ignored: bool = False
    published_at: Optional[datetime] = None


class LifecyclePeriod(BaseModel):
    period: str
    supported: int
    end_of_life: int
    end_of_support: int


class DepartmentUserShare(BaseModel):
    department: str
    count: int
    percentage: float
    color: str


class DepartmentVulnBar(BaseModel):
    department: str
    count: int
    color: str


class VendorProductCount(BaseModel):
    vendor: str
    count: int
    products: List[Dict[str, Any]] = []


class AcmeRiskReviewResponse(BaseModel):
    dashboard_title: str = "Acme Risk Review"
    total_assets: int
    assets_trend_pct: float
    total_software_titles: int
    software_trend_pct: float
    total_users: int
    users_trend_pct: float
    lifecycle_progression: List[LifecyclePeriod]
    users_by_department: List[DepartmentUserShare]
    vulnerabilities_by_department: Dict[str, List[DepartmentVulnBar]]
    servers_at_risk_by_severity: Dict[str, int]


class MonthlyVulnTrend(BaseModel):
    month: str
    critical: int
    high: int
    medium: int


class VulnerableAssetsOverviewResponse(BaseModel):
    total_vulnerabilities: int
    new_vulnerabilities: int
    vulnerable_assets: int
    cves: List[VulnerabilityItem]
    vulnerabilities_by_severity: Dict[str, int]
    vulnerable_assets_over_time: List[MonthlyVulnTrend]
    patch_info: Dict[str, int]
    exploited_in_wild: Dict[str, int]
    vendor_affected_products: List[VendorProductCount]


class HardwareWarrantyItem(BaseModel):
    id: str
    asset_name: str
    asset_type: str
    manufacturer: str
    model: str
    serial_number: str
    purchase_date: Optional[str] = None
    warranty_expiration: str
    warranty_status: str  # active, expiring_30d, expiring_90d, expired
    support_tier: str
    estimated_replacement_cost: int
    location: Optional[str] = None


class HardwareLifecycleResponse(BaseModel):
    total_tracked_assets: int
    active_warranty: int
    expiring_soon_30d: int
    expiring_soon_90d: int
    expired_warranty: int
    total_replacement_budget: int
    vendor_distribution: Dict[str, int]
    warranty_by_type: Dict[str, Dict[str, int]]
    hardware_items: List[HardwareWarrantyItem]


class OSAssetItem(BaseModel):
    id: str
    hostname: str
    ip_address: str
    operating_system: str
    os_version: str
    os_family: str  # windows, linux, macos
    support_status: str  # supported, extended, end_of_life, end_of_support
    eol_date: str
    win11_ready: Optional[bool] = None
    asset_type: str


class OSFamilySummary(BaseModel):
    name: str
    version: str
    family: str
    count: int
    support_status: str
    eol_date: str
    percent: float


class OSLifecycleResponse(BaseModel):
    total_systems: int
    fully_supported: int
    extended_support: int
    end_of_life: int
    end_of_support: int
    win10_eol_countdown_days: int
    win11_ready_percentage: float
    os_families: List[OSFamilySummary]
    systems: List[OSAssetItem]


class SecurityInsightFinding(BaseModel):
    id: str
    category: str  # exposure, compliance, hygiene, security
    title: str
    description: str
    severity: str  # critical, high, medium, low
    affected_count: int
    recommended_action: str
    impact: str
    detected_at: str


class SecurityInsightsResponse(BaseModel):
    total_findings: int
    critical_findings: int
    high_findings: int
    compliance_score: int
    findings: List[SecurityInsightFinding]

