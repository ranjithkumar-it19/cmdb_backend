from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth,
    assets,
    discovery,
    imports,
    relationships,
    software,
    dashboard,
    audit_logs,
    health,
    business_services,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(assets.router, prefix="/assets", tags=["Asset Inventory"])
api_router.include_router(discovery.router, prefix="/discovery", tags=["Discovery Engine"])
api_router.include_router(imports.router, prefix="/imports", tags=["CSV Import & Ingestion"])
api_router.include_router(relationships.router, prefix="/relationships", tags=["CMDB Relationships"])
api_router.include_router(software.router, prefix="/software", tags=["Software Inventory"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard & Metrics"])
api_router.include_router(audit_logs.router, prefix="/audit-logs", tags=["Audit Trail"])
api_router.include_router(health.router, prefix="/health", tags=["Health & Readiness"])
api_router.include_router(business_services.router, prefix="/business-services", tags=["Business Services"])
