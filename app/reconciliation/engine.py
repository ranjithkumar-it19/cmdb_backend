import json
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from app.core.logging import logger
from app.models.asset import Asset, AssetIdentifier
from app.models.observation import AssetObservation
from app.models.change_history import AssetChangeEvent
from app.models.software import SoftwareProduct, SoftwareInstallation
from app.models.base import utc_now
from app.reconciliation.normalizer import Normalizer
from app.change_tracking.tracker import ChangeTracker


class ReconciliationResult:
    def __init__(
        self,
        decision: str,  # "created_new", "updated_existing", "flagged_review", "ignored"
        asset: Optional[Asset] = None,
        confidence_score: float = 0.0,
        matched_by: Optional[str] = None,
        change_events: Optional[List[AssetChangeEvent]] = None,
    ):
        self.decision = decision
        self.asset = asset
        self.confidence_score = confidence_score
        self.matched_by = matched_by
        self.change_events = change_events or []


class ReconciliationEngine:
    """Enterprise Multi-Factor IT Asset Reconciliation Engine."""

    def __init__(self, db: Session):
        self.db = db

    def process_observation(
        self,
        observation: AssetObservation,
        auto_commit: bool = True,
    ) -> ReconciliationResult:
        """Process an asset observation through normalization, candidate lookup, and reconciliation."""
        raw_data: Dict[str, Any] = {}
        if observation.raw_payload:
            try:
                raw_data = json.loads(observation.raw_payload) if isinstance(observation.raw_payload, str) else observation.raw_payload
            except Exception:
                raw_data = {}

        # 1. Normalize attributes
        norm_hostname = Normalizer.normalize_hostname(
            observation.observed_hostname or raw_data.get("hostname") or raw_data.get("primary_hostname")
        )
        norm_ip = Normalizer.normalize_ip(
            observation.observed_ip or raw_data.get("ip") or raw_data.get("primary_ip")
        )
        norm_serial = Normalizer.normalize_serial(
            observation.observed_serial or raw_data.get("serial_number")
        )
        raw_macs = observation.observed_macs or raw_data.get("mac_addresses") or raw_data.get("mac")
        norm_mac_list = Normalizer.normalize_mac_list(raw_macs)
        norm_mac_str = ",".join(norm_mac_list) if norm_mac_list else None

        os_raw = observation.observed_os or raw_data.get("operating_system")
        os_info = Normalizer.normalize_os(os_raw)
        norm_mfg = Normalizer.normalize_manufacturer(raw_data.get("manufacturer"))

        norm_data = {
            "primary_hostname": norm_hostname,
            "primary_ip": norm_ip,
            "serial_number": norm_serial,
            "mac_addresses": norm_mac_str,
            "operating_system": os_info["name"] if os_info["name"] != "Unknown" else os_raw,
            "operating_system_version": os_info["version"] or raw_data.get("operating_system_version"),
            "manufacturer": norm_mfg,
            "model": raw_data.get("model"),
            "cpu_info": raw_data.get("cpu_info"),
            "memory_gb": raw_data.get("memory_gb"),
            "storage_gb": raw_data.get("storage_gb"),
            "architecture": raw_data.get("architecture"),
            "domain_or_workgroup": raw_data.get("domain_or_workgroup"),
            "asset_type": raw_data.get("asset_type") or "unknown",
            "environment": raw_data.get("environment") or "production",
            "location": raw_data.get("location"),
            "owner": raw_data.get("owner"),
            "status": raw_data.get("status") or "active",
        }

        observation.normalized_payload = json.dumps(norm_data)

        # 2. Find Candidates & Score Matches
        candidate_asset, confidence, match_reason = self._find_best_match(
            serial=norm_serial,
            mac_list=norm_mac_list,
            hostname=norm_hostname,
            bios_uuid=raw_data.get("bios_uuid"),
            machine_id=raw_data.get("machine_id"),
        )

        now = utc_now()

        # 3. Apply Decision Logic
        # Confidence threshold: >= 0.80 for automatic match/merge
        if candidate_asset and confidence >= 0.80:
            # Update existing asset
            changes = ChangeTracker.detect_and_record_changes(
                db=self.db,
                existing_asset=candidate_asset,
                updated_attributes=norm_data,
                change_source=f"discovery_job_{observation.job_id}" if observation.job_id else "observation",
                actor_or_process="reconciliation_engine",
                observation_id=observation.id,
            )

            candidate_asset.last_discovered_at = now
            observation.asset_id = candidate_asset.id
            observation.reconciliation_decision = "updated_existing"
            observation.confidence_score = confidence
            observation.processed_at = now

            # Ensure identifiers are recorded
            self._sync_identifiers(candidate_asset, norm_serial, norm_mac_list, norm_hostname, raw_data)

            # Sync software if included
            self._sync_software(candidate_asset, raw_data.get("installed_software", []))

            result = ReconciliationResult(
                decision="updated_existing",
                asset=candidate_asset,
                confidence_score=confidence,
                matched_by=match_reason,
                change_events=changes,
            )
        elif candidate_asset and confidence >= 0.50:
            # Ambiguous match (e.g. shared hostname or unverified MAC with differing hardware)
            # Flag for manual administrator review
            observation.reconciliation_decision = "flagged_review"
            observation.confidence_score = confidence
            observation.processed_at = now
            result = ReconciliationResult(
                decision="flagged_review",
                asset=candidate_asset,
                confidence_score=confidence,
                matched_by=f"ambiguous: {match_reason}",
            )
        else:
            # Create new canonical asset
            display_name = (
                norm_hostname
                or raw_data.get("display_name")
                or norm_ip
                or f"Discovered Asset ({now.strftime('%Y%m%d-%H%M%S')})"
            )

            new_asset = Asset(
                display_name=display_name,
                primary_hostname=norm_hostname,
                primary_ip=norm_ip,
                asset_tag=raw_data.get("asset_tag"),
                asset_type=norm_data["asset_type"],
                manufacturer=norm_data["manufacturer"],
                model=norm_data["model"],
                serial_number=norm_serial,
                cpu_info=norm_data["cpu_info"],
                memory_gb=norm_data["memory_gb"],
                storage_gb=norm_data["storage_gb"],
                operating_system=norm_data["operating_system"],
                operating_system_version=norm_data["operating_system_version"],
                architecture=norm_data["architecture"],
                domain_or_workgroup=norm_data["domain_or_workgroup"],
                environment=norm_data["environment"],
                location=norm_data["location"],
                owner=norm_data["owner"],
                mac_addresses=norm_mac_str,
                status=norm_data["status"],
                confidence_score=1.0,
                first_discovered_at=now,
                last_discovered_at=now,
            )
            self.db.add(new_asset)
            self.db.flush()

            # Record initial identifiers
            self._sync_identifiers(new_asset, norm_serial, norm_mac_list, norm_hostname, raw_data)

            # Initial change event
            init_change = AssetChangeEvent(
                asset_id=new_asset.id,
                field_name="status",
                old_value=None,
                new_value=new_asset.status,
                change_source=f"discovery_job_{observation.job_id}" if observation.job_id else "observation",
                actor_or_process="reconciliation_engine",
                observation_id=observation.id,
                created_at=now,
            )
            self.db.add(init_change)

            # Sync software if included
            self._sync_software(new_asset, raw_data.get("installed_software", []))

            observation.asset_id = new_asset.id
            observation.reconciliation_decision = "created_new"
            observation.confidence_score = 1.0
            observation.processed_at = now

            result = ReconciliationResult(
                decision="created_new",
                asset=new_asset,
                confidence_score=1.0,
                matched_by="none (new asset created)",
                change_events=[init_change],
            )

        if auto_commit:
            self.db.commit()

        return result

    def _find_best_match(
        self,
        serial: Optional[str],
        mac_list: List[str],
        hostname: Optional[str],
        bios_uuid: Optional[str],
        machine_id: Optional[str],
    ) -> Tuple[Optional[Asset], float, Optional[str]]:
        """Multi-factor candidate match evaluation based on strong & secondary identifiers."""

        # 1. Strong ID: Serial Number
        if serial:
            match_by_serial = (
                self.db.query(Asset)
                .filter(func.upper(Asset.serial_number) == serial.upper())
                .first()
            )
            if match_by_serial:
                return match_by_serial, 0.98, f"serial_number:{serial}"

            # Check asset_identifiers
            ident = (
                self.db.query(AssetIdentifier)
                .filter(
                    AssetIdentifier.identifier_type == "serial_number",
                    AssetIdentifier.identifier_value == serial,
                )
                .first()
            )
            if ident and ident.asset:
                return ident.asset, 0.98, f"asset_identifier:serial_number:{serial}"

        # 2. Strong ID: BIOS UUID
        if bios_uuid:
            ident = (
                self.db.query(AssetIdentifier)
                .filter(
                    AssetIdentifier.identifier_type == "bios_uuid",
                    AssetIdentifier.identifier_value == bios_uuid.strip().lower(),
                )
                .first()
            )
            if ident and ident.asset:
                return ident.asset, 0.95, f"bios_uuid:{bios_uuid}"

        # 3. Strong ID: Machine ID
        if machine_id:
            ident = (
                self.db.query(AssetIdentifier)
                .filter(
                    AssetIdentifier.identifier_type == "machine_id",
                    AssetIdentifier.identifier_value == machine_id.strip().lower(),
                )
                .first()
            )
            if ident and ident.asset:
                return ident.asset, 0.95, f"machine_id:{machine_id}"

        # 4. Secondary: MAC Address match
        if mac_list:
            for mac in mac_list:
                ident = (
                    self.db.query(AssetIdentifier)
                    .filter(
                        AssetIdentifier.identifier_type == "mac_address",
                        AssetIdentifier.identifier_value == mac,
                    )
                    .first()
                )
                if ident and ident.asset:
                    asset = ident.asset
                    # Boost confidence if hostname also matches
                    if hostname and asset.primary_hostname and asset.primary_hostname.lower() == hostname.lower():
                        return asset, 0.90, f"mac_address:{mac} + hostname:{hostname}"
                    return asset, 0.82, f"mac_address:{mac}"

        # 5. Hostname match alone (Weaker confidence)
        if hostname:
            asset = (
                self.db.query(Asset)
                .filter(func.lower(Asset.primary_hostname) == hostname.lower())
                .first()
            )
            if asset:
                # Hostname alone does not meet 0.80 auto-merge threshold
                return asset, 0.55, f"hostname_only:{hostname}"

        return None, 0.0, None

    def _sync_identifiers(
        self,
        asset: Asset,
        serial: Optional[str],
        mac_list: List[str],
        hostname: Optional[str],
        raw_data: Dict[str, Any],
    ) -> None:
        """Upsert asset identifiers to preserve candidate search indexes."""
        existing_idents = {
            (i.identifier_type, i.identifier_value): i for i in asset.identifiers
        }

        def add_ident_if_absent(itype: str, ival: str, raw: Optional[str], confidence: float, is_primary: bool):
            if not ival:
                return
            key = (itype, ival)
            if key not in existing_idents:
                new_ident = AssetIdentifier(
                    asset_id=asset.id,
                    identifier_type=itype,
                    identifier_value=ival,
                    raw_value=raw,
                    source="reconciliation",
                    confidence=confidence,
                    is_primary=is_primary,
                )
                self.db.add(new_ident)
                existing_idents[key] = new_ident

        if serial:
            add_ident_if_absent("serial_number", serial, raw_data.get("serial_number"), 1.0, True)

        if raw_data.get("bios_uuid"):
            add_ident_if_absent("bios_uuid", raw_data["bios_uuid"].strip().lower(), raw_data["bios_uuid"], 0.95, False)

        if raw_data.get("machine_id"):
            add_ident_if_absent("machine_id", raw_data["machine_id"].strip().lower(), raw_data["machine_id"], 0.95, False)

        for mac in mac_list:
            add_ident_if_absent("mac_address", mac, mac, 0.85, False)

        if hostname:
            add_ident_if_absent("hostname", hostname, hostname, 0.60, False)

    def _sync_software(self, asset: Asset, software_list: List[Dict[str, Any]]) -> None:
        """Register discovered software products and link installations."""
        if not software_list or not isinstance(software_list, list):
            return

        now = utc_now()
        for sw in software_list:
            if not isinstance(sw, dict):
                continue
            name = sw.get("name")
            if not name:
                continue
            norm_name = Normalizer.normalize_software_name(name) or name
            publisher = sw.get("publisher")
            version = sw.get("version")
            arch = sw.get("architecture")

            # Find or create SoftwareProduct
            product = (
                self.db.query(SoftwareProduct)
                .filter(
                    SoftwareProduct.normalized_name == norm_name,
                    SoftwareProduct.publisher == publisher,
                )
                .first()
            )
            if not product:
                product = SoftwareProduct(
                    name=name,
                    normalized_name=norm_name,
                    publisher=publisher,
                    category=sw.get("category"),
                )
                self.db.add(product)
                self.db.flush()

            # Find or create SoftwareInstallation
            inst = (
                self.db.query(SoftwareInstallation)
                .filter(
                    SoftwareInstallation.asset_id == asset.id,
                    SoftwareInstallation.product_id == product.id,
                    SoftwareInstallation.version == version,
                )
                .first()
            )
            if inst:
                inst.last_seen_at = now
            else:
                inst = SoftwareInstallation(
                    asset_id=asset.id,
                    product_id=product.id,
                    version=version,
                    architecture=arch,
                    source="discovery",
                    last_seen_at=now,
                )
                self.db.add(inst)
