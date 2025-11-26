import os
import uuid
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi import Body
from pydantic import BaseModel
from sqlalchemy import (
    create_engine, Column, String, DateTime, Text, Integer, JSON
)
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

# ======== DB Model ========
class Document(Base):
    __tablename__ = "documents"

    file_id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True)
    file_name = Column(String)
    file_type = Column(String)
    file_size = Column(Integer)
    status = Column(String, default="pending")  # pending, processing, completed, failed
    upload_time = Column(DateTime, default=datetime.utcnow)
    completed_time = Column(DateTime, nullable=True)
    s3_key = Column(String)
    error = Column(Text, nullable=True)
    extracted_metadata = Column(JSON, nullable=True)  # flexible for demo

Base.metadata.create_all(bind=engine)

# ======== Pydantic Schemas ========
class UploadRequest(BaseModel):
    userId: str
    fileName: str
    fileSize: int
    fileType: str

class UploadResponse(BaseModel):
    fileId: str
    uploadUrl: str
    uploadMethod: str = "PUT"
    headers: dict
    expiresIn: int
    s3Key: str

class StatusResponse(BaseModel):
    fileId: str
    status: str
    message: str
    metadata: dict | None = None
    downloadUrl: str | None = None
    lastUpdated: datetime | None = None
    error: str | None = None

# ======== FastAPI App ========
app = FastAPI(title="File Processing Backend")


# ======== Helper ========
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def build_s3_key(user_id: str, file_id: str, extension: str) -> str:
    now = datetime.utcnow()
    return f"uploads/{user_id}/{now.year}/{now.month:02}/{now.day:02}/{file_id}.{extension}"


# ======== Routes ========

@app.post("/api/v1/uploads/request", response_model=UploadResponse)
def request_upload(payload: UploadRequest = Body(...)):
    db = next(get_db())

    if payload.fileSize <= 0:
        raise HTTPException(status_code=400, detail="Invalid file size")

    # Simple allowlist
    allowed = ["application/pdf", "image/jpeg", "image/png", "text/csv",
               "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]
    if payload.fileType not in allowed:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    file_id = str(uuid.uuid4())
    # get extension from filename
    if "." in payload.fileName:
        extension = payload.fileName.split(".")[-1]
    else:
        extension = "bin"

    s3_key = build_s3_key(payload.userId, file_id, extension)

    # Create DB record
    doc = Document(
        file_id=file_id,
        user_id=payload.userId,
        file_name=payload.fileName,
        file_type=payload.fileType,
        file_size=payload.fileSize,
        status="pending",
        s3_key=s3_key,
        upload_time=datetime.utcnow()
    )
    db.add(doc)
    db.commit()

    # Presigned URL
    expires_in = 1800  # 30 min
    try:
        upload_url = s3_client.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": S3_BUCKET_NAME,
                "Key": s3_key,
                # "ContentType": payload.fileType,
            },
            HttpMethod="PUT",
            ExpiresIn=expires_in
        )
    except Exception as e:
        # roll back record if needed
        db.delete(doc)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Failed to create presigned URL: {e}")

    return UploadResponse(
        fileId=file_id,
        uploadUrl=upload_url,
        uploadMethod="PUT",
        # headers={"Content-Type": payload.fileType},
        headers={},
        expiresIn=expires_in,
        s3Key=s3_key
    )


@app.get("/api/v1/uploads/{file_id}/status", response_model=StatusResponse)
def get_status(file_id: str):
    db = next(get_db())
    doc = db.query(Document).filter(Document.file_id == file_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="fileId not found")

    message_map = {
        "pending": "File uploaded. Awaiting processing.",
        "processing": "File is being processed.",
        "completed": "Processing completed.",
        "failed": "Processing failed."
    }
    message = message_map.get(doc.status, "Unknown status")

    download_url = None
    if doc.status == "completed":
        # give presigned download URL to original file
        try:
            download_url = s3_client.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": S3_BUCKET_NAME, "Key": doc.s3_key},
                ExpiresIn=1800
            )
        except Exception:
            download_url = None

    return StatusResponse(
        fileId=doc.file_id,
        status=doc.status,
        message=message,
        metadata=doc.extracted_metadata,
        downloadUrl=download_url,
        lastUpdated=doc.completed_time or doc.upload_time,
        error=doc.error
    )
