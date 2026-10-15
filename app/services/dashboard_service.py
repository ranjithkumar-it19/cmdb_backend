from typing import Any, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.asset import Asset
from app.models.software import SoftwareProduct, SoftwareInstallation
from app.models.discovery import DiscoveryJob
from app.models.change_history import AssetChangeEvent
from app.models.audit import AuditLog
from app.schemas.dashboard import DashboardSummaryResponse


class DashboardService:
    @staticmethod
    def get_summary(db: Session) -> DashboardSummaryResponse:
        total_assets = db.query(Asset).count()
        active_assets = db.query(Asset).filter(Asset.status == "active").count()
        offline_assets = db.query(Asset).filter(Asset.status == "offline").count()

        # Asset types distribution
        type_rows = (
            db.query(Asset.asset_type, func.count(Asset.id))
            .group_by(Asset.asset_type)
            .all()
        )
        asset_types = {t or "unknown": c for t, c in type_rows}

        # OS distribution
        os_rows = (
            db.query(Asset.operating_system, func.count(Asset.id))
            .filter(Asset.operating_system.isnot(None))
            .group_by(Asset.operating_system)
            .limit(10)
            .all()
        )
        os_dist = {o: c for o, c in os_rows}

        total_sw_products = db.query(SoftwareProduct).count()
        total_sw_installs = db.query(SoftwareInstallation).count()

        total_jobs = db.query(DiscoveryJob).count()
        recent_jobs = db.query(DiscoveryJob).filter(DiscoveryJob.status.in_(["running", "succeeded", "partially_succeeded"])).count()
        failed_jobs = db.query(DiscoveryJob).filter(DiscoveryJob.status == "failed").count()

        recent_changes_count = db.query(AssetChangeEvent).count()

        # Recent activities from AuditLog and ChangeEvents
        recent_changes = (
            db.query(AssetChangeEvent)
            .order_by(AssetChangeEvent.created_at.desc())
            .limit(5)
            .all()
        )
        activities = [
            {
                "type": "asset_change",
                "title": f"Asset {c.field_name} updated",
                "detail": f"{c.old_value or 'None'} -> {c.new_value}",
                "timestamp": c.created_at.isoformat(),
                "actor": c.actor_or_process,
            }
            for c in recent_changes
        ]

        return DashboardSummaryResponse(
            total_assets=total_assets,
            active_assets=active_assets,
            offline_assets=offline_assets,
            asset_types_distribution=asset_types,
            operating_systems_distribution=os_dist,
            total_software_products=total_sw_products,
            total_software_installations=total_sw_installs,
            total_discovery_jobs=total_jobs,
            recent_jobs_count=recent_jobs,
            failed_jobs_count=failed_jobs,
            recent_changes_count=recent_changes_count,
            recent_activities=activities,
        )
