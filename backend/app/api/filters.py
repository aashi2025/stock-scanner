from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List
import json
from backend.app.database import get_db
from backend.app.models import CustomFilter
from backend.app.schemas import CustomFilterSchema

router = APIRouter(prefix="/api/filters", tags=["Filter Builder"])

@router.get("/", response_model=List[CustomFilterSchema])
def list_saved_filters(db: Session = Depends(get_db)):
    filters = db.query(CustomFilter).all()
    return [
        CustomFilterSchema(
            id=f.id,
            name=f.name,
            description=f.description,
            rules_json=f.rules_json,
            created_at=f.created_at
        ) for f in filters
    ]

@router.post("/save", response_model=CustomFilterSchema)
def save_custom_filter(
    name: str = Body(...),
    description: str = Body(None),
    rules_json: str = Body(...), # JSON string of rule condition tree
    db: Session = Depends(get_db)
):
    existing = db.query(CustomFilter).filter(CustomFilter.name == name).first()
    if existing:
        existing.description = description
        existing.rules_json = rules_json
        db.commit()
        db.refresh(existing)
        return CustomFilterSchema(id=existing.id, name=existing.name, description=existing.description, rules_json=existing.rules_json, created_at=existing.created_at)

    new_filter = CustomFilter(name=name, description=description, rules_json=rules_json)
    db.add(new_filter)
    db.commit()
    db.refresh(new_filter)
    return CustomFilterSchema(id=new_filter.id, name=new_filter.name, description=new_filter.description, rules_json=new_filter.rules_json, created_at=new_filter.created_at)

@router.delete("/delete/{filter_id}")
def delete_custom_filter(filter_id: int, db: Session = Depends(get_db)):
    f = db.query(CustomFilter).filter(CustomFilter.id == filter_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="Filter not found.")
    db.delete(f)
    db.commit()
    return {"message": "Custom filter deleted successfully"}
