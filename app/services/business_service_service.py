from typing import List
from sqlalchemy.orm import Session

from app.models.business_service import BusinessService, BusinessServiceAsset
from app.models.asset import Asset
from app.schemas.business_service import (
    BusinessServiceCreate,
    BusinessServiceUpdate,
    BusinessServiceAssetLink,
    BusinessServiceResponse,
    BusinessServiceAssetResponse,
)


class BusinessServiceService:

    @staticmethod
    def list_services(db: Session) -> List[BusinessServiceResponse]:
        services = db.query(BusinessService).order_by(BusinessService.name).all()
        result = []
        for svc in services:
            result.append(BusinessServiceResponse(
                id=svc.id,
                name=svc.name,
                description=svc.description,
                criticality=svc.criticality,
                sla_tier=svc.sla_tier,
                environment=svc.environment,
                owner=svc.owner,
                team=svc.team,
                contact_email=svc.contact_email,
                status=svc.status,
                asset_count=len(svc.asset_links),
                created_at=svc.created_at.isoformat(),
                updated_at=svc.updated_at.isoformat(),
            ))
        return result

    @staticmethod
    def get_service(db: Session, service_id: str) -> BusinessService:
        svc = db.query(BusinessService).filter(BusinessService.id == service_id).first()
        if not svc:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Business service not found")
        return svc

    @staticmethod
    def create_service(db: Session, data: BusinessServiceCreate) -> BusinessService:
        svc = BusinessService(**data.model_dump())
        db.add(svc)
        db.commit()
        db.refresh(svc)
        return svc

    @staticmethod
    def update_service(db: Session, service_id: str, data: BusinessServiceUpdate) -> BusinessService:
        svc = BusinessServiceService.get_service(db, service_id)
        update_data = data.model_dump(exclude_unset=True)
        for key, val in update_data.items():
            setattr(svc, key, val)
        db.commit()
        db.refresh(svc)
        return svc

    @staticmethod
    def delete_service(db: Session, service_id: str) -> None:
        svc = BusinessServiceService.get_service(db, service_id)
        db.delete(svc)
        db.commit()

    @staticmethod
    def link_asset(db: Session, service_id: str, link: BusinessServiceAssetLink) -> BusinessServiceAsset:
        # Ensure service and asset both exist
        BusinessServiceService.get_service(db, service_id)
        asset = db.query(Asset).filter(Asset.id == link.asset_id).first()
        if not asset:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Asset not found")

        # Check for duplicates
        existing = db.query(BusinessServiceAsset).filter(
            BusinessServiceAsset.service_id == service_id,
            BusinessServiceAsset.asset_id == link.asset_id,
        ).first()
        if existing:
            existing.role = link.role
            existing.is_primary = link.is_primary
            db.commit()
            db.refresh(existing)
            return existing

        bsa = BusinessServiceAsset(
            service_id=service_id,
            asset_id=link.asset_id,
            role=link.role,
            is_primary=link.is_primary,
        )
        db.add(bsa)
        db.commit()
        db.refresh(bsa)
        return bsa

    @staticmethod
    def unlink_asset(db: Session, service_id: str, asset_id: str) -> None:
        link = db.query(BusinessServiceAsset).filter(
            BusinessServiceAsset.service_id == service_id,
            BusinessServiceAsset.asset_id == asset_id,
        ).first()
        if link:
            db.delete(link)
            db.commit()

    @staticmethod
    def get_service_assets(db: Session, service_id: str) -> List[BusinessServiceAssetResponse]:
        svc = BusinessServiceService.get_service(db, service_id)
        results = []
        for link in svc.asset_links:
            asset = db.query(Asset).filter(Asset.id == link.asset_id).first()
            results.append(BusinessServiceAssetResponse(
                id=link.id,
                asset_id=link.asset_id,
                role=link.role,
                is_primary=link.is_primary,
                asset_display_name=asset.display_name if asset else None,
                asset_type=asset.asset_type if asset else None,
                asset_status=asset.status if asset else None,
            ))
        return results
