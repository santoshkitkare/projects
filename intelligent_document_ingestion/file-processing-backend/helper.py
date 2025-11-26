from datetime import datetime
from config import SessionLocal
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