variable "aws_region" {
  type    = string
  default = "ap-south-1"
}

variable "vpc_id" {
  type        = string
  description = "Existing VPC ID"
}

variable "public_subnet_ids" {
  type        = list(string)
  description = "List of public subnet IDs for ECS tasks"
}

variable "private_subnet_ids" {
  type        = list(string)
  description = "List of public subnet IDs for ECS tasks"
}

variable "allowed_ip" {
  type        = string
  description = "Your public IP with /32 for UI/API access"
  default     = "0.0.0.0/0"
}

variable "db_url" {
  type        = string
  description = "Postgres DATABASE_URL for backend/worker"
}

variable "s3_bucket_name" {
  type = string
}

variable "sqs_queue_url" {
  type = string
}

variable "desired_count_backend" {
  # type = integer
  default = 0
}

variable "desired_count_frontend" {
  # type = integer
  default = 0
}

variable "desired_count_worker" {
  # type = integer
  default = 0
}

variable "secret_key" {
  type      = string
  sensitive = true
}

variable "account_id" {
  type        = string
  description = "Your AWS account ID (for ECR URLs)"
}

variable "project" {}

variable "db_name" {}
variable "db_username" {}
variable "db_password" {}
variable "instance_type" {
  default = "db.t3.micro" # free-tier eligible
}

# variable "allowed_sg_ids" {
#  type = list(string)
#   description = "Security groups that are allowed to connect to Redis (e.g. backend SG)"
# }