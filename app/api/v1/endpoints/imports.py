from fastapi import APIRouter, Depends, File, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.discovery.csv_importer import CsvImporter
from app.schemas.import_export import CsvPreviewResponse, CsvImportSummary, CsvImportRequest
from app.services.auth_service import get_current_user
from app.services.audit_service import AuditService
from app.models.user import User

router = APIRouter()


@router.get("/csv/template")
def download_csv_template():
    """Download standardized CSV template with instructions."""
    csv_data = CsvImporter.get_template_csv()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=atlas_import_template.csv"},
    )


@router.post("/csv/preview", response_model=CsvPreviewResponse)
async def preview_csv_import(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Preview CSV rows, validate schemas, and detect potential duplicate matches."""
    contents = await file.read()
    csv_text = contents.decode("utf-8-sig", errors="replace")
    return CsvImporter.preview(csv_text, db)


@router.post("/csv/execute", response_model=CsvImportSummary)
async def execute_csv_import(
    file: UploadFile = File(...),
    dry_run: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Import CSV inventory file with reconciliation and duplicate handling."""
    contents = await file.read()
    csv_text = contents.decode("utf-8-sig", errors="replace")
    summary = CsvImporter.execute_import(csv_text, db, dry_run=dry_run)

    if not dry_run:
        AuditService.log_event(
            db=db,
            action="import_csv_assets",
            resource_type="asset",
            user=current_user,
            details={
                "created": summary.created_count,
                "updated": summary.updated_count,
                "errors": summary.error_count,
            },
        )

    return summary
