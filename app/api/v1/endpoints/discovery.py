from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.discovery import (
    DiscoverySourceCreate,
    DiscoverySourceResponse,
    DiscoveryJobCreate,
    DiscoveryJobResponse,
    DiscoveryJobEventResponse,
)
from app.services.discovery_service import DiscoveryService
from app.services.auth_service import get_current_user
from app.services.audit_service import AuditService
from app.models.user import User

router = APIRouter()


@router.get("/sources", response_model=List[DiscoverySourceResponse])
def list_discovery_sources(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List configured discovery sources."""
    return DiscoveryService.list_sources(db)


@router.post("/sources", response_model=DiscoverySourceResponse, status_code=status.HTTP_201_CREATED)
def create_discovery_source(
    source_in: DiscoverySourceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Configure a new discovery source with authorized scope definition."""
    source = DiscoveryService.create_source(db, source_in)
    AuditService.log_event(
        db=db,
        action="create_discovery_source",
        resource_type="discovery_source",
        resource_id=source.id,
        user=current_user,
        details={"name": source.name, "type": source.source_type},
    )
    return source


@router.get("/jobs", response_model=List[DiscoveryJobResponse])
def list_discovery_jobs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List recent discovery jobs and execution statuses."""
    jobs = DiscoveryService.list_jobs(db)
    return [DiscoveryJobResponse.model_validate(j) for j in jobs]


@router.post("/jobs", response_model=DiscoveryJobResponse, status_code=status.HTTP_201_CREATED)
def create_discovery_job(
    job_in: DiscoveryJobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trigger an asynchronous discovery job."""
    job = DiscoveryService.create_job(db, job_in, user_id=current_user.id)
    AuditService.log_event(
        db=db,
        action="launch_discovery_job",
        resource_type="discovery_job",
        resource_id=job.id,
        user=current_user,
        details={"source_id": job.source_id},
    )
    return DiscoveryJobResponse.model_validate(job)


@router.get("/jobs/{job_id}", response_model=DiscoveryJobResponse)
def get_discovery_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get live status and progress of a discovery job."""
    job = DiscoveryService.get_job(db, job_id)
    return DiscoveryJobResponse.model_validate(job)


@router.post("/jobs/{job_id}/cancel", response_model=DiscoveryJobResponse)
def cancel_discovery_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancel an active or queued discovery job."""
    job = DiscoveryService.cancel_job(db, job_id)
    AuditService.log_event(
        db=db,
        action="cancel_discovery_job",
        resource_type="discovery_job",
        resource_id=job.id,
        user=current_user,
    )
    return DiscoveryJobResponse.model_validate(job)


@router.get("/jobs/{job_id}/events", response_model=List[DiscoveryJobEventResponse])
def get_discovery_job_events(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve execution log events for a discovery job."""
    events = DiscoveryService.get_job_events(db, job_id)
    return [DiscoveryJobEventResponse.model_validate(e) for e in events]
