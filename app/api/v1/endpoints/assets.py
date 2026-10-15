from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.asset import (
    AssetCreate,
    AssetUpdate,
    AssetResponse,
    AssetDetailResponse,
    PaginatedAssetsResponse,
    AssetChangeEventSchema,
)
from app.schemas.software import SoftwareInstallationResponse
from app.schemas.relationship import RelationshipResponse
from app.services.asset_service import AssetService
from app.services.auth_service import get_current_user
from app.services.audit_service import AuditService
from app.discovery.csv_importer import CsvImporter
from app.models.user import User

router = APIRouter()


@router.get("", response_model=PaginatedAssetsResponse)
def list_assets(
    q: Optional[str] = Query(None, description="Search term for hostname, IP, serial, asset tag"),
    asset_type: Optional[str] = Query(None, description="Filter by asset type"),
    operating_system: Optional[str] = Query(None, description="Filter by OS"),
    status: Optional[str] = Query(None, description="Filter by status (active, offline, etc.)"),
    environment: Optional[str] = Query(None, description="Filter by environment"),
    location: Optional[str] = Query(None, description="Filter by location"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", description="Sort direction (asc/desc)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(25, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List assets with full-text search, filtering, sorting, and pagination."""
    return AssetService.list_assets(
        db=db,
        query=q,
        asset_type=asset_type,
        operating_system=operating_system,
        status_filter=status,
        environment=environment,
        location=location,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )


@router.get("/export")
def export_assets_to_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export authorized asset inventory to CSV with formula injection defense."""
    paginated = AssetService.list_assets(db=db, page=1, page_size=10000)
    # Fetch Asset objects
    asset_ids = [item.id for item in paginated.items]
    from app.models.asset import Asset
    assets = db.query(Asset).filter(Asset.id.in_(asset_ids)).all() if asset_ids else []
    csv_data = CsvImporter.export_assets_csv(assets)

    AuditService.log_event(
        db=db,
        action="export_assets_csv",
        resource_type="asset",
        user=current_user,
        details={"exported_count": len(assets)},
    )

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=atlas_inventory_export.csv"},
    )


@router.post("", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
def create_asset(
    asset_in: AssetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Manually register an asset into inventory."""
    asset = AssetService.create_asset(db, asset_in, actor=current_user.email)
    AuditService.log_event(
        db=db,
        action="create_asset",
        resource_type="asset",
        resource_id=asset.id,
        user=current_user,
        details={"display_name": asset.display_name},
    )
    return asset


@router.get("/{asset_id}", response_model=AssetDetailResponse)
def get_asset_detail(
    asset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get full details of a specific asset including change history."""
    asset = AssetService.get_asset(db, asset_id)
    history = AssetService.get_asset_history(db, asset_id)
    resp = AssetDetailResponse.model_validate(asset)
    resp.change_events = [AssetChangeEventSchema.model_validate(h) for h in history]
    return resp


@router.patch("/{asset_id}", response_model=AssetResponse)
def update_asset(
    asset_id: str,
    asset_in: AssetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update asset attributes with automatic change detection."""
    asset = AssetService.update_asset(db, asset_id, asset_in, actor=current_user.email)
    AuditService.log_event(
        db=db,
        action="update_asset",
        resource_type="asset",
        resource_id=asset.id,
        user=current_user,
    )
    return asset


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_asset(
    asset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an asset record and audit the deletion."""
    AssetService.delete_asset(db, asset_id)
    AuditService.log_event(
        db=db,
        action="delete_asset",
        resource_type="asset",
        resource_id=asset_id,
        user=current_user,
    )
    return None


@router.get("/{asset_id}/history", response_model=List[AssetChangeEventSchema])
def get_asset_history(
    asset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve historical attribute modifications for an asset."""
    events = AssetService.get_asset_history(db, asset_id)
    return [AssetChangeEventSchema.model_validate(e) for e in events]


@router.get("/{asset_id}/software", response_model=List[SoftwareInstallationResponse])
def get_asset_software(
    asset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve installed software products on an asset."""
    installations = AssetService.get_asset_software(db, asset_id)
    return [
        SoftwareInstallationResponse(
            id=i.id,
            asset_id=i.asset_id,
            asset_display_name=i.asset.display_name if i.asset else None,
            product_id=i.product_id,
            product_name=i.product.name if i.product else None,
            publisher=i.product.publisher if i.product else None,
            version=i.version,
            architecture=i.architecture,
            install_date=i.install_date,
            source=i.source,
            last_seen_at=i.last_seen_at,
        )
        for i in installations
    ]


@router.get("/{asset_id}/relationships", response_model=List[RelationshipResponse])
def get_asset_relationships(
    asset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve relationships involving an asset."""
    rels = AssetService.get_asset_relationships(db, asset_id)
    return [RelationshipResponse.model_validate(r) for r in rels]
