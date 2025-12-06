variable "region" {
  type    = string
  default = "ap-south-1"
}

variable "s3_input_bucket" {
  type    = string
  default = "s3-file-processor-input-bucket-demo"
}

variable "lambda_name" {
  default = "s3_file_processing_parallel_lambda"
}

variable "lambda_zip_path" {
  type    = string
  default = "../lambda/s3_file_processing_parallel_lambda.zip"
}

variable "sqs_queue_name" {
  type    = string
  default = "file_upload_notification_queue"
}

variable "dlq_name" {
  type    = string
  default = "file_upload_notification_queue-dlq"
}

variable "sqs_batch_size" {
  type    = number
  default = 1
}

variable "lambda_memory" {
  type    = number
  default = 1024
}

variable "lambda_timeout" {
  type    = number
  default = 10
}

variable "ddb_table_name" {
  type    = string
  default = "FileMetadata"
}

variable "s3_event_prefix" {
  type    = string
  default = "uploads/" # e.g. "uploads/"
}

variable "s3_event_suffix" {
  type    = string
  default = "" # e.g. ".csv"
}
