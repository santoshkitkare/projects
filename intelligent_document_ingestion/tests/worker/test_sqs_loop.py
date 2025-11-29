from moto import mock_sqs
import boto3
from worker import process_message

@mock_sqs
def test_worker_receives_message():
    sqs = boto3.client("sqs")
    queue = sqs.create_queue(QueueName="document-intelligence-queue")["QueueUrl"]

    sqs.send_message(
        QueueUrl=queue,
        MessageBody='{"file_id": "123", "s3_key": "uploads/123.docx"}'
    )

    msg = sqs.receive_message(QueueUrl=queue)
    assert "Messages" in msg
