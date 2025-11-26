import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import boto3

load_dotenv()

# ======== Config ========
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/filedb")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "your-bucket-name")
AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")

if not S3_BUCKET_NAME:
    raise RuntimeError("S3_BUCKET_NAME env var is required")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

s3_client = boto3.client("s3", region_name=AWS_REGION, 
                         config=boto3.session.Config(signature_version="s3v4",
                                                     s3={"addressing_style": "virtual", "use_arn_region": True}))