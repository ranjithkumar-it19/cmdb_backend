import csv
import io
import json
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.observation import AssetObservation
from app.reconciliation.normalizer import Normalizer
from app.reconciliation.engine import ReconciliationEngine
from app.schemas.import_export import CsvPreviewResponse, CsvPreviewRow, CsvImportSummary


CSV_TEMPLATE_COLUMNS = [
    "display_name",
    "primary_hostname",
    "primary_ip",
    "serial_number",
    "mac_addresses",
    "asset_tag",
    "asset_type",
    "manufacturer",
    "model",
    "operating_system",
    "operating_system_version",
    "architecture",
    "cpu_info",
    "memory_gb",
    "storage_gb",
    "domain_or_workgroup",
    "environment",
    "location",
    "owner",
    "status",
]


class CsvImporter:
    """Robust CSV Import & Export Processor with Validation and Injection Defense."""

    @staticmethod
    def get_template_csv() -> str:
        """Generate clean downloadable CSV template with standard headers."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(CSV_TEMPLATE_COLUMNS)
        # Add sample row
        writer.writerow([
            "Primary Domain Controller",
            "dc01.corp.local",
            "192.168.1.10",
            "VMW-984210",
            "00:50:56:AB:CD:01",
            "ATLAS-SRV-001",
            "server",
            "VMware, Inc.",
            "VMware Virtual Platform",
            "Windows Server 2022",
            "21H2",
            "x64",
            "Intel Xeon Gold 6248R",
            "32.0",
            "500.0",
            "CORP.LOCAL",
            "production",
            "HQ Datacenter",
            "IT Infrastructure",
            "active",
        ])
        return output.getvalue()

    @staticmethod
    def sanitize_field_against_csv_injection(value: Optional[str]) -> Optional[str]:
        """Prevent CSV formula injection by prepending apostrophe if field begins with =, +, -, @."""
        if not value:
            return value
        val_str = str(value).strip()
        if val_str and val_str[0] in ("=", "+", "-", "@", "\t", "\r"):
            return "'" + val_str
        return val_str

    @staticmethod
    def preview(csv_content: str, db: Session) -> CsvPreviewResponse:
        """Parse, validate, and check duplicates for CSV preview."""
        rows, headers = CsvImporter._parse_csv_string(csv_content)
        preview_rows: List[CsvPreviewRow] = []

        valid_count = 0
        invalid_count = 0
        duplicate_count = 0

        # Query existing assets for duplicate detection
        existing_hostnames = {a[0].lower() for a in db.query(Asset.primary_hostname).filter(Asset.primary_hostname.isnot(None)).all()}
        existing_serials = {a[0].upper() for a in db.query(Asset.serial_number).filter(Asset.serial_number.isnot(None)).all()}
        existing_tags = {a[0].upper() for a in db.query(Asset.asset_tag).filter(Asset.asset_tag.isnot(None)).all()}

        for idx, row in enumerate(rows, start=1):
            errors = []
            warnings = []
            is_duplicate = False
            match_info = None

            # Validation
            display_name = row.get("display_name") or row.get("primary_hostname") or row.get("primary_ip")
            if not display_name:
                errors.append("Row requires at least a display_name, primary_hostname, or primary_ip")

            ip = row.get("primary_ip")
            if ip and not Normalizer.normalize_ip(ip):
                warnings.append(f"Primary IP '{ip}' is not a standard IPv4 address")

            # Check potential duplicates
            serial = row.get("serial_number")
            hostname = row.get("primary_hostname")
            tag = row.get("asset_tag")

            if serial and serial.strip().upper() in existing_serials:
                is_duplicate = True
                match_info = f"Serial number '{serial}' already exists in inventory"
            elif tag and tag.strip().upper() in existing_tags:
                is_duplicate = True
                match_info = f"Asset tag '{tag}' already exists in inventory"
            elif hostname and hostname.strip().lower() in existing_hostnames:
                warnings.append(f"Hostname '{hostname}' exists on an existing asset (possible merge/update)")

            is_valid = len(errors) == 0
            if is_valid:
                valid_count += 1
            else:
                invalid_count += 1

            if is_duplicate:
                duplicate_count += 1

            preview_rows.append(CsvPreviewRow(
                row_number=idx,
                data=row,
                is_valid=is_valid,
                errors=errors,
                warnings=warnings,
                is_duplicate=is_duplicate,
                duplicate_match_info=match_info,
            ))

        return CsvPreviewResponse(
            total_rows=len(rows),
            valid_rows_count=valid_count,
            invalid_rows_count=invalid_count,
            duplicates_detected_count=duplicate_count,
            detected_headers=headers,
            preview_rows=preview_rows[:50],  # Preview first 50 rows
        )

    @staticmethod
    def execute_import(
        csv_content: str,
        db: Session,
        dry_run: bool = False,
        column_mapping: Optional[Dict[str, str]] = None,
        job_id: Optional[str] = None,
    ) -> CsvImportSummary:
        """Import rows through observation and reconciliation engine."""
        rows, _ = CsvImporter._parse_csv_string(csv_content)
        created_count = 0
        updated_count = 0
        skipped_count = 0
        error_count = 0
        errors: List[str] = []

        reconciliation_engine = ReconciliationEngine(db)

        for idx, raw_row in enumerate(rows, start=1):
            try:
                # Apply column mapping if provided
                row = {}
                for k, v in raw_row.items():
                    target_field = column_mapping.get(k, k) if column_mapping else k
                    row[target_field] = v.strip() if isinstance(v, str) else v

                display_name = row.get("display_name") or row.get("primary_hostname") or row.get("primary_ip")
                if not display_name:
                    error_count += 1
                    errors.append(f"Row {idx}: missing required display_name, hostname, or IP")
                    continue

                if dry_run:
                    # In dry-run mode, validate without saving
                    created_count += 1
                    continue

                # Ingest through AssetObservation for complete auditability
                obs = AssetObservation(
                    job_id=job_id,
                    observed_hostname=row.get("primary_hostname"),
                    observed_ip=row.get("primary_ip"),
                    observed_macs=row.get("mac_addresses"),
                    observed_os=row.get("operating_system"),
                    observed_serial=row.get("serial_number"),
                    raw_payload=json.dumps(row),
                    validation_status="valid",
                )
                db.add(obs)
                db.flush()

                rec_result = reconciliation_engine.process_observation(obs, auto_commit=False)
                if rec_result.decision == "created_new":
                    created_count += 1
                elif rec_result.decision == "updated_existing":
                    updated_count += 1
                else:
                    skipped_count += 1

            except Exception as e:
                error_count += 1
                errors.append(f"Row {idx} error: {str(e)}")

        if not dry_run and error_count == 0:
            db.commit()
        elif not dry_run and error_count > 0:
            # Commit valid items and report partial errors
            db.commit()

        return CsvImportSummary(
            total_processed=len(rows),
            created_count=created_count,
            updated_count=updated_count,
            skipped_count=skipped_count,
            error_count=error_count,
            errors=errors,
            dry_run=dry_run,
        )

    @staticmethod
    def export_assets_csv(assets: List[Asset]) -> str:
        """Export asset inventory to CSV with formula injection sanitization."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(CSV_TEMPLATE_COLUMNS)

        for a in assets:
            writer.writerow([
                CsvImporter.sanitize_field_against_csv_injection(a.display_name),
                CsvImporter.sanitize_field_against_csv_injection(a.primary_hostname),
                CsvImporter.sanitize_field_against_csv_injection(a.primary_ip),
                CsvImporter.sanitize_field_against_csv_injection(a.serial_number),
                CsvImporter.sanitize_field_against_csv_injection(a.mac_addresses),
                CsvImporter.sanitize_field_against_csv_injection(a.asset_tag),
                a.asset_type,
                CsvImporter.sanitize_field_against_csv_injection(a.manufacturer),
                CsvImporter.sanitize_field_against_csv_injection(a.model),
                CsvImporter.sanitize_field_against_csv_injection(a.operating_system),
                CsvImporter.sanitize_field_against_csv_injection(a.operating_system_version),
                a.architecture,
                CsvImporter.sanitize_field_against_csv_injection(a.cpu_info),
                a.memory_gb,
                a.storage_gb,
                CsvImporter.sanitize_field_against_csv_injection(a.domain_or_workgroup),
                a.environment,
                CsvImporter.sanitize_field_against_csv_injection(a.location),
                CsvImporter.sanitize_field_against_csv_injection(a.owner),
                a.status,
            ])

        return output.getvalue()

    @staticmethod
    def _parse_csv_string(csv_text: str) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Parse raw CSV string safely into list of dictionaries."""
        reader = csv.reader(io.StringIO(csv_text.strip()))
        headers = []
        rows = []
        for i, raw_line in enumerate(reader):
            if not raw_line or all(not cell.strip() for cell in raw_line):
                continue
            if not headers:
                headers = [h.strip() for h in raw_line]
            else:
                row_dict = {}
                for idx, col in enumerate(headers):
                    val = raw_line[idx] if idx < len(raw_line) else ""
                    row_dict[col] = val.strip()
                rows.append(row_dict)
        return rows, headers
