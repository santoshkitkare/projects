variable "region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "ap-south-1"
}

variable "s3_input_bucket" {
  description = "Name of the S3 bucket where files will be uploaded"
  type        = string
  default     = "s3-file-processor-input-bucket-sns-demo"
}

variable "lambda_name" {
  description = "Name of the Lambda function"
  type        = string
  default     = "s3-file-processor-sns"
}

variable "lambda_timeout" {
  description = "Timeout for Lambda in seconds"
  type        = number
  default     = 30
}

variable "lambda_memory" {
  description = "Memory for Lambda in MB"
  type        = number
  default     = 512
}

variable "ddb_table_name" {
  description = "DynamoDB table for storing file metadata"
  type        = string
  default     = "FileMetadataTableSns"
}

variable "lambda_zip_path" {
  description = "Path to Lambda deployment package zip"
  type        = string
  default     = "../lambda/sns_s3_file_processing_parallel_lambda.zip"
}

variable "s3_event_prefix" {
  description = "Optional prefix filter for S3 events"
  type        = string
  default     = "uploads/"
}

variable "s3_event_suffix" {
  description = "Optional suffix filter for S3 events"
  type        = string
  default     = ""
}

variable "sns_topic_name" {
  description = "Name of the SNS topic"
  type        = string
  default     = "s3-file-upload-topic"
}

variable "sns_subscription_protocol" {
  description = "Protocol for SNS subscription (lambda)"
  type        = string
  default     = "lambda"
}
