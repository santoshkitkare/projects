# S3 File Processing – Parallel Execution Pipeline

This project implements a horizontally scalable, event-driven architecture for processing files uploaded to Amazon S3. The workflow leverages S3 Event Notifications, SQS, AWS Lambda, and DynamoDB to ensure reliability, parallelism, and fault tolerance.

# 🚀 High-Level Architecture
S3 Bucket  --->  SQS Queue  --->  Lambda Function  --->  DynamoDB Table
      |                |                |                     |
 File Upload       Message Fanout   Parallel Workers   Persistence Layer

# 🧠 System Workflow (Step-by-Step)
## 1. File Upload to S3 (Trigger Event)
A user (or system) uploads a file to the input S3 bucket.
Amazon S3 generates an ObjectCreated:Put event.
Instead of sending the event directly to Lambda (not scalable), S3 pushes the event to an SQS queue.

### Why SQS?
Handles massive spikes in uploads without dropping events.
Allows Lambda to scale horizontally.
Ensures retries in case Lambda temporarily fails.

## 2. S3 Event Delivered to SQS
The SQS queue receives a message containing:
Bucket name
Object key
File metadata (size, eTag, etc.)
The message structure looks like:
{
  "Records": [
    {
      "eventSource": "aws:s3",
      "s3": {
        "bucket": { "name": "your-bucket" },
        "object": { "key": "uploads/file.pdf", "size": 12345 }
      }
    }
  ]
}

This ensures that even if 1000 files are uploaded together, every event is captured reliably.

## 3. Lambda Triggered by SQS
SQS invokes Lambda with a batch of messages.
Lambda processes each record in parallel.
If one message fails, only that one is retried — not the entire batch.
Inside Lambda:
Parse SQS body
Extract bucket + key
Confirm the file exists using head_object
Read file metadata
Insert record into DynamoDB
Error handling ensures:
Bad messages go to SQS DLQ
Retries follow exponential backoff
No messages are lost

## 4. Parallel Processing
You achieve horizontal scaling through:
Lambda reserved concurrency
SQS message batching
High-throughput SQS polling
This means:
100 files uploaded = 100 Lambda executions
Throughput automatically increases without manual tuning

## 5. DynamoDB Persistence Layer

Every processed file gets a record inserted into DynamoDB:
Field	Description
id	UUID generated per message
bucket	S3 bucket name
key	Object key
size	File size (bytes)
contentType	File MIME type
timestamp	ISO timestamp when Lambda handled it
etag	S3 file checksum

This becomes your single source of truth for:
Auditing
Reporting
Reprocessing
Analytics

# ⚙️ Infrastructure Deployment
The project includes:
Terraform scripts to automatically create:
S3 bucket
SQS queue + DLQ
Lambda function
IAM roles/policies
DynamoDB table
S3 → SQS notifications
CloudFormation template (for teams using CFN workflows)
Both IaC stacks are aligned with the same architecture.

# 🔐 Permission Model (IAM)
Lambda requires:
s3:GetObject
s3:HeadObject
dynamodb:PutItem
logs:CreateLogGroup
sqs:ReceiveMessage
S3 bucket requires:
Permission to publish events to SQS (sqs:SendMessage)
SQS requires:
Access policy to accept messages only from S3
These are already included in your updated Terraform/CFN templates.

## 📈 Scalability Highlights
Challenge	Solution
High file upload volume	SQS decouples load from compute
Parallel processing	Lambda auto-scales
Event reliability	SQS retry + DLQ
State corruption	Each event processed idempotently
Slow downstream system	SQS buffering absorbs pressure

This design is basically “cloud-native best practice” in motion.

## 🧪 Testing the End-to-End Flow
Upload a file:
aws s3 cp sample.pdf s3://your-bucket/uploads/
Verify queue has a message:
aws sqs receive-message --queue-url <queue-url>
Check Lambda logs:
CloudWatch → Log groups → /aws/lambda/s3-file-processor
Verify DynamoDB entry:
aws dynamodb scan --table-name FileMetadataTable
All pieces should line up cleanly.