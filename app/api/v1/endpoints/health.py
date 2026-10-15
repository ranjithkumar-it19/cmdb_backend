from typing import Any, Dict
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db

router = APIRouter()


@router.get("")
def health_check(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Central health and readiness probe verifying database connectivity."""
    db_status = "healthy"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "service": "Atlas Discovery & CMDB API",
        "database": db_status,
        "version": "1.0.0",
    }
