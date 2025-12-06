# tests/conftest.py
import os
import pytest
from fastapi.testclient import TestClient

# --- Force test env vars BEFORE importing app/config ---
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("S3_BUCKET_NAME", "test-bucket")
os.environ.setdefault("AWS_REGION", "ap-south-1")
os.environ.setdefault("SQS_QUEUE_URL", "https://sqs.ap-south-1.amazonaws.com/123456789012/test-queue")
os.environ.setdefault("SECRET_KEY", "test-secret-key")

# Import backend pieces
from file_processing_backend.config import Base, engine, SessionLocal  # adjust module path if needed
from file_processing_backend.app import app
from file_processing_backend.user import User, hash_password
from file_processing_backend.helper import get_db

# --- DB schema init (documents + users etc.) ---
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)


@pytest.fixture(scope="session")
def db_engine():
    return engine


@pytest.fixture
def db_session():
    """Scoped DB session for each test."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture
def client(db_session, monkeypatch):
    """FastAPI TestClient with get_db overridden to use our test session."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


@pytest.fixture
def admin_user(db_session):
    """Seed an admin user for auth tests."""
    user = User(
        username="admin",
        password_hash=hash_password("admin@123"),
        role="admin",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def system_user(db_session):
    """Non-admin (system) user."""
    user = User(
        username="user1",
        password_hash=hash_password("user@123"),
        role="system",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user
