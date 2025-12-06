from fastapi import FastAPI, HTTPException, Depends
from typing import List, Dict, Literal
from pydantic import BaseModel, Field, field_validator, EmailStr
import re
###### 
# SQLAlchemy
from sqlalchemy import create_engine, Enum
from sqlalchemy.orm import sessionmaker, declarative_base, Session
import enum

DATABASE_URL = "postgresql://postgres:postgres@127.0.0.1:5433/mytestdb"

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
class Items(Base):
    __tablename__ = "stationary"
    id = Column(Integer, primary_key=True, index=True, nullable=False)
    name= Column(String, primary_key=False, index=True, nullable=False)
    price = Column( Float, nullable=False)
    in_stock_count = Column(Integer, nullable=False)
    
class UserRole(enum.Enum):
    admin = "admin"
    system = "system"
    
class Users(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), primary_key=True, index=True, nullable=False)
    password = Column(String(100), index=False, nullable=False)
    email = Column(String(100), index=False, nullable=False)
    address = Column(String(255), index=False, nullable=False)
    role = Column(Enum(UserRole), nullable=False)

Base.metadata.create_all(bind=engine)


app = FastAPI(
    title = "General Store Inventory Management",
    description= "General Store",
)


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

class Users(BaseModel):
    name: str = Field(..., min_length=4, max_length=30, description="Name of the item")
    password: str = Field(..., min=8, description="Password for user")
    email: EmailStr
    mobile_number: str = Field(..., min_length=7)
    role: Literal["admin", "system"]
    
    @field_validator("mobile_number")
    def validate_mobile(cls, v):
        mb = v.strip().replace(' ', '')
        if not len(v) or len(v) < 10 or len(re.sub(r"[a-zA-Z]", "", v)) < 10:
            raise Exception("Mobile number should contains at least 10 numeric chars")
        return v
    
    
# user = Users(name="santosh", password="santosh", email="santosh@gmail.com", mobile_number="8722555111", role="admin")
# print("####################################################################")
# print(user)
# print("####################################################################")

# dummy_items = [
#     Item(name="Computer", price=30000, inventory=5),
#     Item(name="Mouse", price=300, inventory=200),
#     Item(name="Keyboard", price=300, inventory=200),
# ]

@app.get("/")
def heartbeats()-> Dict:
    return {"Status": "Working"}

@app.get("/items", response_model=List[ItemRead])
def get_items(db : Session = Depends(get_db)) -> List[ItemRead]:
    records = db.query(Items).all()
    return records

@app.get("/items/{item_id}", response_model=List[ItemRead])
def get_items(item_id : int, db : Session = Depends(get_db)) -> List[ItemRead]:
    records = db.query(Items).filter(Items.id == item_id).all()
    return records
    # return dummy_items

@app.post("/item", response_model=ItemRead)
def add_item(item: Item, db: Session = Depends(get_db)) -> ItemRead:
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
def delete_item(item_id: int, db: Session = Depends(get_db)):
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
def add_item(item_id: int, item: ItemPut, db: Session = Depends(get_db)) -> Item:
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
def add_item(item_id: int, item: ItemPatch, db: Session = Depends(get_db)) -> ItemRead:
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