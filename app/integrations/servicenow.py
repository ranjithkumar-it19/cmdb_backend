"""
ServiceNow CMDB Integration Connector (Simulated).

In production this would use the ServiceNow Table API to push/pull CIs.
For this sandbox, we simulate the sync operations with realistic responses.
"""
import json
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.integrations.models import IntegrationConfig, IntegrationSyncLog
from app.models.asset import Asset


# ServiceNow CI Table mappings
ASSET_TYPE_TO_SN_TABLE = {
    "server": "cmdb_ci_server",
    "virtual_machine": "cmdb_ci_server",
    "workstation": "cmdb_ci_computer",
    "network_device": "cmdb_ci_netgear",
    "printer": "cmdb_ci_printer",
    "unknown": "cmdb_ci",
}


def map_asset_to_servicenow_ci(asset: Asset) -> Dict[str, Any]:
    """Map an Atlas asset to a ServiceNow CI payload."""
    return {
        "name": asset.display_name,
        "asset_tag": asset.asset_tag or "",
        "serial_number": asset.serial_number or "",
        "ip_address": asset.primary_ip or "",
        "manufacturer": asset.manufacturer or "",
        "model_id": asset.model or "",
        "os": asset.operating_system or "",
        "os_version": asset.operating_system_version or "",
        "cpu_type": asset.cpu_info or "",
        "ram": int(asset.memory_gb) if asset.memory_gb else 0,
        "disk_space": int(asset.storage_gb) if asset.storage_gb else 0,
        "install_status": "1" if asset.status == "active" else "7",
        "dns_domain": asset.domain_or_workgroup or "",
        "location": asset.location or "",
        "u_atlas_id": asset.id,
    }


class ServiceNowConnector:

    @staticmethod
    def list_configs(db: Session) -> List[IntegrationConfig]:
        return db.query(IntegrationConfig).order_by(IntegrationConfig.name).all()

    @staticmethod
    def get_config(db: Session, config_id: str) -> IntegrationConfig:
        cfg = db.query(IntegrationConfig).filter(IntegrationConfig.id == config_id).first()
        if not cfg:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Integration config not found")
        return cfg

    @staticmethod
    def create_config(db: Session, data: dict) -> IntegrationConfig:
        cfg = IntegrationConfig(**data)
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
        return cfg

    @staticmethod
    def update_config(db: Session, config_id: str, data: dict) -> IntegrationConfig:
        cfg = ServiceNowConnector.get_config(db, config_id)
        for key, val in data.items():
            if val is not None:
                setattr(cfg, key, val)
        db.commit()
        db.refresh(cfg)
        return cfg

    @staticmethod
    def delete_config(db: Session, config_id: str) -> None:
        cfg = ServiceNowConnector.get_config(db, config_id)
        db.delete(cfg)
        db.commit()

    @staticmethod
    def simulate_push_sync(db: Session, config_id: str) -> IntegrationSyncLog:
        """Simulate pushing assets to ServiceNow. In production, this would call the SN Table API."""
        cfg = ServiceNowConnector.get_config(db, config_id)
        assets = db.query(Asset).filter(Asset.status == "active").all()

        pushed = 0
        errors = 0
        error_details = []

        for asset in assets:
            try:
                ci_payload = map_asset_to_servicenow_ci(asset)
                # In production: requests.post(f"{cfg.instance_url}/api/now/table/{table}", json=ci_payload, ...)
                sn_table = ASSET_TYPE_TO_SN_TABLE.get(asset.asset_type, "cmdb_ci")
                pushed += 1
            except Exception as e:
                errors += 1
                error_details.append(f"Asset {asset.id}: {str(e)}")

        now = datetime.now(timezone.utc)
        sync_log = IntegrationSyncLog(
            config_id=config_id,
            direction="push",
            status="success" if errors == 0 else ("partial" if pushed > 0 else "failed"),
            records_pushed=pushed,
            records_pulled=0,
            errors_count=errors,
            error_details=json.dumps(error_details) if error_details else None,
            started_at=now,
            completed_at=now,
        )
        db.add(sync_log)

        cfg.last_sync_at = now
        cfg.last_sync_status = sync_log.status
        cfg.sync_stats = json.dumps({"pushed": pushed, "pulled": 0, "errors": errors})
        db.commit()
        db.refresh(sync_log)
        return sync_log

    @staticmethod
    def simulate_pull_sync(db: Session, config_id: str) -> IntegrationSyncLog:
        """Simulate pulling CIs from ServiceNow. In production, this reads from the SN Table API."""
        cfg = ServiceNowConnector.get_config(db, config_id)
        now = datetime.now(timezone.utc)

        # Simulate pulling 0 new records (no real SN instance)
        sync_log = IntegrationSyncLog(
            config_id=config_id,
            direction="pull",
            status="success",
            records_pushed=0,
            records_pulled=0,
            errors_count=0,
            started_at=now,
            completed_at=now,
        )
        db.add(sync_log)
        cfg.last_sync_at = now
        cfg.last_sync_status = "success"
        db.commit()
        db.refresh(sync_log)
        return sync_log

    @staticmethod
    def get_sync_logs(db: Session, config_id: str = None, limit: int = 50) -> List[IntegrationSyncLog]:
        q = db.query(IntegrationSyncLog)
        if config_id:
            q = q.filter(IntegrationSyncLog.config_id == config_id)
        return q.order_by(IntegrationSyncLog.started_at.desc()).limit(limit).all()
