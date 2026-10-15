import json
import pytest
from app.models.asset import Asset
from app.models.observation import AssetObservation
from app.reconciliation.engine import ReconciliationEngine


def test_reconciliation_creates_new_asset(db):
    engine = ReconciliationEngine(db)
    obs = AssetObservation(
        observed_hostname="server-alpha.corp.local",
        observed_ip="10.0.1.15",
        observed_serial="SRV-ALPHA-99",
        raw_payload=json.dumps({
            "hostname": "server-alpha.corp.local",
            "ip": "10.0.1.15",
            "serial_number": "SRV-ALPHA-99",
            "manufacturer": "Dell Inc.",
            "operating_system": "Ubuntu 22.04 LTS",
        }),
    )
    db.add(obs)
    db.flush()

    result = engine.process_observation(obs)
    assert result.decision == "created_new"
    assert result.asset is not None
    assert result.asset.primary_hostname == "server-alpha.corp.local"
    assert result.asset.manufacturer == "Dell"
    assert result.asset.operating_system == "Ubuntu"


def test_reconciliation_matches_existing_by_serial(db):
    engine = ReconciliationEngine(db)

    # First observation creates the asset
    obs1 = AssetObservation(
        observed_serial="SRV-EXACT-001",
        raw_payload=json.dumps({
            "hostname": "initial-host.local",
            "serial_number": "SRV-EXACT-001",
            "operating_system": "Windows Server 2022",
        }),
    )
    db.add(obs1)
    db.flush()
    res1 = engine.process_observation(obs1)
    asset_id = res1.asset.id

    # Second observation with same serial but updated IP and hostname updates the existing asset
    obs2 = AssetObservation(
        observed_serial="SRV-EXACT-001",
        raw_payload=json.dumps({
            "hostname": "renamed-host.local",
            "ip": "10.0.2.55",
            "serial_number": "SRV-EXACT-001",
            "operating_system": "Windows Server 2022",
        }),
    )
    db.add(obs2)
    db.flush()
    res2 = engine.process_observation(obs2)

    assert res2.decision == "updated_existing"
    assert res2.asset.id == asset_id
    assert res2.asset.primary_hostname == "renamed-host.local"
    assert res2.asset.primary_ip == "10.0.2.55"


def test_no_destructive_merge_on_unverified_hostname_alone(db):
    engine = ReconciliationEngine(db)

    # Create asset 1 with serial A
    obs1 = AssetObservation(
        observed_hostname="common-bastion.corp.local",
        observed_serial="SRV-DIFFERENT-A",
        raw_payload=json.dumps({"hostname": "common-bastion.corp.local", "serial_number": "SRV-DIFFERENT-A"}),
    )
    db.add(obs1)
    db.flush()
    engine.process_observation(obs1)

    # Asset 2 shares same hostname but has different serial number
    obs2 = AssetObservation(
        observed_hostname="common-bastion.corp.local",
        observed_serial="SRV-DIFFERENT-B",
        raw_payload=json.dumps({"hostname": "common-bastion.corp.local", "serial_number": "SRV-DIFFERENT-B"}),
    )
    db.add(obs2)
    db.flush()
    res2 = engine.process_observation(obs2)

    # It must NOT auto-merge asset 2 into asset 1!
    assert res2.decision != "updated_existing"
