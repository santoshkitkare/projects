# tests/test_profile_and_admin_users.py
from file_processing_backend.user import create_access_token


def auth_header_for(user):
    token = create_access_token({"sub": user.user_id, "role": user.role})
    return {"Authorization": f"Bearer {token}"}


def test_me_update_username(client, system_user, db_session):
    headers = auth_header_for(system_user)

    res = client.put(
        "/me/profile",
        json={"username": "newname"},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["message"] == "Profile updated"

    db_session.refresh(system_user)
    assert system_user.username == "newname"


def test_me_update_password(client, system_user, db_session):
    headers = auth_header_for(system_user)

    res = client.put(
        "/me/profile",
        json={"password": "newpassword"},
        headers=headers,
    )
    assert res.status_code == 200

    # check login with new password works
    login_res = client.post(
        "/auth/login",
        data={"username": system_user.username, "password": "newpassword"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login_res.status_code == 200


def test_admin_create_user(client, admin_user, db_session):
    headers = auth_header_for(admin_user)

    res = client.post(
        "/admin/users",
        json={"username": "bob", "password": "bob123", "role": "system"},
        headers=headers,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["username"] == "bob"
    assert body["role"] == "system"

    # check user exists
    from file_processing_backend.user import User
    u = db_session.query(User).filter_by(username="bob").first()
    assert u is not None


def test_admin_list_users(client, admin_user):
    headers = auth_header_for(admin_user)
    res = client.get("/admin/users", headers=headers)
    assert res.status_code == 200
    users = res.json()
    assert any(u["username"] == "admin" for u in users)


def test_admin_update_user_role(client, admin_user, db_session):
    headers = auth_header_for(admin_user)
    # create user
    res = client.post(
        "/admin/users",
        json={"username": "promote_me", "password": "x", "role": "system"},
        headers=headers,
    )
    user_id = res.json()["userId"]

    # promote to admin
    res2 = client.put(
        f"/admin/users/{user_id}",
        json={"role": "admin"},
        headers=headers,
    )
    assert res2.status_code == 200

    from file_processing_backend.user import User
    u = db_session.query(User).filter_by(user_id=user_id).first()
    assert u.role == "admin"


def test_admin_delete_user(client, admin_user, db_session):
    headers = auth_header_for(admin_user)

    res = client.post(
        "/admin/users",
        json={"username": "deleteme", "password": "x", "role": "system"},
        headers=headers,
    )
    user_id = res.json()["userId"]

    res2 = client.delete(f"/admin/users/{user_id}", headers=headers)
    assert res2.status_code == 200
    assert res2.json()["message"] == "User deleted"

    from file_processing_backend.user import User
    u = db_session.query(User).filter_by(user_id=user_id).first()
    assert u is None
