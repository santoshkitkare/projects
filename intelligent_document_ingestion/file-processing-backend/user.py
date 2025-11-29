from sqlalchemy import Boolean
import uuid
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import timedelta
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from fastapi import Depends, status
from datetime import datetime
from sqlalchemy import Column, String, DateTime
import os
from config import Base, engine, SessionLocal
from helper import get_db
from pydantic import BaseModel
from fastapi import HTTPException

# === Auth Config ===
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

class User(Base):
    __tablename__ = "users"

    user_id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default="system")  # "admin" or "system"
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_user_by_username(db, username: str) -> User | None:
    return db.query(User).filter(User.username == username).first()


class TokenData(BaseModel):
    user_id: str
    role: str

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db=Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        role: str = payload.get("role")
        if user_id is None or role is None:
            raise credentials_exception
        token_data = TokenData(user_id=user_id, role=role)
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.user_id == token_data.user_id).first()
    if user is None:
        raise credentials_exception
    return user

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


class TokenResponse(BaseModel):
    accessToken: str
    tokenType: str = "bearer"
    userId: str
    username: str
    role: str


class MeUpdateRequest(BaseModel):
    username: str | None = None
    password: str | None = None


class AdminCreateUserRequest(BaseModel):
    username: str
    password: str
    role: str  # "admin" or "system"

class AdminUserResponse(BaseModel):
    userId: str
    username: str
    role: str
    created_at: datetime
    updated_at: datetime


class AdminUpdateUserRequest(BaseModel):
    username: str | None = None
    password: str | None = None
    role: str | None = None  # "admin" or "system"


Base.metadata.create_all(bind=engine)



def seed_admin():
    db = SessionLocal()
    existing = db.query(User).first()
    if not existing:
        admin = User(
            username="admin",
            password_hash=pwd_context.hash("admin@123"),
            role="admin"
        )
        db.add(admin)
        db.commit()
        print("🚀 Default admin created: username='admin' password='admin@123'")
    db.close()

seed_admin()