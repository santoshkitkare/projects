# tests/test_auth.py
import pytest
from jose import jwt
from file_processing_backend.user import SECRET_KEY, ALGORITHM, create_access_token


def test_login_success(client, admin_user):
    res = client.post(
        "/auth/login",
        data={"username": "admin", "password": "admin@123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert res.status_code == 200
    body = res.json()
    assert "accessToken" in body
    assert body["username"] == "admin"
    assert body["role"] == "admin"

    # token sanity
    payload = jwt.decode(body["accessToken"], SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == admin_user.user_id
    assert payload["role"] == "admin"


def test_login_invalid_password(client, admin_user):
    res = client.post(
        "/auth/login",
        data={"username": "admin", "password": "wrong"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert res.status_code == 400
    assert res.json()["detail"] == "Incorrect username or password"


def test_protected_route_requires_token(client):
    res = client.get("/api/v1/uploads/user/whatever")
    assert res.status_code in (401, 403)


def test_admin_guard_blocks_system_user(client, system_user):
    # manually craft token for system user
    from file_processing_backend.user import create_access_token
    token = create_access_token({"sub": system_user.user_id, "role": "system"})

    res = client.get(
        "/admin/users",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403
    assert res.json()["detail"] == "Admin access required"
