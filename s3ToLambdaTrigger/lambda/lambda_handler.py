import json
import boto3
from datetime import datetime
import os

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["DDB_TABLE"])  # Make sure table exists

def handler(event, context):
    """
    Lambda triggered by SQS messages.
    Each message contains one S3 event for one uploaded file.
    We extract bucket/key, fetch metadata from S3, and store in DynamoDB.
    """

    print(f"Event received :{event}")
    for record in event.get("Records", []):
        # SQS message body
        body_raw = record.get("body")

        # body_raw contains S3 Event JSON
        body = json.loads(body_raw) if body_raw else record

        if "Event" in body and body["Event"] == "s3:TestEvent":
            print("Skipping S3 test event")
            continue

        s3_info = body["Records"][0]["s3"]
        bucket = s3_info["bucket"]["name"]
        key = s3_info["object"]["key"]

        # Fetch metadata from S3
        print(f"bucket:{bucket} key : {key}")
        head = s3.head_object(Bucket=bucket, Key=key)
        size = head["ContentLength"]
        last_modified = head["LastModified"].isoformat()

        # Write to DynamoDB
        table.put_item(
            Item={
                "s3_key": key,
                "bucket": bucket,
                "file_size": size,
                "last_modified": last_modified,
                "processed_at": datetime.utcnow().isoformat(),
                "extension": key.split(".")[-1]
            }
        )

    return {
        "status": "success",
        "processed_records": len(event.get("Records", [])),
    }
