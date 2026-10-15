from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, asc, func
from fastapi import HTTPException, status

from app.models.asset import Asset, AssetIdentifier
from app.models.change_history import AssetChangeEvent
from app.models.software import SoftwareInstallation
from app.models.relationship import AssetRelationship
from app.models.base import utc_now
from app.schemas.asset import AssetCreate, AssetUpdate, PaginatedAssetsResponse, AssetResponse
from app.change_tracking.tracker import ChangeTracker


class AssetService:
    @staticmethod
    def list_assets(
        db: Session,
        query: Optional[str] = None,
        asset_type: Optional[str] = None,
        operating_system: Optional[str] = None,
        status_filter: Optional[str] = None,
        environment: Optional[str] = None,
        location: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = 25,
    ) -> PaginatedAssetsResponse:
        q = db.query(Asset)

        # Full-text / identifier search
        if query:
            clean_q = f"%{query.strip()}%"
            q = q.filter(
                or_(
                    Asset.display_name.ilike(clean_q),
                    Asset.primary_hostname.ilike(clean_q),
                    Asset.primary_ip.ilike(clean_q),
                    Asset.serial_number.ilike(clean_q),
                    Asset.asset_tag.ilike(clean_q),
                    Asset.manufacturer.ilike(clean_q),
                    Asset.model.ilike(clean_q),
                )
            )

        if asset_type:
            q = q.filter(Asset.asset_type == asset_type)
        if operating_system:
            q = q.filter(Asset.operating_system.ilike(f"%{operating_system}%"))
        if status_filter:
            q = q.filter(Asset.status == status_filter)
        if environment:
            q = q.filter(Asset.environment == environment)
        if location:
            q = q.filter(Asset.location.ilike(f"%{location}%"))

        total = q.count()

        # Sorting
        sort_column = getattr(Asset, sort_by, Asset.created_at)
        if sort_order.lower() == "asc":
            q = q.order_by(asc(sort_column))
        else:
            q = q.order_by(desc(sort_column))

        # Pagination
        offset = (page - 1) * page_size
        items = q.offset(offset).limit(page_size).all()
        pages = (total + page_size - 1) // page_size if total > 0 else 1

        return PaginatedAssetsResponse(
            items=[AssetResponse.model_validate(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    @staticmethod
    def get_asset(db: Session, asset_id: str) -> Asset:
        asset = db.query(Asset).filter(Asset.id == asset_id).first()
        if not asset:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Asset with ID '{asset_id}' not found")
        return asset

    @staticmethod
    def create_asset(db: Session, asset_in: AssetCreate, actor: str = "manual") -> Asset:
        now = utc_now()
        asset = Asset(
            **asset_in.model_dump(),
            first_discovered_at=now,
            last_discovered_at=now,
        )
        db.add(asset)
        db.flush()

        # Add initial identifier
        if asset.serial_number:
            ident = AssetIdentifier(
                asset_id=asset.id,
                identifier_type="serial_number",
                identifier_value=asset.serial_number.upper(),
                raw_value=asset.serial_number,
                source="manual",
                confidence=1.0,
                is_primary=True,
            )
            db.add(ident)

        # Log change event
        event = AssetChangeEvent(
            asset_id=asset.id,
            field_name="status",
            old_value=None,
            new_value=asset.status,
            change_source="manual_entry",
            actor_or_process=actor,
            created_at=now,
        )
        db.add(event)
        db.commit()
        db.refresh(asset)
        return asset

    @staticmethod
    def update_asset(db: Session, asset_id: str, asset_in: AssetUpdate, actor: str = "manual") -> Asset:
        asset = AssetService.get_asset(db, asset_id)
        update_data = {k: v for k, v in asset_in.model_dump().items() if v is not None}

        # Track changes and apply updates
        ChangeTracker.detect_and_record_changes(
            db=db,
            existing_asset=asset,
            updated_attributes=update_data,
            change_source="manual_update",
            actor_or_process=actor,
        )

        db.commit()
        db.refresh(asset)
        return asset

    @staticmethod
    def delete_asset(db: Session, asset_id: str) -> None:
        asset = AssetService.get_asset(db, asset_id)
        db.delete(asset)
        db.commit()

    @staticmethod
    def get_asset_history(db: Session, asset_id: str) -> List[AssetChangeEvent]:
        AssetService.get_asset(db, asset_id)
        return (
            db.query(AssetChangeEvent)
            .filter(AssetChangeEvent.asset_id == asset_id)
            .order_by(desc(AssetChangeEvent.created_at))
            .all()
        )

    @staticmethod
    def get_asset_software(db: Session, asset_id: str) -> List[SoftwareInstallation]:
        AssetService.get_asset(db, asset_id)
        return (
            db.query(SoftwareInstallation)
            .filter(SoftwareInstallation.asset_id == asset_id)
            .order_by(SoftwareInstallation.last_seen_at.desc())
            .all()
        )

    @staticmethod
    def get_asset_relationships(db: Session, asset_id: str) -> List[AssetRelationship]:
        AssetService.get_asset(db, asset_id)
        return (
            db.query(AssetRelationship)
            .filter(
                or_(
                    AssetRelationship.source_asset_id == asset_id,
                    AssetRelationship.target_asset_id == asset_id,
                )
            )
            .all()
        )
