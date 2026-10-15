from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.integration import (
    IntegrationConfigCreate,
    IntegrationConfigUpdate,
    IntegrationConfigResponse,
    IntegrationSyncLogResponse,
)
from app.integrations.servicenow import ServiceNowConnector
from app.services.auth_service import get_current_user
from app.services.audit_service import AuditService
from app.models.user import User

router = APIRouter()


def _cfg_to_response(cfg) -> IntegrationConfigResponse:
    return IntegrationConfigResponse(
        id=cfg.id, name=cfg.name, integration_type=cfg.integration_type,
        instance_url=cfg.instance_url, auth_type=cfg.auth_type,
        username=cfg.username, is_active=cfg.is_active,
        sync_direction=cfg.sync_direction,
        last_sync_at=cfg.last_sync_at.isoformat() if cfg.last_sync_at else None,
        last_sync_status=cfg.last_sync_status,
        sync_stats=cfg.sync_stats,
        created_at=cfg.created_at.isoformat(),
        updated_at=cfg.updated_at.isoformat(),
    )


def _log_to_response(log) -> IntegrationSyncLogResponse:
    return IntegrationSyncLogResponse(
        id=log.id, config_id=log.config_id, direction=log.direction,
        status=log.status, records_pushed=log.records_pushed,
        records_pulled=log.records_pulled, errors_count=log.errors_count,
        error_details=log.error_details,
        started_at=log.started_at.isoformat(),
        completed_at=log.completed_at.isoformat() if log.completed_at else None,
    )


@router.get("", response_model=List[IntegrationConfigResponse])
def list_integrations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all integration configs."""
    return [_cfg_to_response(c) for c in ServiceNowConnector.list_configs(db)]


@router.post("", response_model=IntegrationConfigResponse, status_code=status.HTTP_201_CREATED)
def create_integration(
    data: IntegrationConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new integration config."""
    cfg = ServiceNowConnector.create_config(db, data.model_dump())
    AuditService.log_event(
        db=db, action="create_integration", resource_type="integration",
        resource_id=cfg.id, user=current_user,
        details={"name": cfg.name, "type": cfg.integration_type},
    )
    return _cfg_to_response(cfg)


@router.get("/{config_id}", response_model=IntegrationConfigResponse)
def get_integration(
    config_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cfg = ServiceNowConnector.get_config(db, config_id)
    return _cfg_to_response(cfg)


@router.patch("/{config_id}", response_model=IntegrationConfigResponse)
def update_integration(
    config_id: str,
    data: IntegrationConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cfg = ServiceNowConnector.update_config(db, config_id, data.model_dump(exclude_unset=True))
    return _cfg_to_response(cfg)


@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_integration(
    config_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ServiceNowConnector.delete_config(db, config_id)


@router.post("/{config_id}/sync/push", response_model=IntegrationSyncLogResponse)
def push_sync(
    config_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Push assets to external ITSM system."""
    log = ServiceNowConnector.simulate_push_sync(db, config_id)
    AuditService.log_event(
        db=db, action="integration_push_sync", resource_type="integration",
        resource_id=config_id, user=current_user,
        details={"pushed": log.records_pushed, "errors": log.errors_count},
    )
    return _log_to_response(log)


@router.post("/{config_id}/sync/pull", response_model=IntegrationSyncLogResponse)
def pull_sync(
    config_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Pull CIs from external ITSM system."""
    log = ServiceNowConnector.simulate_pull_sync(db, config_id)
    return _log_to_response(log)


@router.get("/{config_id}/logs", response_model=List[IntegrationSyncLogResponse])
def get_sync_logs(
    config_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get sync logs for an integration."""
    logs = ServiceNowConnector.get_sync_logs(db, config_id)
    return [_log_to_response(l) for l in logs]
