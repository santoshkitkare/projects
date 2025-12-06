# tests/test_uploads_and_status.py
import json
from datetime import datetime
from file_processing_backend.user import create_access_token
from file_processing_backend.app import Document


def auth_header_for(user):
    token = create_access_token({"sub": user.user_id, "role": user.role})
    return {"Authorization": f"Bearer {token}"}


class DummySQS:
    def __init__(self):
        self.messages = []

    def send_message(self, QueueUrl, MessageBody):
        self.messages.append({"QueueUrl": QueueUrl, "Body": MessageBody})
        return {"MessageId": "msg-1"}


def test_request_upload_creates_doc_and_presign(
    client, system_user, db_session, monkeypatch
):
    headers = auth_header_for(system_user)

    # fake presigned URL so we don't call real S3
    import file_processing_backend.config as cfg
    monkeypatch.setattr(
        cfg.s3_client,
        "generate_presigned_url",
        lambda ClientMethod, Params, HttpMethod, ExpiresIn: "https://fake-presigned-url",
    )

    payload = {
        "userId": system_user.user_id,
        "fileName": "test.pdf",
        "fileSize": 1234,
        "fileType": "application/pdf",
    }

    res = client.post("/api/v1/uploads/request", json=payload, headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["uploadUrl"].startswith("https://fake-presigned-url")
    assert body["fileId"]
    assert body["s3Key"].startswith("uploads/")

    # doc exists in DB
    doc = db_session.query(Document).filter_by(file_id=body["fileId"]).first()
    assert doc is not None
    assert doc.status == "pending"
    assert doc.file_name == "test.pdf"


def test_upload_complete_sets_processing_and_sends_sqs(
    client, system_user, db_session, monkeypatch
):
    headers = auth_header_for(system_user)

    # create a doc first
    doc = Document(
        file_id="file-123",
        user_id=system_user.user_id,
        file_name="demo.pdf",
        file_type="application/pdf",
        file_size=100,
        status="pending",
        s3_key="uploads/demo.pdf",
        upload_time=datetime.utcnow(),
    )
    db_session.add(doc)
    db_session.commit()

    # fake SQS
    from file_processing_backend import app as app_mod
    dummy_sqs = DummySQS()
    monkeypatch.setattr(app_mod, "sqs", dummy_sqs)

    res = client.post(
        "/api/v1/uploads/complete",
        json={"fileId": "file-123"},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["message"] == "Upload processed & job queued successfully"

    db_session.refresh(doc)
    assert doc.status == "processing"

    # SQS message captured
    assert len(dummy_sqs.messages) == 1
    msg = json.loads(dummy_sqs.messages[0]["Body"])
    assert msg["fileId"] == "file-123"


def test_get_status_returns_metadata_and_download_url(
    client, system_user, db_session, monkeypatch
):
    # fake doc in completed state
    doc = Document(
        file_id="file-999",
        user_id=system_user.user_id,
        file_name="done.pdf",
        file_type="application/pdf",
        file_size=100,
        status="completed",
        s3_key="uploads/done.pdf",
        upload_time=datetime.utcnow(),
        completed_time=datetime.utcnow(),
        extracted_metadata={"processedAt": "2025-11-26T00:00:00Z"},
    )
    db_session.add(doc)
    db_session.commit()

    # fake S3 download URL
    import file_processing_backend.config as cfg
    monkeypatch.setattr(
        cfg.s3_client,
        "generate_presigned_url",
        lambda ClientMethod, Params, ExpiresIn: "https://fake-download-url",
    )

    res = client.get(f"/api/v1/uploads/{doc.file_id}/status")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "completed"
    assert body["metadata"]["processedAt"] == "2025-11-26T00:00:00Z"
    assert body["downloadUrl"] == "https://fake-download-url"


def test_user_history_endpoint(client, system_user, db_session):
    headers = auth_header_for(system_user)

    # two docs
    d1 = Document(
        file_id="h1",
        user_id=system_user.user_id,
        file_name="a.pdf",
        file_type="application/pdf",
        file_size=1,
        status="pending",
        s3_key="uploads/a.pdf",
        upload_time=datetime.utcnow(),
    )
    d2 = Document(
        file_id="h2",
        user_id=system_user.user_id,
        file_name="b.pdf",
        file_type="application/pdf",
        file_size=1,
        status="completed",
        s3_key="uploads/b.pdf",
        upload_time=datetime.utcnow(),
    )
    db_session.add_all([d1, d2])
    db_session.commit()

    res = client.get(f"/api/v1/uploads/user/{system_user.user_id}", headers=headers)
    assert res.status_code == 200
    data = res.json()
    file_ids = [d["fileId"] for d in data]
    assert "h1" in file_ids and "h2" in file_ids


def test_download_endpoint(client, system_user, db_session, monkeypatch):
    doc = Document(
        file_id="d1",
        user_id=system_user.user_id,
        file_name="x.pdf",
        file_type="application/pdf",
        file_size=1,
        status="completed",
        s3_key="uploads/x.pdf",
        upload_time=datetime.utcnow(),
    )
    db_session.add(doc)
    db_session.commit()

    import file_processing_backend.config as cfg
    monkeypatch.setattr(
        cfg.s3_client,
        "generate_presigned_url",
        lambda *args, **kwargs: "https://fake-download-url",
    )

    res = client.get(f"/api/v1/uploads/{doc.file_id}/download")
    assert res.status_code == 200
    assert res.json()["downloadUrl"] == "https://fake-download-url"


def test_retry_endpoint(client, system_user, db_session, monkeypatch):
    # doc with failed status
    doc = Document(
        file_id="r1",
        user_id=system_user.user_id,
        file_name="fail.pdf",
        file_type="application/pdf",
        file_size=1,
        status="failed",
        error="Some error",
        s3_key="uploads/fail.pdf",
        upload_time=datetime.utcnow(),
    )
    db_session.add(doc)
    db_session.commit()

    # fake SQS send
    from file_processing_backend import app as app_mod
    dummy_sqs = DummySQS()
    monkeypatch.setattr(app_mod, "sqs", dummy_sqs)

    res = client.post(f"/api/v1/uploads/{doc.file_id}/retry")
    assert res.status_code == 200
    assert res.json()["message"] == "Retry triggered"

    db_session.refresh(doc)
    assert doc.status == "pending"
    assert doc.error is None
    assert len(dummy_sqs.messages) == 1
