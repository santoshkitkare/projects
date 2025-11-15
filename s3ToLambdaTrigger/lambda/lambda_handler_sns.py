import json
import boto3
from datetime import datetime

s3 = boto3.client("s3")
ddb = boto3.resource("dynamodb")
table = None  # Will initialize inside handler to get env var

import os

def handler(event, context):
    """
    Lambda triggered by SNS messages containing S3 events.
    Each message may contain multiple S3 events.
    Extract bucket/key, fetch metadata, store in DynamoDB.
    """
    global table
    if table is None:
        table = ddb.Table(os.environ["DDB_TABLE"])

    print(f"Event received: {json.dumps(event)}")
    processed_records = 0

    for record in event.get("Records", []):
        sns_message = record.get("Sns", {}).get("Message")
        if not sns_message:
            continue

        # The SNS message contains the S3 event JSON
        try:
            s3_event = json.loads(sns_message)
        except json.JSONDecodeError:
            print(f"Cannot decode SNS message: {sns_message}")
            continue

        for s3_record in s3_event.get("Records", []):
            s3_info = s3_record.get("s3", {})
            bucket = s3_info.get("bucket", {}).get("name")
            key = s3_info.get("object", {}).get("key")

            if not bucket or not key:
                continue

            # Fetch object metadata
            try:
                head = s3.head_object(Bucket=bucket, Key=key)
                size = head.get("ContentLength")
                last_modified = head.get("LastModified").isoformat()
            except Exception as e:
                print(f"Error fetching object metadata for {bucket}/{key}: {e}")
                continue

            # Write metadata to DynamoDB
            try:
                table.put_item(
                    Item={
                        "s3_key": key,
                        "bucket": bucket,
                        "file_size": size,
                        "last_modified": last_modified,
                        "processed_at": datetime.utcnow().isoformat(),
                        "extension": key.split(".")[-1] if "." in key else ""
                    }
                )
                processed_records += 1
            except Exception as e:
                print(f"Error writing to DynamoDB for {bucket}/{key}: {e}")

    return {
        "status": "success",
        "processed_records": processed_records
    }
