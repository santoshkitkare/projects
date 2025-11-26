import os
import json
from datetime import datetime
import tempfile

import boto3
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()
from app import Base, Document

# extract libs
import PyPDF2
import pytesseract
from PIL import Image
import docx
import pandas as pd


DATABASE_URL = os.getenv("DATABASE_URL")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL")
AWS_REGION = os.getenv("AWS_REGION")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

s3_client = boto3.client("s3", region_name=AWS_REGION)
sqs_client = boto3.client("sqs", region_name=AWS_REGION)


def extract_pdf_text(fpath):
    with open(fpath, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return {
            "text": text[:5000],   # limit size for DB
            "pageCount": len(reader.pages)
        }


def extract_image_text(fpath):
    img = Image.open(fpath)
    text = pytesseract.image_to_string(img)
    return {
        "text": text[:5000],
        "pageCount": 1
    }


def extract_docx_text(fpath):
    document = docx.Document(fpath)
    full_text = "\n".join(p.text for p in document.paragraphs)
    return {
        "text": full_text[:5000],
        "pageCount": None
    }


def extract_csv_info(fpath):
    df = pd.read_csv(fpath, nrows=5)
    return {
        "columns": df.columns.tolist(),
        "sampleRows": df.head(3).to_dict(),
        "pageCount": None
    }


def run_extraction(file_path, file_type):
    if file_type == "application/pdf":
        return extract_pdf_text(file_path)

    elif file_type in ["image/jpeg", "image/png"]:
        return extract_image_text(file_path)

    elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return extract_docx_text(file_path)

    elif file_type == "text/csv":
        return extract_csv_info(file_path)

    else:
        return {"text": "Unsupported format", "pageCount": None}


def process_message(body: dict):
    print("[WORKER] Processing message: ", body)
    file_id = body["fileId"]
    s3_info = body["s3Location"]
    bucket = s3_info["bucket"]
    key = s3_info["key"]

    db = SessionLocal()
    doc = db.query(Document).filter(Document.file_id == file_id).first()
    if not doc:
        db.close()
        return

    doc.status = "processing"
    db.commit()

    try:
        # download to temp file
        # with tempfile.NamedTemporaryFile(delete=False) as tmp:
        #     s3_client.download_file(Bucket=bucket, Key=key, Filename=tmp.name)
        #     extracted = run_extraction(tmp.name, doc.file_type)
        
        tmp = tempfile.NamedTemporaryFile(delete=False)
        tmp_path = tmp.name
        tmp.close()
        try:
            s3_client.download_file(Bucket=bucket, Key=key, Filename=tmp_path)
            extracted = run_extraction(tmp_path, doc.file_type)
            metadata = {
                "processedAt": datetime.utcnow().isoformat() + "Z",
                **extracted
            }
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

        doc.status = "completed"
        doc.completed_time = datetime.utcnow()
        doc.extracted_metadata  = metadata
        doc.error = None
        db.commit()
        print(f"[OK] Real processing done for {file_id}")

    except Exception as e:
        print(f"[ERROR] {file_id} failed: {e}")
        doc.status = "failed"
        doc.error = str(e)
        db.commit()

    finally:
        db.close()


def main():
    print("[WORKER] Running with REAL extraction...")
    while True:
        resp = sqs_client.receive_message(
            QueueUrl=SQS_QUEUE_URL,
            MaxNumberOfMessages=5,
            WaitTimeSeconds=10
        )
        for msg in resp.get("Messages", []):
            body = json.loads(msg["Body"])
            process_message(body)

            sqs_client.delete_message(
                QueueUrl=SQS_QUEUE_URL,
                ReceiptHandle=msg["ReceiptHandle"]
            )


if __name__ == "__main__":
    main()
