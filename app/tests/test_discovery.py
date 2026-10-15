import pytest
from app.discovery.mock_adapter import MockDiscoveryAdapter
from app.discovery.base import DiscoveryError
from app.workers.tasks import execute_discovery_job
from app.models.discovery import DiscoverySource, DiscoveryJob
from app.models.asset import Asset


def test_mock_discovery_adapter_deterministic_collection():
    adapter = MockDiscoveryAdapter()
    assert adapter.test_connectivity("192.168.1.10") is True
    assert adapter.test_connectivity("192.168.1.99") is False  # Simulated offline

    # Test collection
    data = adapter.collect("192.168.1.10")
    assert "hostname" in data
    assert "ip" in data
    assert data["ip"] == "192.168.1.10"
    assert "operating_system" in data

    # Test offline host raises DiscoveryError
    with pytest.raises(DiscoveryError):
        adapter.collect("192.168.1.99")


def test_scope_validation_enforcement():
    adapter = MockDiscoveryAdapter()
    scope_def = '["192.168.1.0/24", "10.0.0.0/24"]'

    # Targets in scope
    assert adapter.validate_target_in_scope("192.168.1.50", scope_def) is True
    assert adapter.validate_target_in_scope("10.0.0.1", scope_def) is True

    # Targets out of scope
    assert adapter.validate_target_in_scope("172.16.0.1", scope_def) is False
    assert adapter.validate_target_in_scope("8.8.8.8", scope_def) is False


def test_discovery_job_execution_pipeline(db):
    source = DiscoverySource(
        name="Unit Test Source",
        source_type="mock",
        scope_definition='["192.168.1.0/24"]',
        is_active=True,
    )
    db.add(source)
    db.commit()

    job = DiscoveryJob(
        source_id=source.id,
        status="queued",
    )
    db.add(job)
    db.commit()

    # Execute discovery job pipeline synchronously in test
    execute_discovery_job(db, job.id)

    db.refresh(job)
    assert job.status in ("succeeded", "partially_succeeded")
    assert job.total_targets > 0
    assert job.successful_targets > 0

    # Verify that asset records were created in the database
    assets = db.query(Asset).all()
    assert len(assets) > 0
