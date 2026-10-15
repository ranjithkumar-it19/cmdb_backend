import io
import pytest
from fastapi.testclient import TestClient


def test_asset_crud_lifecycle(client: TestClient, auth_headers: dict):
    # 1. Create asset
    asset_payload = {
        "display_name": "Test Web Server 01",
        "primary_hostname": "web01.internal",
        "primary_ip": "10.0.5.10",
        "asset_type": "server",
        "operating_system": "Ubuntu 22.04 LTS",
        "serial_number": "VMW-TEST-123",
        "status": "active",
        "environment": "production",
    }
    create_res = client.post("/api/v1/assets", json=asset_payload, headers=auth_headers)
    assert create_res.status_code == 201
    created_data = create_res.json()
    asset_id = created_data["id"]
    assert created_data["display_name"] == "Test Web Server 01"

    # 2. Get asset detail
    detail_res = client.get(f"/api/v1/assets/{asset_id}", headers=auth_headers)
    assert detail_res.status_code == 200
    assert detail_res.json()["primary_hostname"] == "web01.internal"

    # 3. Search asset
    search_res = client.get("/api/v1/assets?q=web01", headers=auth_headers)
    assert search_res.status_code == 200
    assert search_res.json()["total"] >= 1

    # 4. Update asset and verify change event
    patch_res = client.patch(
        f"/api/v1/assets/{asset_id}",
        json={"primary_ip": "10.0.5.20", "status": "maintenance"},
        headers=auth_headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["primary_ip"] == "10.0.5.20"
    assert patch_res.json()["status"] == "maintenance"

    # 5. Verify history
    history_res = client.get(f"/api/v1/assets/{asset_id}/history", headers=auth_headers)
    assert history_res.status_code == 200
    history = history_res.json()
    assert len(history) >= 2

    # 6. Delete asset
    del_res = client.delete(f"/api/v1/assets/{asset_id}", headers=auth_headers)
    assert del_res.status_code == 204

    # 7. Verify 404 on deleted asset
    get_del = client.get(f"/api/v1/assets/{asset_id}", headers=auth_headers)
    assert get_del.status_code == 404


def test_csv_import_and_export(client: TestClient, auth_headers: dict):
    csv_content = """display_name,primary_hostname,primary_ip,serial_number,asset_type,status
Database Server,db01.corp.local,10.0.10.5,SRV-DB-9901,server,active
Core Switch,sw01.corp.local,10.0.10.1,FOC-SW-1100,network_device,active
"""
    # 1. Preview
    files = {"file": ("test.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    preview_res = client.post("/api/v1/imports/csv/preview", files=files, headers=auth_headers)
    assert preview_res.status_code == 200
    p_data = preview_res.json()
    assert p_data["total_rows"] == 2
    assert p_data["valid_rows_count"] == 2

    # 2. Execute import
    files = {"file": ("test.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    import_res = client.post("/api/v1/imports/csv/execute", files=files, headers=auth_headers)
    assert import_res.status_code == 200
    i_data = import_res.json()
    assert i_data["created_count"] == 2

    # 3. Export CSV
    export_res = client.get("/api/v1/assets/export", headers=auth_headers)
    assert export_res.status_code == 200
    assert "db01.corp.local" in export_res.text
