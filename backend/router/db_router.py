from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel

import os
from dotenv import load_dotenv
load_dotenv()

router = APIRouter(prefix="/db", tags=["database"])

# DB 설정
DB_USER = os.getenv("DB_USER")
DB_PW = os.getenv("DB_PW")
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
CHARSET=os.getenv("CHARSET")

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PW}@localhost/{DB_NAME}"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Session:
    """Provide a request-scoped database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 모델 정의
class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String)

class ItemSchema(BaseModel):
    name: str
    description: str

    class Config:
        from_attributes = True

# 라우트
@router.get("/")
def read_root():
    return {"message" : "Welcome to the db!"}

@router.get("/items")
def get_items(db: Session = Depends(get_db)):
    return db.query(Item).all()


@router.post("/items")
def create_item(item: ItemSchema, db: Session = Depends(get_db)):
    db_item = Item(name=item.name, description=item.description)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.get("/items/{item_id}")
def get_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.delete("/items/{item_id}")
def delete_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(item)
    db.commit()
    return {"message": "Item deleted"}
