from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.software import SoftwareProductResponse, SoftwareInstallationResponse
from app.services.software_service import SoftwareService
from app.services.auth_service import get_current_user
from app.models.user import User

router = APIRouter()


@router.get("", response_model=List[SoftwareProductResponse])
def list_software_products(
    q: Optional[str] = Query(None, description="Search software name or publisher"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List discovered software products and total installation count."""
    return SoftwareService.list_products(db, query=q)


@router.get("/{product_id}/installations", response_model=List[SoftwareInstallationResponse])
def list_product_installations(
    product_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List assets on which this software product is installed."""
    return SoftwareService.list_installations(db, product_id)
