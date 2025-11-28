resource "aws_ecr_repository" "backend" {
  name = "ido-backend"
}

resource "aws_ecr_repository" "frontend" {
  name = "ido-frontend"
}

resource "aws_ecr_repository" "worker" {
  name = "ido-worker"
}
