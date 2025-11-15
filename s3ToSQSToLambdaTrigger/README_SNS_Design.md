# S3 File Processing with SNS and Lambda

This Terraform project deploys an end-to-end serverless architecture to process files uploaded to an S3 bucket using SNS, Lambda, and DynamoDB.

## Architecture Flow
### 1. S3 Bucket
 - Files are uploaded to an S3 bucket (optionally filtered by prefix/suffix).
 - S3 triggers an SNS notification on object creation.

### 2. SNS Topic
 - The S3 bucket publishes file upload events to an SNS topic.
 - SNS decouples event publishing from processing, allowing multiple subscribers in the future.

### 3. Lambda Function
 - The Lambda function subscribes to the SNS topic.
 - On receiving a notification, it extracts the file key and bucket name.
 - It fetches metadata from the uploaded file in S3 (size, last modified).
 - It stores metadata in a DynamoDB table.

### 4. DynamoDB Table
 - Stores file metadata such as bucket, key, size, last_modified, processed_at, and extension.
 - Acts as a central store for tracking processed files.

## Features
 - Serverless & scalable: Lambda scales automatically based on the SNS message throughput.
 - Decoupled design: SNS allows multiple consumers (Lambda, SQS, email) without changing S3 configuration.
 - Error handling: Optional DLQ can be added to Lambda or SNS for failed processing events.
 - Filtering: S3 event notifications can filter by prefix (uploads/) or suffix (.pdf, .csv, etc.) for selective processing.

## Deployment Instructions
### Prerequisites
 - Terraform >= 1.5
 - AWS CLI configured with proper permissions
 - Python 3.14+ for Lambda function
 - A Lambda ZIP file containing lambda_handler.py and dependencies

### Steps
 1. Clone the repository:
```
git clone <repo-url>
cd <repo-folder>
```
 2. Configure variables in variables.tf or create a terraform.tfvars file.
 3. Initialize Terraform:
```
terraform init
```
 4. Plan the deployment:
```
terraform plan
```
 5. Apply the deployment:
```
terraform apply
```
 6. Upload files to the S3 bucket to trigger processing.

## Lambda Function
 - Runtime: Python 3.14
 - Handler: lambda_handler.handler
 - Environment Variables:
    -  DDB_TABLE → DynamoDB table name
    - RESULT_BUCKET → S3 bucket name

 - Sample Lambda Logic:
    1. Receive SNS message containing S3 object details.
    2. Parse bucket and key from the event.
    3. Fetch object metadata via head_object.
    4. Store metadata in DynamoDB.

## Terraform Resources Created
 - S3 Bucket: File upload source
 - SNS Topic: Event broker
 - SNS Subscription: Lambda function subscriber
 - Lambda Function: Processes files
 - DynamoDB Table: Stores file metadata

## Event Flow Diagram (Textual)
```
S3 Bucket
   │
   ├─> SNS Topic
           │
           └─> Lambda Function
                   │
                   └─> DynamoDB Table
```