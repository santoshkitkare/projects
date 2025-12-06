from fastapi.testclient import TestClient
from moto import mock_s3, mock_sqs
import boto3
from app import app

client = TestClient(app)

@mock_sqs
@mock_s3
def test_upload_flow():
    # mock S3 + SQS
    s3 = boto3.client("s3")
    queue = boto3.client("sqs")
    s3.create_bucket(Bucket="company-document-intelligence")
    q = queue.create_queue(QueueName="document-intelligence-queue")

    response = client.post(
        "/api/v1/uploads/request",
        files={"file": ("hello.txt", b"hello")},
        headers={"Authorization": "Bearer dummy"}
    )

    assert response.status_code == 200
