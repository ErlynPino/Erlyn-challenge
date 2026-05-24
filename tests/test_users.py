"""
Tests for all CRUD endpoints of /api/v1/users.

Each test function is independent: the in-memory SQLite database is
recreated per test session via the `client` fixture in conftest.py.
"""
import pytest
from sqlalchemy.exc import IntegrityError
from unittest.mock import patch
from fastapi.testclient import TestClient

BASE = "/api/v1/users"

JOHN = {
    "username": "john_doe",
    "email": "john@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "role": "user",
    "active": True,
}


# ── Helpers ───────────────────────────────────────────────────────────────────


def create_john(client: TestClient) -> dict:
    return client.post(BASE, json=JOHN).json()


# ── CREATE ────────────────────────────────────────────────────────────────────


def test_create_user_returns_201(client: TestClient):
    response = client.post(BASE, json=JOHN)
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "john_doe"
    assert data["email"] == "john@example.com"
    assert "id" in data
    assert "password" not in data


def test_create_user_with_explicit_role(client: TestClient):
    payload = {**JOHN, "role": "admin"}
    data = client.post(BASE, json=payload).json()
    assert data["role"] == "admin"


def test_create_user_duplicate_username_returns_409(client: TestClient):
    client.post(BASE, json=JOHN)
    response = client.post(BASE, json={**JOHN, "email": "other@example.com"})
    assert response.status_code == 409


def test_create_user_duplicate_email_returns_409(client: TestClient):
    client.post(BASE, json=JOHN)
    response = client.post(BASE, json={**JOHN, "username": "jane_doe"})
    assert response.status_code == 409


def test_create_user_invalid_email_returns_422(client: TestClient):
    response = client.post(BASE, json={**JOHN, "email": "not-an-email"})
    assert response.status_code == 422


def test_create_user_invalid_role_returns_422(client: TestClient):
    response = client.post(BASE, json={**JOHN, "role": "superuser"})
    assert response.status_code == 422


def test_create_user_short_username_returns_422(client: TestClient):
    response = client.post(BASE, json={**JOHN, "username": "ab"})
    assert response.status_code == 422


# ── LIST ──────────────────────────────────────────────────────────────────────


def test_list_users_empty(client: TestClient):
    response = client.get(BASE)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 0
    assert body["data"] == []


def test_list_users_returns_all(client: TestClient):
    client.post(BASE, json=JOHN)
    response = client.get(BASE)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert len(body["data"]) == 1


def test_list_users_pagination(client: TestClient):
    for i in range(5):
        client.post(
            BASE,
            json={**JOHN, "username": f"user{i}", "email": f"user{i}@example.com"},
        )
    response = client.get(f"{BASE}?skip=2&limit=2")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 5
    assert len(body["data"]) == 2
    assert body["skip"] == 2
    assert body["limit"] == 2


def test_list_users_invalid_limit_returns_422(client: TestClient):
    response = client.get(f"{BASE}?limit=0")
    assert response.status_code == 422


# ── GET BY ID ─────────────────────────────────────────────────────────────────


def test_get_user_by_id(client: TestClient):
    created = create_john(client)
    response = client.get(f"{BASE}/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_user_not_found_returns_404(client: TestClient):
    response = client.get(f"{BASE}/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


# ── PUT ───────────────────────────────────────────────────────────────────────


def test_full_update_user(client: TestClient):
    created = create_john(client)
    response = client.put(
        f"{BASE}/{created['id']}",
        json={"first_name": "Jane", "last_name": "Smith", "role": "admin"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "Jane"
    assert data["role"] == "admin"


def test_full_update_user_not_found_returns_404(client: TestClient):
    response = client.put(
        f"{BASE}/00000000-0000-0000-0000-000000000000",
        json={"first_name": "X"},
    )
    assert response.status_code == 404


def test_full_update_duplicate_username_returns_409(client: TestClient):
    create_john(client)
    u2 = client.post(
        BASE, json={**JOHN, "username": "jane_doe", "email": "jane@example.com"}
    ).json()
    response = client.put(f"{BASE}/{u2['id']}", json={"username": "john_doe"})
    assert response.status_code == 409


def test_full_update_duplicate_email_returns_409(client: TestClient):
    create_john(client)
    u2 = client.post(
        BASE, json={**JOHN, "username": "jane_doe", "email": "jane@example.com"}
    ).json()
    response = client.put(f"{BASE}/{u2['id']}", json={"email": "john@example.com"})
    assert response.status_code == 409


# ── PATCH ─────────────────────────────────────────────────────────────────────


def test_partial_update_active_flag(client: TestClient):
    created = create_john(client)
    response = client.patch(f"{BASE}/{created['id']}", json={"active": False})
    assert response.status_code == 200
    assert response.json()["active"] is False


def test_partial_update_preserves_other_fields(client: TestClient):
    created = create_john(client)
    response = client.patch(
        f"{BASE}/{created['id']}", json={"first_name": "Johnny"}
    )
    data = response.json()
    assert data["first_name"] == "Johnny"
    assert data["last_name"] == created["last_name"]


def test_partial_update_user_not_found_returns_404(client: TestClient):
    response = client.patch(
        f"{BASE}/00000000-0000-0000-0000-000000000000", json={"active": False}
    )
    assert response.status_code == 404


def test_partial_update_updated_at_changes(client: TestClient):
    created = create_john(client)
    original_updated_at = created["updated_at"]
    response = client.patch(f"{BASE}/{created['id']}", json={"first_name": "New"})
    assert response.json()["updated_at"] >= original_updated_at


# ── DELETE ────────────────────────────────────────────────────────────────────


def test_delete_user_returns_204(client: TestClient):
    created = create_john(client)
    response = client.delete(f"{BASE}/{created['id']}")
    assert response.status_code == 204


def test_delete_user_removes_record(client: TestClient):
    created = create_john(client)
    client.delete(f"{BASE}/{created['id']}")
    assert client.get(f"{BASE}/{created['id']}").status_code == 404


def test_delete_user_not_found_returns_404(client: TestClient):
    response = client.delete(f"{BASE}/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


# ── HEALTH ────────────────────────────────────────────────────────────────────


def test_health_check(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


# ── SCHEMA VALIDATION ────────────────────────────────────────────────────────


def test_create_user_username_too_long_returns_422(client: TestClient):
    response = client.post(BASE, json={**JOHN, "username": "a" * 51})
    assert response.status_code == 422


def test_create_user_first_name_too_long_returns_422(client: TestClient):
    response = client.post(BASE, json={**JOHN, "first_name": "a" * 101})
    assert response.status_code == 422


# ── INTEGRITY ERROR SAFETY NET ────────────────────────────────────────────────


def test_create_user_integrity_error_returns_409(client: TestClient):
    """Simulates a concurrent insert that bypasses pre-checks but hits a DB unique constraint."""
    with patch(
        "app.routers.users.user_service.create_user",
        side_effect=IntegrityError("duplicate", {}, Exception()),
    ):
        response = client.post(BASE, json=JOHN)
    assert response.status_code == 409


def test_full_update_integrity_error_returns_409(client: TestClient):
    created = create_john(client)
    with patch(
        "app.routers.users.user_service.update_user",
        side_effect=IntegrityError("duplicate", {}, Exception()),
    ):
        response = client.put(
            f"{BASE}/{created['id']}", json={"username": "other_name"}
        )
    assert response.status_code == 409


def test_partial_update_integrity_error_returns_409(client: TestClient):
    created = create_john(client)
    with patch(
        "app.routers.users.user_service.update_user",
        side_effect=IntegrityError("duplicate", {}, Exception()),
    ):
        response = client.patch(
            f"{BASE}/{created['id']}", json={"username": "other_name"}
        )
    assert response.status_code == 409
