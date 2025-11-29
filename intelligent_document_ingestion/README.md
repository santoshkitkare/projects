# 📌 Intelligent Document Ingestion – Full AI-Powered Automation Pipeline

This project implements an end-to-end Intelligent Document Processing (IDP) system that ingests documents, extracts key information using AI + LLMs, and stores structured results in a database — all deployed on AWS using ECS Fargate + RDS + S3 + SQS + ECR + Terraform.

## 🚀 System Architecture
| Component      | Tech Stack                                                |
| -------------- | --------------------------------------------------------- |
| Frontend       | Streamlit (Python)                                        |
| Backend API    | FastAPI + PostgreSQL + SQLAlchemy                         |
| Worker Service | Python + LLMs + SQS + S3                                  |
| AI Extraction  | GPT / Claude-Based Prompting                              |
| Cloud Infra    | AWS ECS Fargate, ECR, RDS PostgreSQL, S3, SQS, CloudWatch |
| IaC            | Terraform                                                 |


## 🔥 Flow Summary

1. User uploads a document from Streamlit Frontend
2. Backend API validates & stores metadata → sends job to SQS
3. Worker reads SQS → downloads file from S3
4. LLM prompts extract structured fields & return insights
5. Worker writes results to RDS PostgreSQL
6. User sees completed extraction in UI dashboard

## 📁 Repository Structure
```
project-root
│── backend/
│── frontend/
│── worker/
│── infra/ (Terraform)
│── README.md
```
## 🛠 Local Development (Optional)
1. Clone repository
git clone https://github.com/<your_repo>/intelligent-document-ingestion.git
cd intelligent-document-ingestion

2. Build Docker images
docker build -t ido-backend ./backend
docker build -t ido-frontend ./frontend
docker build -t ido-worker ./worker

## ☁ Deploying to AWS (Recommended)
1. Create & authenticate ECR repositories
```
aws ecr create-repository --repository-name ido-backend
aws ecr create-repository --repository-name ido-frontend
aws ecr create-repository --repository-name ido-worker
```

2. Login to ECR
```
aws ecr get-login-password --region <region> | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.<region>.amazonaws.com
```

3. Tag & push Docker images to ECR
```
docker tag ido-backend:latest <ACCOUNT_ID>.dkr.ecr.<region>.amazonaws.com/ido-backend:latest
docker tag ido-frontend:latest <ACCOUNT_ID>.dkr.ecr.<region>.amazonaws.com/ido-frontend:latest
docker tag ido-worker:latest <ACCOUNT_ID>.dkr.ecr.<region>.amazonaws.com/ido-worker:latest

docker push <ACCOUNT_ID>.dkr.ecr.<region>.amazonaws.com/ido-backend:latest
docker push <ACCOUNT_ID>.dkr.ecr.<region>.amazonaws.com/ido-frontend:latest
docker push <ACCOUNT_ID>.dkr.ecr.<region>.amazonaws.com/ido-worker:latest
```
## 🧩 Terraform Deployment
1. Update terraform.tfvars (⚠ mandatory)

Replace placeholders according to your AWS setup:
```
aws_region        = "ap-south-1"
vpc_id            = "<YOUR_VPC_ID>"
public_subnet_ids = ["<SUBNET_1>", "<SUBNET_2>"]
private_subnet_ids= ["<PRIVATE_SUBNET_1>", "<PRIVATE_SUBNET_2>"]  # for RDS
allowed_ip        = "<YOUR_PUBLIC_IP>/32"
db_name           = "filedb"
db_username       = "postgres"
db_password       = "<YOUR_DB_PASSWORD>"
secret_key        = "<JWT_SECRET>"
s3_bucket_name    = "<YOUR_BUCKET_NAME>"
sqs_queue_url     = "<YOUR_SQS_QUEUE_URL>"
account_id        = "<YOUR_AWS_ACCOUNT_ID>"
project           = "doc-intelligence"
```

#### 💡 _If you don’t have subnets or VPC → create them first using AWS console or Terraform module_

2. Initialize & apply Terraform
```
bash

cd infra
terraform init
terraform apply
```

3. Scale ECS services after deployment
```
bash

aws ecs update-service --cluster ido-doc-intelligence-cluster --service ido-backend-svc --desired-count 1
aws ecs update-service --cluster ido-doc-intelligence-cluster --service ido-frontend-svc --desired-count 1
aws ecs update-service --cluster ido-doc-intelligence-cluster --service ido-worker-svc --desired-count 1
```
## 🔐 Credentials & Configurations
| Variable       | Where it is used  |
| -------------- | ----------------- |
| DATABASE_URL   | Backend + Worker  |
| SECRET_KEY     | Backend Auth      |
| S3_BUCKET_NAME | Backend + Worker  |
| SQS_QUEUE_URL  | Worker            |
| BACKEND_URL    | Frontend + Worker |


## 📌 Default Admin (Optional)
To create default login (admin / admin@123) — uncomment the block in app.py:
```
python

seed_admin()
```

Run once → then disable it again.

## 📈 Future Enhancements
| Feature                                          | Status |
| ------------------------------------------------ | ------ |
| Multi-tenant / User roles                        | 🔜     |
| Vector DB (FAISS / Pinecone) for semantic search | 🔜     |
| Auto-scaling Worker based on SQS queue depth     | 🔜     |
| OCR + Vision Transformers (LayoutLMv3)           | 🔜     |
| Audit / Analytics Dashboard                      | 🔜     |

## 🧪 Skills Demonstrated

✔ Python, FastAPI, Streamlit
✔ LLM Prompt Engineering & Document Extraction
✔ SQLAlchemy ORM + PostgreSQL
✔ Asynchronous queues (AWS SQS)
✔ Object Storage (S3)
✔ Containerization (Docker)
✔ AWS ECS Fargate scalable microservices architecture
✔ Infrastructure-as-Code with Terraform
✔ CI/CD ready (GitHub Actions / AWS CodePipeline supported)

## 💡 Support

If you deploy this on your AWS and face infra issues (networking, DB, ECS, IAM), feel free to ping — happy to troubleshoot.