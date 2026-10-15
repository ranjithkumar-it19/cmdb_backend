from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class CsvPreviewRow(BaseModel):
    row_number: int
    data: Dict[str, Any]
    is_valid: bool
    errors: List[str] = []
    warnings: List[str] = []
    is_duplicate: bool = False
    duplicate_match_info: Optional[str] = None


class CsvPreviewResponse(BaseModel):
    total_rows: int
    valid_rows_count: int
    invalid_rows_count: int
    duplicates_detected_count: int
    detected_headers: List[str]
    preview_rows: List[CsvPreviewRow]


class CsvImportRequest(BaseModel):
    file_content: str  # Base64 or raw string
    dry_run: bool = False
    column_mapping: Optional[Dict[str, str]] = None  # csv_col -> asset_field


class CsvImportSummary(BaseModel):
    total_processed: int
    created_count: int
    updated_count: int
    skipped_count: int
    error_count: int
    errors: List[str] = []
    dry_run: bool = False
