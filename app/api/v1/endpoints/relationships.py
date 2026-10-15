from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.relationship import (
    RelationshipCreate,
    RelationshipResponse,
    RelationshipGraphResponse,
)
from app.services.relationship_service import RelationshipService
from app.services.auth_service import get_current_user
from app.services.audit_service import AuditService
from app.models.user import User

router = APIRouter()


@router.get("", response_model=List[RelationshipResponse])
def list_relationships(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List active asset relationships."""
    return RelationshipService.list_relationships(db)


@router.post("", response_model=RelationshipResponse, status_code=status.HTTP_201_CREATED)
def create_relationship(
    rel_in: RelationshipCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a typed relationship between two assets."""
    rel = RelationshipService.create_relationship(db, rel_in, source=current_user.email)
    AuditService.log_event(
        db=db,
        action="create_relationship",
        resource_type="asset_relationship",
        resource_id=rel.id,
        user=current_user,
        details={
            "source_id": rel.source_asset_id,
            "target_id": rel.target_asset_id,
            "type": rel.relationship_type,
        },
    )
    return rel


@router.get("/graph", response_model=RelationshipGraphResponse)
def get_relationship_graph(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve nodes and edges for CMDB topological visualization."""
    return RelationshipService.get_relationship_graph(db)


@router.post("/infer")
def infer_topology(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Run automated topology inference algorithm across current assets."""
    inferred_count = RelationshipService.infer_topology(db)
    AuditService.log_event(
        db=db,
        action="infer_topology",
        resource_type="topology",
        user=current_user,
        details={"inferred_relationships_count": inferred_count},
    )
    return {"message": f"Inferred {inferred_count} new infrastructure relationships", "count": inferred_count}

