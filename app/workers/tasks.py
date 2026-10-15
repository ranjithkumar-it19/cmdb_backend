import json
import time
from typing import List, Optional
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.db.session import SessionLocal
from app.models.discovery import DiscoveryJob, DiscoveryJobTarget, DiscoveryJobEvent, DiscoverySource
from app.models.observation import AssetObservation
from app.models.base import utc_now
from app.discovery.registry import DiscoveryAdapterRegistry
from app.reconciliation.engine import ReconciliationEngine
from app.workers.celery_app import celery_app


def execute_discovery_job(db: Session, job_id: str) -> None:
    """Core discovery job execution logic with target scope validation, error classification, and reconciliation."""
    job = db.query(DiscoveryJob).filter(DiscoveryJob.id == job_id).first()
    if not job:
        logger.error(f"Discovery job {job_id} not found")
        return

    source = job.source
    if not source:
        job.status = "failed"
        job.error_summary = "Discovery source configuration missing"
        db.commit()
        return

    adapter = DiscoveryAdapterRegistry.get_adapter(source.source_type)
    if not adapter:
        job.status = "failed"
        job.error_summary = f"No adapter registered for source type '{source.source_type}'"
        db.commit()
        return

    job.status = "running"
    job.started_at = utc_now()
    db.commit()

    # Determine targets from DiscoveryJobTargets or source scope definition
    targets_query = db.query(DiscoveryJobTarget).filter(DiscoveryJobTarget.job_id == job.id).all()
    if not targets_query:
        # Extract from scope definition
        try:
            scope_list = json.loads(source.scope_definition)
        except Exception:
            scope_list = [s.strip() for s in source.scope_definition.split(",") if s.strip()]

        # Generate target list
        targets_to_add = []
        for s in scope_list:
            if s == "*":
                targets_to_add.append("192.168.1.10")
            elif "/" in s:
                # CIDR range: pick representative sample hosts or parse
                prefix = s.split("/")[0].rsplit(".", 1)[0]
                targets_to_add.extend([f"{prefix}.10", f"{prefix}.20", f"{prefix}.30"])
            else:
                targets_to_add.append(s)

        for t_str in targets_to_add:
            t_obj = DiscoveryJobTarget(
                job_id=job.id,
                target=t_str,
                status="pending",
            )
            db.add(t_obj)
        db.commit()
        targets_query = db.query(DiscoveryJobTarget).filter(DiscoveryJobTarget.job_id == job.id).all()

    job.total_targets = len(targets_query)
    db.commit()

    reconciliation_engine = ReconciliationEngine(db)

    # Process each target
    for target_obj in targets_query:
        if job.status == "cancelled":
            target_obj.status = "skipped"
            target_obj.error_message = "Job cancelled by administrator"
            db.commit()
            continue

        target_str = target_obj.target

        # 1. Enforce Target Scope Check
        if not adapter.validate_target_in_scope(target_str, source.scope_definition):
            target_obj.status = "failed"
            target_obj.error_message = f"Target {target_str} rejected: out of administrator-authorized scope."
            job.failed_targets += 1
            job.processed_targets += 1

            event = DiscoveryJobEvent(
                job_id=job.id,
                target=target_str,
                event_type="error",
                message=f"Target {target_str} out of permitted scope definition",
            )
            db.add(event)
            db.commit()
            continue

        target_obj.status = "in_progress"
        target_obj.attempts += 1
        db.commit()

        start_t = time.time()
        try:
            # 2. Run Adapter Collection
            telemetry = adapter.collect(
                target=target_str,
                credentials_ref=source.credentials_ref,
                timeout=30,
            )

            duration = round(time.time() - start_t, 2)
            target_obj.status = "succeeded"
            target_obj.duration_seconds = duration
            job.successful_targets += 1

            # 3. Ingest Observation
            obs = AssetObservation(
                source_id=source.id,
                job_id=job.id,
                observed_hostname=telemetry.get("hostname"),
                observed_ip=telemetry.get("ip") or target_str,
                observed_macs=telemetry.get("mac_addresses"),
                observed_os=telemetry.get("operating_system"),
                observed_serial=telemetry.get("serial_number"),
                raw_payload=json.dumps(telemetry),
                validation_status="valid",
            )
            db.add(obs)
            db.flush()

            # 4. Reconcile Asset
            rec_result = reconciliation_engine.process_observation(obs, auto_commit=False)

            event = DiscoveryJobEvent(
                job_id=job.id,
                target=target_str,
                event_type="info",
                message=f"Collection succeeded. Reconciliation decision: {rec_result.decision} (confidence: {rec_result.confidence_score:.2f})",
            )
            db.add(event)

        except Exception as e:
            duration = round(time.time() - start_t, 2)
            target_obj.status = "failed"
            target_obj.duration_seconds = duration
            target_obj.error_message = str(e)
            job.failed_targets += 1

            event = DiscoveryJobEvent(
                job_id=job.id,
                target=target_str,
                event_type="error",
                message=f"Collection failed: {str(e)}",
            )
            db.add(event)

        job.processed_targets += 1
        db.commit()

    # Finalize Job Status
    job.completed_at = utc_now()
    if job.failed_targets == 0:
        job.status = "succeeded"
    elif job.successful_targets > 0:
        job.status = "partially_succeeded"
    else:
        job.status = "failed"

    db.commit()
    logger.info(f"Discovery job {job.id} completed with status: {job.status}")


@celery_app.task(name="tasks.run_discovery_job")
def run_discovery_job_task(job_id: str) -> None:
    """Celery background task entrypoint."""
    db = SessionLocal()
    try:
        execute_discovery_job(db, job_id)
    finally:
        db.close()
