from sqlalchemy.orm import Session
from typing import List, Optional

from . import models, schemas

def get_item(db: Session, item_id: int):
    return db.query(models.Item).filter(models.Item.id == item_id).first()

def get_items(
    db: Session, 
    skip: int = 0, 
    limit: int = 100,
    title_search: Optional[str] = None
):
    query = db.query(models.Item)
    
    if title_search:
        query = query.filter(models.Item.title.ilike(f"%{title_search}%"))
    
    total = query.count()
    items = query.offset(skip).limit(limit).all()
    
    return items, total

def create_item(db: Session, item: schemas.ItemCreate):
    db_item = models.Item(**item.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

def update_item(db: Session, item_id: int, item: schemas.ItemUpdate):
    db_item = get_item(db, item_id)
    if db_item:
        update_data = item.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_item, key, value)
        db.commit()
        db.refresh(db_item)
    return db_item

def delete_item(db: Session, item_id: int):
    db_item = get_item(db, item_id)
    if db_item:
        db.delete(db_item)
        db.commit()
    return db_item