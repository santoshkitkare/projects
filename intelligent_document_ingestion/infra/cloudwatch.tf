resource "aws_cloudwatch_log_group" "backend" {
  name              = "/ecs/ido-backend"
  retention_in_days = 1
}

resource "aws_cloudwatch_log_group" "frontend" {
  name              = "/ecs/ido-frontend"
  retention_in_days = 1
}

resource "aws_cloudwatch_log_group" "worker" {
  name              = "/ecs/ido-worker"
  retention_in_days = 1
}
