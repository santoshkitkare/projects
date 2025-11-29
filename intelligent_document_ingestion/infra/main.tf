terraform {
  backend "s3" {
    bucket         = "santosh-s3-bucket-demo"
    key            = "terraform_states/intelligent-document-ingestion/terraform.tfstate"
    region         = "ap-south-1"
    encrypt        = true
  }
}

# 1️⃣ Security Group for RDS
resource "aws_security_group" "rds_sg" {
  name        = "${var.project}-rds-sg"
  description = "Allow PostgreSQL traffic"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ip]  # 🔐 restrict to your IP
  }

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_sg.id]   # ECS tasks
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# 2️⃣ Subnet Group (RDS must stay in private subnets ideally)
resource "aws_db_subnet_group" "rds_subnet_group" {
  name       = "${var.project}-rds-subnet-group"
  subnet_ids = var.private_subnet_ids
}

# 3️⃣ PostgreSQL RDS instance
resource "aws_db_instance" "postgres" {
  identifier              = "${var.project}-postgres"
  engine                  = "postgres"
  engine_version          = "16.6"
  instance_class          = var.instance_type
  allocated_storage       = 20
  db_subnet_group_name    = aws_db_subnet_group.rds_subnet_group.name
  vpc_security_group_ids  = [aws_security_group.rds_sg.id]
  publicly_accessible     = false
  skip_final_snapshot     = true

  db_name                 = var.db_name
  username                = var.db_username
  password                = var.db_password

  performance_insights_enabled = false
  backup_retention_period      = 1
  deletion_protection          = false

  tags = {
    Name    = "${var.project}-postgres"
    Project = var.project
  }
}