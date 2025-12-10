from fastapi import FastAPI, HTTPException, Depends
from typing import List, Dict, Literal
from pydantic import BaseModel, Field, field_validator, EmailStr
import re
###### 
# SQLAlchemy
from sqlalchemy import create_engine, Enum
from sqlalchemy.orm import sessionmaker, declarative_base, Session
import enum
from passlib.context import CryptContext

# JWT Token schema
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from fastapi.security import OAuth2PasswordBearer

# for getting username and password from login form
from fastapi.security import OAuth2PasswordRequestForm
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


# Define a CryptContext with bcrypt as the scheme
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

DATABASE_URL = "postgresql://postgres:postgres@127.0.0.1:5433/mytestdb"
# JWT Core configuration
SECRET_KEY = "ILoveCodingWantToLearnML"     # used to sign tokens. In real life: environment var, long and random. 
ALGORITHM = "HS256"                         # ALGORITHM → standard is "HS256" (HMAC with SHA-256).
ACCESS_TOKEN_EXPIRE_MINUTES = 15            # how long a normal token is valid.
REFRESH_TOKEN_EXPIRE_DAYS = 7               # for refresh token, usually days/weeks.

engine = create_engine(
    url = DATABASE_URL,
    echo=True, 
    
)

SessionMaker = sessionmaker(
    bind=engine,
    autoflush=False,
)

Base = declarative_base()

#####
# Create DB session
def get_db():
    db = SessionMaker()
    try:
        yield db
    finally:
        db.close()
    

#####
# Models
from sqlalchemy import Column, Integer, String, Float
    
class UserRole(enum.Enum):
    admin = "admin"
    system = "system"
    
class Users(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True, nullable=False)
    name = Column(String(100), primary_key=False, index=True, nullable=False)
    password = Column(String(255), index=False, nullable=False)
    mobile_number = Column(String(15), index=False, nullable=True)
    email = Column(String(100), index=False, nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    
class UserCreate(BaseModel):
    name: str = Field(..., min_length=4, max_length=30, description="Name of the item")
    password: str = Field(..., min=8, description="Password for user")
    email: EmailStr
    mobile_number: str
    role: Literal["admin", "system"]
    
    @field_validator("mobile_number")
    def validate_mobile(cls, v):
        mb = v.strip().replace(' ', '')
        if not len(v) or len(v) < 10 or len(re.sub(r"[a-zA-Z]", "", v)) < 10:
            raise Exception("Mobile number should contains at least 10 numeric chars")
        return v
    
class UserRead(BaseModel):
    id: int
    name: str
    email: EmailStr
    mobile_number: str
    role: Literal["admin", "system"]
    class Config:
        from_attributes = True
    
    
# login and refresh response model
class Token(BaseModel):
    access_token: str               # the short-lived token used in Authorization: Bearer ...
    refresh_token: str              # long-lived token used to get a new access token
    token_type: str = "bearer"      # usually "bearer" by convention; default so you don’t have to always set it.
    
    
# Model for decoded token payload (internal use)
class TokenPayload(BaseModel):
    sub: str     # subject (user id as string)
    role: str    # user role (admin/system)
    exp: datetime   # expiry time. JWT spec uses exp for expiration.
    type: str    # "access" or "refresh" - to distinguish access token from refresh token.
    
# user = Users(name="santosh", password="santosh", email="santosh@gmail.com", mobile_number="8722555111", role="admin")
# print("####################################################################")
# print(user)
# print("####################################################################")


app = FastAPI(
    title = "General Store Inventory Management",
    description= "General Store",
)

# Table schema
class Items(Base):
    __tablename__ = "stationary"
    id = Column(Integer, primary_key=True, index=True, nullable=False)
    name= Column(String, primary_key=False, index=True, nullable=False)
    price = Column( Float, nullable=False)
    in_stock_count = Column(Integer, nullable=False)

# Pydantic validation classes
class Item(BaseModel):
    name: str = Field(..., min_length=4, max_length=30, description="Name of the item")
    price: float = Field(..., min = 1, description="Price of the item")
    in_stock_count: int = Field(..., min = 1, description="Number of item present in store")

class ItemRead(Item):
    id : int
    class Config:
        from_attributes = True

# Pydantic model for PUT method which will update all the fields    
class ItemPut(Item):
    pass
    
# Pydantic model for PATCH method which will update either one or all the fields
class ItemPatch(BaseModel):
    name: str | None = Field(default=None, min_length=4, max_length=30, description="Name of the item")
    price: float | None = Field(default=None, min = 1, description="Price of the item")
    in_stock_count: int | None = Field(default=None, min = 1, description="Number of item present in store")


# dummy_items = [
#     Item(name="Computer", price=30000, inventory=5),
#     Item(name="Mouse", price=300, inventory=200),
#     Item(name="Keyboard", price=300, inventory=200),
# ]

Base.metadata.create_all(bind=engine)



def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Users:
    # Decode token
    payload = decode_token(token)
    
    # Ensure token is access token, not refresh
    if payload.type != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")
    
    # Get user from DB using sub (user id)
    user = db.query(Users).filter(Users.id == int(payload.sub)).first()
    # Handle missing user
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user

def is_admin_user(user : Users = Depends(get_current_user)) -> bool:
    if user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return user

    
# JWT Token creation 
def create_token(data: dict, expires_delta: timedelta, token_type: str) -> str:
    # Copy input data
    to_encode = data.copy()
    
    # Calculate expiry time
    expire = datetime.now(timezone.utc) + expires_delta
    
    # Add exp and type to payload
    to_encode.update({"exp": expire, "type": token_type})
    
    # Encode with jwt.encode
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt # returns a string → this is your token


# Access token builder
def create_access_token(user: UserRead) -> str:
    # Decide what to store in token
    return create_token(
        data={
            "sub": str(user.id),
            "role": user.role.value,
        },
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        token_type="access",
    )
    
    
# Refresh token builder
def create_refresh_token(user: UserRead):
    # Decide what to store in token
    return create_token(
        data={
            "sub": str(user.id),
            "role": user.role.value,
        },
        expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        token_type="refresh",
    )
    
    
def decode_token(token: str) -> TokenPayload:
    try:
        # jwt.decode verifies signature
        # checks exp for expiry
        # returns a dict if valid
        # raises JWTError if invalid/expired
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return TokenPayload(**payload)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


@app.get("/")
def heartbeats()-> Dict:
    return {"Status": "Working"}

@app.get("/items", response_model=List[ItemRead])
def get_items(db : Session = Depends(get_db), 
                user : Users = Depends(get_current_user)) -> List[ItemRead]:
    records = db.query(Items).all()
    return records

@app.get("/items/{item_id}", response_model=List[ItemRead])
def get_items(item_id : int, db : Session = Depends(get_db),
              user : Users = Depends(get_current_user)) -> List[ItemRead]:
    records = db.query(Items).filter(Items.id == item_id).all()
    return records
    # return dummy_items

@app.post("/item", response_model=ItemRead)
def add_item(item: Item, db: Session = Depends(get_db), 
             current_user : Users = Depends(is_admin_user)) -> ItemRead:
    """
    ############## using local global data #############
    global dummy_items
    print(f"Dummy Item: {dummy_items}")
    item_names_list = [i.name for i in dummy_items]
    
    print(f"Present items : {item_names_list}")
    if item.name in item_names_list:
        raise HTTPException(status_code=500, detail="Item already present")
    dummy_items.append(item)
    return item
    """
    # check whether item already present in database
    record = db.query(Items).filter(Items.name==item.name).all()
    if record:
        raise HTTPException(status_code=500, detail="Item already present")
    
    new_item = Items(
        name = item.name,
        price = item.price,
        in_stock_count = item.in_stock_count
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    
    return new_item


@app.delete("/item/delete/{item_id}", response_model=Item)
def delete_item(item_id: int, db: Session = Depends(get_db), 
                current_user : Users = Depends(is_admin_user)):
    """
    ################# using local data ############
    global dummy_items
    print(f"Dummy Item: {dummy_items}")
    item_names_list = [i.name for i in dummy_items]
    
    if item_name not in item_names_list:
        raise HTTPException(status_code=500, detail="Item not present")
    
    deleted_item =  [item for item in dummy_items if item.name in item_name]
    dummy_items = [item for item in dummy_items if item.name not in item_name]
    print(dummy_items)
    return deleted_item[0]
    """
    item = db.query(Items).filter(Items.id == item_id).first()
    if item:
        db.delete(item)
        db.commit()
        return Item(name=item.name, price=item.price, in_stock_count=item.in_stock_count)
    else:
        raise HTTPException(status_code=500, detail=f"{item_id} not present")
    

@app.put("/item/{item_id}", response_model=Item)
def add_item_put(item_id: int, item: ItemPut, 
            db: Session = Depends(get_db),
            current_user: Users = Depends(is_admin_user)) -> Item:
    """
    Update items details matching the name
    """
    # check whether item already present in database
    db_item = db.query(Items).filter(Items.id==item_id).first()
    if db_item is None:
        raise HTTPException(status_code=404, detail=f"Item id {item_id} not present")
    
    db_item.name = item.name
    db_item.price = item.price,
    db_item.in_stock_count = item.in_stock_count
    
    db.commit()
    db.refresh(db_item)
    
    return db_item


@app.patch("/item/{item_id}", response_model=ItemRead)
def add_item_patch(item_id: int, item: ItemPatch, 
            db: Session = Depends(get_db),
            current_user: Users = Depends(is_admin_user)) -> ItemRead:
    """
    Update items details matching the name
    """    
    # check whether item already present in database
    db_item = db.query(Items).filter(Items.id==item_id).first()
    if db_item is None:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not present")
    
    if item.name:
        db_item.name = item.name
    if item.price:
        db_item.price = item.price
    if item.in_stock_count:
        db_item.in_stock_count = item.in_stock_count
    
    db.commit()
    db.refresh(db_item)
    
    return db_item



@app.post("/register", response_model=UserRead)
def register_user(user: UserCreate, 
                db : Session = Depends(get_db),
                current_user: Users = Depends(is_admin_user)) -> UserRead:
    # Check if user already exist
    db_user = db.query(Users).filter(Users.name == user.name).first()
    if db_user:
        raise HTTPException(status_code=500, detail="User already exists")

    # Hash the password
    hashed_password = pwd_context.hash(user.password)
    print(f"Hashed password: {hashed_password}")
    
    db_user = Users(
        name = user.name,
        password = hashed_password,
        mobile_number = user.mobile_number,
        email = user.email,
        role = user.role
    )
    
    # If user.role == "admin" then only
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    print(f"================== {db_user} ==================")
    return UserRead(
        id=db_user.id,
        name=db_user.name,
        email=db_user.email,
        mobile_number=db_user.mobile_number,
        role=db_user.role.value  # <--- .value converts Enum → string
    )
    
class UserLogin(BaseModel):
    name: str
    password: str
    
class UserAuth(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    
# Refresh token input model
class RefreshRequest(BaseModel):
    refresh_token: str
    
    
# get if my username
@app.get("/me", response_model=UserRead)
def read_me(db_user: Users = Depends(get_current_user)):
    return UserRead(
        id=db_user.id,
        name=db_user.name,
        email=db_user.email,
        mobile_number=db_user.mobile_number,
        role=db_user.role.value  # <--- .value converts Enum → string
    )


@app.post("/login", response_model=UserAuth)
def login_user(form_data: OAuth2PasswordRequestForm = Depends(), db : Session = Depends(get_db)) -> UserAuth:
    # Check if user already exist
    db_user = db.query(Users).filter(Users.name == form_data.username).first()
    if not db_user:
        raise HTTPException(status_code=401, detail="Invalid User name")
    
    # Hash the password
    print(f"Input password: {form_data.password}")
    hashed_password = pwd_context.hash(form_data.password)
    print(f"Hashed password: {hashed_password}")
    print(f"DB Password password: {db_user.password}")
    
    if not pwd_context.verify(form_data.password, db_user.password):
    # if hashed_password != db_user.password:
        raise HTTPException(status_code=401, detail="Unauthorized user")
    
    access_token = create_access_token(db_user)
    refresh_token = create_refresh_token(db_user)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }
    


@app.post("/refresh", response_model=UserAuth)
def refresh_tokens(body: RefreshRequest, db: Session = Depends(get_db)):
    # Decode the provided refresh token
    payload = decode_token(body.refresh_token)
    print(f"Payload : {payload}")
    
    # Check type is refresh
    if payload.type != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")
    
    # Find user in DB
    user = db.query(Users).filter(Users.id == int(payload.sub)).first()
    
    # Handle missing user
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    # Create fresh tokens
    new_access_token = create_access_token(user)
    new_refresh_token = create_refresh_token(user)
    
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }
    
    
from fastapi import Query

@app.get("/searchItems", response_model=Dict)
def get_items(
    search: str | None = Query(default=None, description="Search term for item name"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    user: Users = Depends(get_current_user)
):
    query = db.query(Items)

    # apply search filter (optional)
    if search:
        query = query.filter(Items.name.ilike(f"%{search}%"))

    # count total
    total = query.count()

    # pagination offset
    skip = (page - 1) * limit

    # fetch rows
    records = query.offset(skip).limit(limit).all()

    return {
        "data": records,
        "meta": {
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total // limit) + (1 if total % limit else 0),
        }
    }
