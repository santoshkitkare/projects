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
import google.generativeai as genai 

# extract libs
import PyPDF2
import pytesseract
from PIL import Image
import docx
import pandas as pd
from llm_prompts import build_metadata_prompt


DATABASE_URL = os.getenv("DATABASE_URL")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL")
AWS_REGION = os.getenv("AWS_REGION")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

s3_client = boto3.client("s3", region_name=AWS_REGION)
sqs_client = boto3.client("sqs", region_name=AWS_REGION)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
    print(f"{'Model Name':<30} | {'DisplayName':<30}")
    print("-" * 65)
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            # The API returns 'models/gemini-...', but SDK usually needs just 'gemini-...'
            print(f"{m.name:<30} | {m.display_name:<30}")
    print("-" * 65)
    gemini_model = genai.GenerativeModel("gemini-2.5-flash")
else:
    gemini_model = None
    
    
def call_gemini_for_json(prompt: str) -> dict:
    """Call Gemini and parse JSON. On failure, return {}."""
    if not gemini_model:
        return {}

    try:
        resp = gemini_model.generate_content(prompt)
        raw = resp.text.strip()
        # In case model wraps JSON in ``` blocks
        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.startswith("json"):
                raw = raw[len("json"):].strip()
        return json.loads(raw)
    except Exception as e:
        print("[GEMINI ERROR]", e)
        return {}


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
            extracted = run_extraction(tmp_path, doc.file_type) # {"text": ..., "pageCount": ...}
            text = extracted.get("text", "") or ""
            page_count = extracted.get("pageCount")
            
            ai_meta = extract_structured_metadata(text, page_count)
            
            metadata = {
                "processedAt": datetime.utcnow().isoformat() + "Z",
                "documentType": ai_meta.get("documentType", "unknown"),
                "llmMetadata": ai_meta,
                "textPreview": text[:1000],
                "pageCount": page_count,
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


def extract_structured_metadata(text: str, page_count: int | None) -> dict:
    doc_type = classify_document_type(text)
    if doc_type == "To be supported":
        return {
            "documentType": "To be supported",
            "shortSummary": "Document type not yet supported.",
            "rawTextPreview": text[:500],
            "pageCount": page_count,
        }

    prompt = build_metadata_prompt(doc_type, text, page_count)
    meta = call_gemini_for_json(prompt)
    if not isinstance(meta, dict):
        meta = {}

    # Ensure documentType present
    if "documentType" not in meta:
        meta["documentType"] = doc_type
    meta["pageCount"] = page_count
    return meta


SUPPORTED_TYPES = [
    "Question Paper",
    "Research Paper",
    "Invoice",
    "Information Document",
]

def classify_document_type(text: str) -> str:
    """Returns one of SUPPORTED_TYPES or 'To be supported'."""
    snippet = text[:4000] if text else ""
    if not snippet or not gemini_model:
        return "To be supported"

    prompt = f"""
You are a strict document classifier.

You must choose EXACTLY ONE of these categories that best describes the document:

1. Question Paper
2. Research Paper
3. Invoice
4. Information Document

If it does not clearly fit any of the above, return exactly:
To be supported

Rules:
- Return ONLY the category string, nothing else.
- Do NOT explain your choice.

Document text (partial):
\"\"\"{snippet}\"\"\"
"""
    try:
        resp = gemini_model.generate_content(prompt)
        label = resp.text.strip()
    except Exception as e:
        print("[GEMINI CLASSIFICATION ERROR]", e)
        return "To be supported"

    # Normalize a bit
    label = label.replace('"', "").strip()
    if label in SUPPORTED_TYPES:
        return label
    return "To be supported"


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
