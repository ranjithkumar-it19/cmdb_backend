import pytest
from fastapi.testclient import TestClient


def test_get_acme_risk_review(client: TestClient, auth_headers: dict):
    response = client.get(
        "/api/v1/risk-insights/acme-risk-review",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["dashboard_title"] == "Acme Risk Review"
    assert data["total_assets"] >= 57842
    assert data["total_software_titles"] >= 9822
    assert data["total_users"] >= 16479
    assert len(data["lifecycle_progression"]) == 4
    assert len(data["users_by_department"]) == 6
    assert "critical" in data["vulnerabilities_by_department"]
    assert "Medium" in data["servers_at_risk_by_severity"]


def test_get_vulnerable_assets(client: TestClient, auth_headers: dict):
    response = client.get(
        "/api/v1/risk-insights/vulnerable-assets",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_vulnerabilities"] == 9274
    assert data["vulnerable_assets"] == 3610
    assert len(data["cves"]) > 0
    assert "Critical" in data["vulnerabilities_by_severity"]
    assert len(data["vulnerable_assets_over_time"]) == 6
    assert "Available" in data["patch_info"]
    assert len(data["vendor_affected_products"]) > 0


def test_toggle_ignore_vulnerability(client: TestClient, auth_headers: dict):
    # Test ignore toggle
    response = client.post(
        "/api/v1/risk-insights/vulnerabilities/CVE-2023-9876/ignore?ignore=true",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["is_ignored"] is True

    # Restore
    response = client.post(
        "/api/v1/risk-insights/vulnerabilities/CVE-2023-9876/ignore?ignore=false",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["is_ignored"] is False


def test_seeded_ignored_vulnerabilities_are_listed_separately(client: TestClient, auth_headers: dict):
    ignored_response = client.get(
        "/api/v1/risk-insights/vulnerable-assets?show_ignored=true",
        headers=auth_headers,
    )
    assert ignored_response.status_code == 200
    ignored_cves = ignored_response.json()["cves"]
    ignored_cve_ids = {cve["cve_id"] for cve in ignored_cves}

    assert {
        "CVE-2024-3094",
        "CVE-2021-41773",
        "CVE-2023-22515",
    }.issubset(ignored_cve_ids)
    assert all(cve["is_ignored"] for cve in ignored_cves)

    active_response = client.get(
        "/api/v1/risk-insights/vulnerable-assets",
        headers=auth_headers,
    )
    assert active_response.status_code == 200
    active_cve_ids = {cve["cve_id"] for cve in active_response.json()["cves"]}
    assert ignored_cve_ids.isdisjoint(active_cve_ids)


def test_get_hardware_lifecycle(client: TestClient, auth_headers: dict):
    response = client.get(
        "/api/v1/risk-insights/hardware-lifecycle",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_tracked_assets"] == 57842
    assert data["active_warranty"] > 0
    assert len(data["hardware_items"]) > 0
    assert "Dell Technologies" in data["vendor_distribution"]


def test_get_os_lifecycle(client: TestClient, auth_headers: dict):
    response = client.get(
        "/api/v1/risk-insights/os-lifecycle",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_systems"] == 57842
    assert data["win10_eol_countdown_days"] > 0
    assert len(data["os_families"]) > 0
    assert len(data["systems"]) > 0


def test_get_security_insights(client: TestClient, auth_headers: dict):
    response = client.get(
        "/api/v1/risk-insights/security-insights",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_findings"] >= 6
    assert data["compliance_score"] > 0
    assert len(data["findings"]) >= 6
