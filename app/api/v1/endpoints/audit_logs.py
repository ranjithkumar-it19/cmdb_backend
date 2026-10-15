from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.audit import AuditLogResponse
from app.services.audit_service import AuditService
from app.services.auth_service import require_admin
from app.models.user import User

router = APIRouter()


@router.get("", response_model=List[AuditLogResponse])
def list_audit_logs(
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Retrieve security and administrative audit trail logs."""
    logs = AuditService.list_logs(db, limit=limit)
    return [AuditLogResponse.model_validate(l) for l in logs]
