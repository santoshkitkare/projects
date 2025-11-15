# Multiple File processing in Parallel using Parallel Lambda Processing
# Flow is
Upload File to S3 Bucket -> SQS Notification with Batch Size = 1 -> Lambda Trigger -> Read Records and extarct metadata, file size, extention -> Store Data in DynamoDB table

## Terraform Deploy Step:
### Notes & deploy steps (Terraform)
1. Place your Lambda handler.py in lambda/ and zip into s3_processor.zip (or set lambda_zip_path to wherever your zip is).
Note: Create zip file command in powershell:
powershell Compress-Archive -Path lambda_handler_sns.py -DestinationPath ../sns_s3_file_processing_parallel_lambda.zip -Force
2. cd lambda && zip -r ../s3_processor.zip .
3. terraform init
4. terraform apply -auto-approve -var 's3_input_bucket=your-unique-bucket-name'
5. Upload a file to s3://your-unique-bucket-name/<prefix> and watch SQS → Lambda fan-out.
6. The visibility_timeout_seconds is set to lambda_timeout + 60 — adjust if you expect longer processing. batch_size defaults to 1 but is configurable via var.

## CloudFormation Template
This CloudFormation stack will create: S3 bucket, SQS queue + DLQ + queue policy, DynamoDB table, Lambda (inline small handler for demo), EventSourceMapping, and S3 notification.
Note: For production: put Lambda code in S3 and reference Code: S3Bucket/S3Key. Inline ZipFile is convenient for testing.


## Key points & tips
 - SQS queue policy is critical. Without the QueuePolicy that allows s3.amazonaws.com to sqs:SendMessage for your bucket ARN, S3 notification creation will fail validation (“Unable to validate the destination”). Both templates include that policy.
 - Region consistency — keep S3, SQS, Lambda in the same region. CloudFormation & Terraform examples above assume same region.
 - Batch size — set batch_size = 1 for one-file-per-Lambda semantics (max isolation). Increase if you want fewer Lambda invocations and can tolerate reprocessing batches on partial failure.
 - Visibility timeout — set SQS visibility_timeout to greater than Lambda timeout to avoid duplicates. Terraform sets it to lambda_timeout + 60.
 - DLQ — messages that fail maxReceiveCount go to DLQ for later analysis. Terraform sets maxReceiveCount=3.
 - Lambda packaging:
    Terraform expects a zip file at var.lambda_zip_path. Zip the handler.py and any libs there.
    CloudFormation demo uses ZipFile inline for quick testing. For larger code, upload zip to S3 and use Code: S3Bucket/S3Key.
- DynamoDB table — included as FileMetadata. Use its name as env var DDB_TABLE.

## Quick troubleshooting checklist if S3 → SQS notification fails
 - Confirm SQS QueuePolicy allows s3.amazonaws.com and aws:SourceArn equals your S3 bucket ARN.
 - Confirm bucket/queue are in same region and account.
 - Check CloudTrail if S3 attempted to send and got AccessDenied.
 - If you used console to add notification earlier and it auto-sent a test event, clear old messages and upload a real file to verify.