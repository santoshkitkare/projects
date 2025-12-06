import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import boto3

load_dotenv()

# ======== Config ========
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/filedb"
)
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "your-bucket-name")
AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")

if not S3_BUCKET_NAME:
    raise RuntimeError("S3_BUCKET_NAME env var is required")

# ---- Pooled engine for high concurrency ----
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=int(os.getenv("DB_POOL_SIZE", "20")),        # base pool
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "30")),  # burst capacity
    pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "30")),
)

SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

s3_client = boto3.client(
    "s3",
    region_name=AWS_REGION,
    config=boto3.session.Config(
        signature_version="s3v4",
        s3={"addressing_style": "virtual", "use_arn_region": True},
    ),
)
