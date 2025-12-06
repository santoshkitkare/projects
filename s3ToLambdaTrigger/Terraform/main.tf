terraform {
   backend "s3" {
    bucket         = "santosh-s3-bucket-demo"
    key            = "terraform_states/s3-to-sqs-to-lambda/terraform.tfstate"
    region         = "ap-south-1"
    encrypt        = true
  }
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

# 1) S3 bucket
resource "aws_s3_bucket" "input_bucket" {
  bucket = var.s3_input_bucket
  force_destroy = true
}

# 1b) S3 bucket policy allowing Lambda to read objects
resource "aws_s3_bucket_policy" "allow_lambda_read" {
  bucket = aws_s3_bucket.input_bucket.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Sid    = "AllowLambdaReadObjects"
        Effect = "Allow"
        Principal = {
          AWS = aws_iam_role.lambda_role.arn
        }
        Action = [
          "s3:GetObject"
        ]
        Resource = "${aws_s3_bucket.input_bucket.arn}/*"
      },
      {
        Sid    = "AllowLambdaListBucket"
        Effect = "Allow"
        Principal = {
          AWS = aws_iam_role.lambda_role.arn
        }
        Action = [
          "s3:ListBucket"
        ]
        Resource = aws_s3_bucket.input_bucket.arn
      }
    ]
  })
}


# 2) Dead-letter queue (DLQ)
resource "aws_sqs_queue" "dlq" {
  name                      = var.dlq_name
  message_retention_seconds = 1209600
}

# 3) Main SQS queue
resource "aws_sqs_queue" "file_queue" {
  name                       = var.sqs_queue_name
  visibility_timeout_seconds = var.lambda_timeout + 60  # visibility > lambda timeout
  message_retention_seconds  = 1209600

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 3
  })
}

# 4) SQS queue policy allowing S3 to SendMessage
data "aws_iam_policy_document" "s3_to_sqs" {
  statement {
    principals {
      type        = "Service"
      identifiers = ["s3.amazonaws.com"]
    }
    actions = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.file_queue.arn]

    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values   = [aws_s3_bucket.input_bucket.arn]
    }
  }
}

resource "aws_sqs_queue_policy" "allow_s3" {
  queue_url = aws_sqs_queue.file_queue.id
  policy    = data.aws_iam_policy_document.s3_to_sqs.json
}

# 5) DynamoDB table for metadata
resource "aws_dynamodb_table" "metadata" {
  name         = var.ddb_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "s3_key"

  attribute {
    name = "s3_key"
    type = "S"
  }
}

# 6) IAM role / policy for Lambda
data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda_role" {
  name               = "${var.lambda_name}_role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

data "aws_iam_policy_document" "lambda_policy" {
  statement {
    sid = "S3Access"
    actions = [
      "s3:GetObject",
      "s3:HeadObject",
      "s3:ListBucket"
    ]
    resources = [
      aws_s3_bucket.input_bucket.arn,
      "${aws_s3_bucket.input_bucket.arn}/*"
    ]
  }

  statement {
    sid = "DDB"
    actions = [
      "dynamodb:PutItem",
      "dynamodb:GetItem",
      "dynamodb:UpdateItem"
    ]
    resources = [aws_dynamodb_table.metadata.arn]
  }

  statement {
    sid = "Logs"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["arn:aws:logs:${var.region}:${data.aws_caller_identity.current.account_id}:*"]
  }

  statement {
    effect = "Allow"
    actions = [
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes",
      "sqs:GetQueueUrl"
    ]
    resources = [aws_sqs_queue.file_queue.arn]
 }
}

data "aws_caller_identity" "current" {}

resource "aws_iam_role_policy" "lambda_policy_attach" {
  name = "lambda_policy_inline"
  role = aws_iam_role.lambda_role.id
  policy = data.aws_iam_policy_document.lambda_policy.json
}

# 7) Lambda function (expects zip at var.lambda_zip_path)
resource "aws_lambda_function" "processor" {
  filename         = var.lambda_zip_path
  function_name    = "s3-file-processor"
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_handler.handler"
  runtime          = "python3.14"
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory
  source_code_hash = filebase64sha256(var.lambda_zip_path)

  environment {
    variables = {
      DDB_TABLE     = aws_dynamodb_table.metadata.name
      RESULT_BUCKET = aws_s3_bucket.input_bucket.bucket
    }
  }
}

# 8) Event source mapping (SQS -> Lambda)
resource "aws_lambda_event_source_mapping" "sqs_mapping" {
  event_source_arn = aws_sqs_queue.file_queue.arn
  function_name    = aws_lambda_function.processor.arn
  batch_size       = var.sqs_batch_size
  enabled          = true
  maximum_batching_window_in_seconds = 0
}

# 9) S3 bucket notification to SQS
resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket = aws_s3_bucket.input_bucket.id
    queue {
        queue_arn     = aws_sqs_queue.file_queue.arn
        events        = ["s3:ObjectCreated:*"]
        filter_prefix = var.s3_event_prefix
        filter_suffix = ""
    }


  depends_on = [aws_sqs_queue_policy.allow_s3]
}

# 10) Outputs
output "s3_bucket" {
  value = aws_s3_bucket.input_bucket.bucket
}
output "sqs_queue_url" {
  value = aws_sqs_queue.file_queue.id
}
output "sqs_queue_arn" {
  value = aws_sqs_queue.file_queue.arn
}
output "lambda_name" {
  value = aws_lambda_function.processor.function_name
}
output "dynamodb_table" {
  value = aws_dynamodb_table.metadata.name
}
