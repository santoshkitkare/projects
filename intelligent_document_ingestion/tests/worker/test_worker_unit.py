# tests/test_worker_unit.py
import json
import types
from unittest.mock import MagicMock


def test_worker_process_question_paper(monkeypatch, tmp_path):
    """
    Template:
    - fake S3 download to a temp file
    - fake LLM response: documentType=Question Paper
    - verify backend callback is called with the right payload
    """
    # import your worker
    import file_processing_backend.worker as worker_mod

    # fake S3 client
    def fake_download_file(Bucket, Key, Filename):
        p = tmp_path / "doc.pdf"
        p.write_bytes(b"%PDF-1.4 fake")  # something
        return

    worker_mod.s3_client = types.SimpleNamespace(download_file=fake_download_file)

    # fake LLM classify+extract function
    def fake_extract_metadata(file_path, file_type):
        assert file_path.endswith(".pdf")
        return {
            "processedAt": "2025-11-26T00:00:00Z",
            "documentType": "Question Paper",
            "llmMetadata": {
                "examName": "Demo",
                "subject": "Physics",
            },
        }

    monkeypatch.setattr(worker_mod, "run_llm_pipeline", fake_extract_metadata, raising=False)

    # fake backend callback using requests
    fake_post = MagicMock(return_value=types.SimpleNamespace(status_code=200))
    monkeypatch.setattr(worker_mod.requests, "post", fake_post)

    # build fake SQS body like your System sends
    message = {
        "fileId": "abc-123",
        "userId": "USR001",
        "fileType": "application/pdf",
        "s3Location": {
            "bucket": "company-document-intelligence",
            "key": "uploads/USR001/2025/11/26/abc-123.pdf",
        },
    }

    # call worker function
    worker_mod.process_message(message)

    # assert backend was called once with metadata
    assert fake_post.call_count == 1
    url, = fake_post.call_args[0]
    assert "/api/v1/uploads/" in url
    _, kwargs = fake_post.call_args
    body = kwargs["json"]
    assert body["fileId"] == "abc-123"
    assert body["status"] == "completed"
    assert body["metadata"]["documentType"] == "Question Paper"
