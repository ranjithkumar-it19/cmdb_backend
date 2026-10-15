from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.asset import Asset
from app.schemas.business_service import (
    BusinessServiceCreate,
    BusinessServiceUpdate,
    BusinessServiceResponse,
    BusinessServiceAssetLink,
    BusinessServiceAssetResponse,
)
from app.services.business_service_service import BusinessServiceService
from app.services.auth_service import get_current_user
from app.services.audit_service import AuditService
from app.models.user import User

router = APIRouter()


@router.get("", response_model=List[BusinessServiceResponse])
def list_services(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all business services."""
    return BusinessServiceService.list_services(db)


@router.post("", response_model=BusinessServiceResponse, status_code=status.HTTP_201_CREATED)
def create_service(
    data: BusinessServiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new business service."""
    svc = BusinessServiceService.create_service(db, data)
    AuditService.log_event(
        db=db, action="create_business_service", resource_type="business_service",
        resource_id=svc.id, user=current_user,
        details={"name": svc.name, "criticality": svc.criticality},
    )
    return BusinessServiceResponse(
        id=svc.id, name=svc.name, description=svc.description,
        criticality=svc.criticality, sla_tier=svc.sla_tier, environment=svc.environment,
        owner=svc.owner, team=svc.team, contact_email=svc.contact_email,
        status=svc.status, asset_count=0,
        created_at=svc.created_at.isoformat(), updated_at=svc.updated_at.isoformat(),
    )


@router.get("/{service_id}", response_model=BusinessServiceResponse)
def get_service(
    service_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve a single business service."""
    svc = BusinessServiceService.get_service(db, service_id)
    return BusinessServiceResponse(
        id=svc.id, name=svc.name, description=svc.description,
        criticality=svc.criticality, sla_tier=svc.sla_tier, environment=svc.environment,
        owner=svc.owner, team=svc.team, contact_email=svc.contact_email,
        status=svc.status, asset_count=len(svc.asset_links),
        created_at=svc.created_at.isoformat(), updated_at=svc.updated_at.isoformat(),
    )


@router.patch("/{service_id}", response_model=BusinessServiceResponse)
def update_service(
    service_id: str,
    data: BusinessServiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a business service."""
    svc = BusinessServiceService.update_service(db, service_id, data)
    AuditService.log_event(
        db=db, action="update_business_service", resource_type="business_service",
        resource_id=svc.id, user=current_user,
        details={"updated_fields": list(data.model_dump(exclude_unset=True).keys())},
    )
    return BusinessServiceResponse(
        id=svc.id, name=svc.name, description=svc.description,
        criticality=svc.criticality, sla_tier=svc.sla_tier, environment=svc.environment,
        owner=svc.owner, team=svc.team, contact_email=svc.contact_email,
        status=svc.status, asset_count=len(svc.asset_links),
        created_at=svc.created_at.isoformat(), updated_at=svc.updated_at.isoformat(),
    )


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_service(
    service_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a business service."""
    BusinessServiceService.delete_service(db, service_id)
    AuditService.log_event(
        db=db, action="delete_business_service", resource_type="business_service",
        resource_id=service_id, user=current_user,
    )


@router.get("/{service_id}/assets", response_model=List[BusinessServiceAssetResponse])
def get_service_assets(
    service_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List assets linked to a business service."""
    return BusinessServiceService.get_service_assets(db, service_id)


@router.post("/{service_id}/assets", response_model=BusinessServiceAssetResponse, status_code=status.HTTP_201_CREATED)
def link_asset(
    service_id: str,
    link: BusinessServiceAssetLink,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Link an asset to a business service."""
    bsa = BusinessServiceService.link_asset(db, service_id, link)
    asset = db.query(Asset).filter_by(id=bsa.asset_id).first()
    return BusinessServiceAssetResponse(
        id=bsa.id, asset_id=bsa.asset_id, role=bsa.role, is_primary=bsa.is_primary,
        asset_display_name=asset.display_name if asset else None,
        asset_type=asset.asset_type if asset else None,
        asset_status=asset.status if asset else None,
    )


@router.delete("/{service_id}/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def unlink_asset(
    service_id: str,
    asset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove an asset from a business service."""
    BusinessServiceService.unlink_asset(db, service_id, asset_id)
