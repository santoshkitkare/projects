terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
  backend "s3" {
    bucket = "santosh-s3-bucket-demo"
    key    = "terraform_states/s3-to-sns-to-lambda/terraform.tfstate"
    region = "ap-south-1"
    encrypt = true
  }
}

provider "aws" {
  region = var.region
}

data "aws_caller_identity" "current" {}

# 1) S3 bucket
resource "aws_s3_bucket" "input_bucket" {
  bucket        = var.s3_input_bucket
  force_destroy = true
}

# 2) SNS Topic
resource "aws_sns_topic" "s3_notifications" {
  name = var.sns_topic_name
}

resource "aws_sns_topic_policy" "allow_s3_publish" {
  arn = aws_sns_topic.s3_notifications.arn

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "s3.amazonaws.com"
        }
        Action = "SNS:Publish"
        Resource = aws_sns_topic.s3_notifications.arn
        Condition = {
          ArnLike = {
            "aws:SourceArn" = aws_s3_bucket.input_bucket.arn
          }
        }
      }
    ]
  })
}


# 3) S3 bucket notification → SNS
resource "aws_s3_bucket_notification" "bucket_to_sns" {
  bucket = aws_s3_bucket.input_bucket.id

  topic {
    topic_arn = aws_sns_topic.s3_notifications.arn
    events    = ["s3:ObjectCreated:*"]
    filter_prefix = var.s3_event_prefix
    filter_suffix = var.s3_event_suffix
  }

  depends_on = [aws_sns_topic.s3_notifications]
}

# 4) DynamoDB table for metadata
resource "aws_dynamodb_table" "metadata" {
  name         = var.ddb_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "s3_key"

  attribute {
    name = "s3_key"
    type = "S"
  }
}

# 5) IAM role / policy for Lambda
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
    actions = ["s3:GetObject","s3:HeadObject","s3:ListBucket"]
    resources = [
      aws_s3_bucket.input_bucket.arn,
      "${aws_s3_bucket.input_bucket.arn}/*"
    ]
  }

  statement {
    sid = "DDB"
    actions = ["dynamodb:PutItem","dynamodb:GetItem","dynamodb:UpdateItem"]
    resources = [aws_dynamodb_table.metadata.arn]
  }

  statement {
    sid = "Logs"
    actions = ["logs:CreateLogGroup","logs:CreateLogStream","logs:PutLogEvents"]
    resources = ["arn:aws:logs:${var.region}:${data.aws_caller_identity.current.account_id}:*"]
  }

  statement {
    sid = "SNSInvokeLambda"
    actions = ["lambda:InvokeFunction"]
    resources = ["*"] # Lambda can be invoked by SNS topic
  }
}

resource "aws_iam_role_policy" "lambda_policy_attach" {
  name   = "lambda_policy_inline"
  role   = aws_iam_role.lambda_role.id
  policy = data.aws_iam_policy_document.lambda_policy.json
}

# 6) Lambda function
resource "aws_lambda_function" "processor" {
  filename         = var.lambda_zip_path
  function_name    = var.lambda_name
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_handler_sns.handler"
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

# 7) SNS subscription to Lambda
resource "aws_sns_topic_subscription" "lambda_sub" {
  topic_arn = aws_sns_topic.s3_notifications.arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.processor.arn

  depends_on = [aws_lambda_function.processor]
}

# 8) Allow SNS to invoke Lambda
resource "aws_lambda_permission" "allow_sns" {
  statement_id  = "AllowExecutionFromSNS"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.processor.function_name
  principal     = "sns.amazonaws.com"
  source_arn    = aws_sns_topic.s3_notifications.arn
}

# 9) Outputs
output "s3_bucket" {
  value = aws_s3_bucket.input_bucket.bucket
}

output "sns_topic_arn" {
  value = aws_sns_topic.s3_notifications.arn
}

output "lambda_name" {
  value = aws_lambda_function.processor.function_name
}

output "dynamodb_table" {
  value = aws_dynamodb_table.metadata.name
}
