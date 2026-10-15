import pytest
from fastapi.testclient import TestClient


def test_auth_login_success(client: TestClient):
    response = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "admin@atlas.local", "password": "AdminSecurePassword123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "admin@atlas.local"


def test_auth_login_invalid_password(client: TestClient):
    response = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "admin@atlas.local", "password": "WrongPassword!"},
    )
    assert response.status_code == 401


def test_get_current_user(client: TestClient, auth_headers: dict):
    response = client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["username"] == "admin"


def test_unauthorized_access_fails(client: TestClient):
    response = client.get("/api/v1/assets")
    assert response.status_code == 401
