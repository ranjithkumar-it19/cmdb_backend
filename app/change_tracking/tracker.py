from typing import Any, Dict, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.asset import Asset
from app.models.change_history import AssetChangeEvent
from app.models.base import utc_now


TRACKED_FIELDS = [
    "primary_hostname",
    "primary_ip",
    "mac_addresses",
    "operating_system",
    "operating_system_version",
    "manufacturer",
    "model",
    "serial_number",
    "cpu_info",
    "memory_gb",
    "storage_gb",
    "domain_or_workgroup",
    "environment",
    "status",
    "location",
    "owner",
]


class ChangeTracker:
    """Detects and persists state changes between observations and existing canonical assets."""

    @staticmethod
    def detect_and_record_changes(
        db: Session,
        existing_asset: Asset,
        updated_attributes: Dict[str, Any],
        change_source: str = "discovery",
        actor_or_process: str = "system",
        observation_id: Optional[str] = None,
    ) -> List[AssetChangeEvent]:
        """Compare attributes and record AssetChangeEvent records for any modified field."""
        events: List[AssetChangeEvent] = []
        now = utc_now()

        for field in TRACKED_FIELDS:
            if field in updated_attributes:
                new_val = updated_attributes[field]
                old_val = getattr(existing_asset, field, None)

                # Normalize to strings for clean comparison
                old_str = str(old_val) if old_val is not None else None
                new_str = str(new_val) if new_val is not None else None

                # Disregard empty-to-empty or no change
                if old_str == new_str:
                    continue

                # If new value is None and old value existed, do not overwrite unless explicitly desired
                if new_str is None and old_str is not None:
                    continue

                # Create change event
                event = AssetChangeEvent(
                    asset_id=existing_asset.id,
                    field_name=field,
                    old_value=old_str,
                    new_value=new_str,
                    change_source=change_source,
                    actor_or_process=actor_or_process,
                    observation_id=observation_id,
                    created_at=now,
                )
                db.add(event)
                events.append(event)

                # Update the asset field
                setattr(existing_asset, field, new_val)

        return events
