import pytest
from fastapi.testclient import TestClient
from app import app
from db import SessionLocal, User
from passlib.context import CryptContext

client = TestClient(app)
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

@pytest.fixture
def admin_user():
    db = SessionLocal()
    user = User(username="admin", password_hash=pwd.hash("admin@123"), role="admin")
    db.add(user)
    db.commit()
    yield user
    db.query(User).delete()
    db.commit()

def test_login_success(admin_user):
    res = client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "admin@123"
    })
    assert res.status_code == 200
    assert "access_token" in res.json()

def test_login_fail(admin_user):
    res = client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "wrongpassword"
    })
    assert res.status_code == 401
