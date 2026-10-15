from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.software import SoftwareProduct, SoftwareInstallation
from app.schemas.software import SoftwareProductResponse, SoftwareInstallationResponse


class SoftwareService:
    @staticmethod
    def list_products(db: Session, query: Optional[str] = None) -> List[SoftwareProductResponse]:
        q = db.query(
            SoftwareProduct,
            func.count(SoftwareInstallation.id).label("install_count")
        ).outerjoin(SoftwareInstallation, SoftwareProduct.id == SoftwareInstallation.product_id)

        if query:
            q = q.filter(
                (SoftwareProduct.name.ilike(f"%{query}%")) |
                (SoftwareProduct.publisher.ilike(f"%{query}%"))
            )

        q = q.group_by(SoftwareProduct.id).order_by(func.count(SoftwareInstallation.id).desc())
        results = q.all()

        output = []
        for prod, count in results:
            resp = SoftwareProductResponse(
                id=prod.id,
                name=prod.name,
                normalized_name=prod.normalized_name,
                publisher=prod.publisher,
                category=prod.category,
                created_at=prod.created_at,
                installations_count=count,
            )
            output.append(resp)
        return output

    @staticmethod
    def list_installations(db: Session, product_id: str) -> List[SoftwareInstallationResponse]:
        installations = (
            db.query(SoftwareInstallation)
            .filter(SoftwareInstallation.product_id == product_id)
            .all()
        )
        return [
            SoftwareInstallationResponse(
                id=inst.id,
                asset_id=inst.asset_id,
                asset_display_name=inst.asset.display_name if inst.asset else "Unknown",
                product_id=inst.product_id,
                product_name=inst.product.name if inst.product else "Unknown",
                publisher=inst.product.publisher if inst.product else None,
                version=inst.version,
                architecture=inst.architecture,
                install_date=inst.install_date,
                source=inst.source,
                last_seen_at=inst.last_seen_at,
            )
            for inst in installations
        ]
