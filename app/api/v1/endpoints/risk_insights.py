from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.auth_service import get_current_user
from app.models.user import User
from app.schemas.risk_insights import (
    AcmeRiskReviewResponse,
    VulnerableAssetsOverviewResponse,
    VulnerabilityItem,
    HardwareLifecycleResponse,
    OSLifecycleResponse,
    SecurityInsightsResponse,
)
from app.services.risk_insights_service import RiskInsightsService

router = APIRouter()


@router.get("/acme-risk-review", response_model=AcmeRiskReviewResponse)
def get_acme_risk_review(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve Lansweeper Acme Risk Review executive telemetry and visual distribution data."""
    return RiskInsightsService.get_acme_risk_review(db)


@router.get("/vulnerable-assets", response_model=VulnerableAssetsOverviewResponse)
def get_vulnerable_assets_overview(
    search: Optional[str] = Query(None, description="Search CVE ID, title, or product"),
    severity: Optional[str] = Query(None, description="Filter by severity: critical, high, medium, low"),
    vendor: Optional[str] = Query(None, description="Filter by vendor: Microsoft, Google, Apple, etc."),
    show_ignored: bool = Query(False, description="Whether to include ignored vulnerabilities"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve Lansweeper Vulnerable Assets overview, CVE tables, and threat telemetry."""
    return RiskInsightsService.get_vulnerable_assets_overview(
        db,
        search=search,
        severity=severity,
        vendor=vendor,
        show_ignored=show_ignored,
    )


@router.post("/vulnerabilities/{cve_id}/ignore", response_model=VulnerabilityItem)
def ignore_vulnerability(
    cve_id: str,
    ignore: bool = Query(True, description="True to ignore, False to restore"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Toggle ignore status for a specific CVE vulnerability."""
    vuln = RiskInsightsService.toggle_ignore_cve(db, cve_id, ignore)
    if not vuln:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vulnerability {cve_id} not found",
        )
    return vuln


@router.get("/hardware-lifecycle", response_model=HardwareLifecycleResponse)
def get_hardware_lifecycle(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve Lansweeper Hardware Lifecycle and Warranty Analytics."""
    return RiskInsightsService.get_hardware_lifecycle(db)


@router.get("/os-lifecycle", response_model=OSLifecycleResponse)
def get_os_lifecycle(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve Lansweeper OS Lifecycle and Windows 11 Readiness Analytics."""
    return RiskInsightsService.get_os_lifecycle(db)


@router.get("/security-insights", response_model=SecurityInsightsResponse)
def get_security_insights(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve Lansweeper Security & Compliance Findings."""
    return RiskInsightsService.get_security_insights(db)

