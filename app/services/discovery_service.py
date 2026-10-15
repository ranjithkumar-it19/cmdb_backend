import json
import threading
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.discovery import DiscoverySource, DiscoveryJob, DiscoveryJobTarget, DiscoveryJobEvent
from app.schemas.discovery import DiscoverySourceCreate, DiscoveryJobCreate
from app.workers.tasks import run_discovery_job_task, execute_discovery_job
from app.core.logging import logger


class DiscoveryService:
    @staticmethod
    def list_sources(db: Session) -> List[DiscoverySource]:
        return db.query(DiscoverySource).all()

    @staticmethod
    def create_source(db: Session, source_in: DiscoverySourceCreate) -> DiscoverySource:
        source = DiscoverySource(**source_in.model_dump())
        db.add(source)
        db.commit()
        db.refresh(source)
        return source

    @staticmethod
    def list_jobs(db: Session, limit: int = 50) -> List[DiscoveryJob]:
        return db.query(DiscoveryJob).order_by(DiscoveryJob.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_job(db: Session, job_id: str) -> DiscoveryJob:
        job = db.query(DiscoveryJob).filter(DiscoveryJob.id == job_id).first()
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discovery job not found")
        return job

    @staticmethod
    def create_job(db: Session, job_in: DiscoveryJobCreate, user_id: Optional[str] = None) -> DiscoveryJob:
        source = db.query(DiscoverySource).filter(DiscoverySource.id == job_in.source_id).first()
        if not source:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discovery source not found")
        if not source.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Discovery source is disabled")

        job = DiscoveryJob(
            source_id=source.id,
            status="queued",
            initiated_by_user_id=user_id,
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        # Prepopulate targets if explicitly supplied
        if job_in.targets:
            for t_str in job_in.targets:
                target_obj = DiscoveryJobTarget(
                    job_id=job.id,
                    target=t_str.strip(),
                    status="pending",
                )
                db.add(target_obj)
            job.total_targets = len(job_in.targets)
            db.commit()

        from app.core.config import settings

        # Dispatch execution: Celery worker queue or local background worker thread
        if settings.USE_CELERY:
            try:
                run_discovery_job_task.delay(job.id)
                logger.info(f"Discovery job {job.id} dispatched to Celery worker queue")
                return job
            except Exception as e:
                logger.warning(f"Celery queue unavailable ({e}). Spawning asynchronous background worker thread.")

        worker_thread = threading.Thread(
            target=execute_discovery_job_in_thread,
            args=(job.id,),
            daemon=True,
        )
        worker_thread.start()

        return job

    @staticmethod
    def cancel_job(db: Session, job_id: str) -> DiscoveryJob:
        job = DiscoveryService.get_job(db, job_id)
        if job.status in ("queued", "running"):
            job.status = "cancelled"
            job.error_summary = "Cancelled by user"
            db.commit()
        return job

    @staticmethod
    def get_job_events(db: Session, job_id: str) -> List[DiscoveryJobEvent]:
        DiscoveryService.get_job(db, job_id)
        return (
            db.query(DiscoveryJobEvent)
            .filter(DiscoveryJobEvent.job_id == job_id)
            .order_by(DiscoveryJobEvent.timestamp.asc())
            .all()
        )


def execute_discovery_job_in_thread(job_id: str) -> None:
    from app.db.session import SessionLocal
    db = SessionLocal()
    try:
        execute_discovery_job(db, job_id)
    finally:
        db.close()
