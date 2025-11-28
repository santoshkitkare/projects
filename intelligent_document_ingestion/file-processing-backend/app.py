import json
import os
import uuid
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi import Body
from fastapi import Depends, status

from fastapi.middleware.cors import CORSMiddleware

from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from pydantic import BaseModel


from sqlalchemy import (
    create_engine, Column, String, DateTime, Text, Integer, JSON
)
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import boto3
from config import Base, S3_BUCKET_NAME, AWS_REGION, engine, s3_client, SessionLocal
from helper import get_db, build_s3_key
from user import User, get_current_user, TokenResponse, MeUpdateRequest
from user import require_admin, AdminCreateUserRequest, AdminUserResponse, AdminUpdateUserRequest
from user import get_user_by_username, verify_password, hash_password, create_access_token

# load_dotenv()

# # ======== Config ========
# DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/filedb")
# S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "your-bucket-name")
# AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")

# if not S3_BUCKET_NAME:
#     raise RuntimeError("S3_BUCKET_NAME env var is required")

# engine = create_engine(DATABASE_URL)
# SessionLocal = sessionmaker(bind=engine)
# Base = declarative_base()

# s3_client = boto3.client("s3", region_name=AWS_REGION, 
#                          config=boto3.session.Config(signature_version="s3v4",
#                                                      s3={"addressing_style": "virtual", "use_arn_region": True}))

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

# # ---- Create default admin if no users exist ----
# from passlib.context import CryptContext

# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# def seed_admin():
#     db = SessionLocal()
#     existing = db.query(User).first()
#     if not existing:
#         admin = User(
#             username="admin",
#             password_hash=pwd_context.hash("admin@123"),
#             role="admin"
#         )
#         db.add(admin)
#         db.commit()
#         print("🚀 Default admin created: username='admin' password='admin@123'")
#     db.close()

# seed_admin()

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
    
# Upload processing 
class UploadCompleteRequest(BaseModel):
    fileId: str

class UploadCompleteResponse(BaseModel):
    message: str


# ======== FastAPI App ========
app = FastAPI(title="File Processing Backend")
# Creste admin usedr if not exists
# seed_admin()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or ["http://localhost:8501"] for Streamlit
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# # ======== Helper ========
# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()


# def build_s3_key(user_id: str, file_id: str, extension: str) -> str:
#     now = datetime.utcnow()
#     return f"uploads/{user_id}/{now.year}/{now.month:02}/{now.day:02}/{file_id}.{extension}"


# ======== Routes ========

@app.post("/api/v1/uploads/request", response_model=UploadResponse)
def request_upload(payload: UploadRequest = Body(...),
                   current_user: User = Depends(get_current_user),):
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
        user_id=current_user.user_id,   # use logged-in user,
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


sqs = boto3.client("sqs", region_name=AWS_REGION)

@app.post("/api/v1/uploads/complete", response_model=UploadCompleteResponse)
def upload_complete(body: UploadCompleteRequest = Body(...)):
    db = next(get_db())

    doc = db.query(Document).filter(Document.file_id == body.fileId).first()
    if not doc:
        raise HTTPException(status_code=404, detail="fileId not found")

    # Update DB
    doc.status = "processing"
    db.commit()

    # Send message to SQS
    message = {
        "fileId": doc.file_id,
        "userId": doc.user_id,
        "fileType": doc.file_type,
        "s3Location": {
            "bucket": S3_BUCKET_NAME,
            "key": doc.s3_key
        }
    }

    try:
        sqs.send_message(
            QueueUrl=os.getenv("SQS_QUEUE_URL"),
            MessageBody=json.dumps(message)
        )
    except Exception as e:
        # If SQS push fails, revert status
        doc.status = "pending"
        doc.error = f"SQS push failed: {e}"
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))

    return UploadCompleteResponse(message="Upload processed & job queued successfully")


@app.get("/api/v1/uploads/user/{userId}")
def list_user_docs(current_user: User = Depends(get_current_user)):
    db = next(get_db())
    docs = db.query(Document)\
             .filter(Document.user_id == current_user.user_id)\
             .order_by(Document.upload_time.desc())\
             .all()
    return [
        {
            "fileId": d.file_id,
            "fileName": d.file_name,
            "status": d.status,
            "uploadedAt": d.upload_time.isoformat() if d.upload_time else None,
            "completedAt": d.completed_time.isoformat() if d.completed_time else None,
            "error": d.error,
        }
        for d in docs
    ]


@app.get("/api/v1/uploads/user/{user_id}/history")
def get_history(user_id: str):
    db = next(get_db())
    docs = (
        db.query(Document)
        .filter(Document.user_id == user_id)
        .order_by(Document.upload_time.desc())
        .limit(50)
        .all()
    )
    response = []
    for d in docs:
        response.append({
            "fileId": d.file_id,
            "fileName": d.file_name,
            "status": d.status,
            "uploadedAt": d.upload_time.isoformat() if d.upload_time else None,
            "completedAt": d.completed_time.isoformat() if d.completed_time else None,
            "error": d.error,
        })
    return response


@app.get("/api/v1/uploads/{file_id}/download")
def download(file_id: str):
    db = next(get_db())
    doc = db.query(Document).filter(Document.file_id == file_id).first()
    if not doc:
        raise HTTPException(404, "Not found")

    url = s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": S3_BUCKET_NAME, "Key": doc.s3_key},
        ExpiresIn=600,
    )
    return {"downloadUrl": url}

@app.post("/api/v1/uploads/{file_id}/retry")
def retry(file_id: str):
    db = next(get_db())
    doc = db.query(Document).filter(Document.file_id == file_id).first()
    if not doc:
        raise HTTPException(404, "Not found")

    sqs = boto3.client("sqs", region_name=AWS_REGION)
    sqs.send_message(
        QueueUrl=os.getenv("SQS_QUEUE_URL"),
        MessageBody=json.dumps({
            "fileId": doc.file_id,
            "userId": doc.user_id,
            "fileType": doc.file_type,
            "s3Location": {
                "bucket": S3_BUCKET_NAME,
                "key": doc.s3_key
            }
        })
    )

    doc.status = "pending"
    doc.error = None
    db.commit()
    return {"message": "Retry triggered"}


@app.delete("/api/v1/uploads/{file_id}")
def delete_file(file_id: str):
    db = next(get_db())
    doc = db.query(Document).filter(Document.file_id == file_id).first()
    if not doc:
        raise HTTPException(404, "Not found")

    s3_client.delete_object(Bucket=S3_BUCKET_NAME, Key=doc.s3_key)
    db.delete(doc)
    db.commit()
    return {"message": "Deleted"}


@app.post("/auth/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    db = next(get_db())
    user = get_user_by_username(db, form_data.username)
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    access_token = create_access_token(
        data={"sub": user.user_id, "role": user.role}
    )
    return TokenResponse(
        accessToken=access_token,
        userId=user.user_id,
        username=user.username,
        role=user.role,
    )


@app.put("/me/profile")
def update_profile(
    body: MeUpdateRequest,
    current_user: User = Depends(get_current_user),
):
    db = next(get_db())

    if body.username:
        # Ensure unique
        existing = db.query(User).filter(User.username == body.username).first()
        if existing and existing.user_id != current_user.user_id:
            raise HTTPException(status_code=400, detail="Username already taken")
        current_user.username = body.username

    if body.password:
        current_user.password_hash = hash_password(body.password)

    db.commit()
    return {"message": "Profile updated"}


@app.post("/admin/users", response_model=AdminUserResponse)
def admin_create_user(
    body: AdminCreateUserRequest,
    admin: User = Depends(require_admin),
):
    db = next(get_db())

    if body.role not in ["admin", "system"]:
        raise HTTPException(status_code=400, detail="Invalid role")

    if get_user_by_username(db, body.username):
        raise HTTPException(status_code=400, detail="Username already exists")

    user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        role=body.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return AdminUserResponse(
        userId=user.user_id,
        username=user.username,
        role=user.role,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@app.get("/admin/users", response_model=list[AdminUserResponse])
def admin_list_users(admin: User = Depends(require_admin)):
    db = next(get_db())
    users = db.query(User).order_by(User.created_at.desc()).all()
    return [
        AdminUserResponse(
            userId=u.user_id,
            username=u.username,
            role=u.role,
            created_at=u.created_at,
            updated_at=u.updated_at,
        )
        for u in users
    ]


@app.put("/admin/users/{user_id}")
def admin_update_user(
    user_id: str,
    body: AdminUpdateUserRequest,
    admin: User = Depends(require_admin),
):
    db = next(get_db())
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if body.username:
        existing = get_user_by_username(db, body.username)
        if existing and existing.user_id != user_id:
            raise HTTPException(status_code=400, detail="Username already exists")
        user.username = body.username

    if body.password:
        user.password_hash = hash_password(body.password)

    if body.role:
        if body.role not in ["admin", "system"]:
            raise HTTPException(status_code=400, detail="Invalid role")
        user.role = body.role

    db.commit()
    return {"message": "User updated"}


@app.delete("/admin/users/{user_id}")
def admin_delete_user(
    user_id: str,
    admin: User = Depends(require_admin),
):
    db = next(get_db())
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(user)
    db.commit()
    return {"message": "User deleted"}
