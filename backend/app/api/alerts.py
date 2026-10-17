from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from datetime import datetime
from backend.app.database import get_db
from backend.app.models import AlertRule

router = APIRouter(prefix="/api/alerts", tags=["Alert System"])

@router.get("/")
def get_alerts(db: Session = Depends(get_db)):
    rules = db.query(AlertRule).all()
    return rules

@router.post("/create")
def create_alert_rule(
    symbol: str = Body(...),
    trigger_type: str = Body(...), # score_above, setup_confirmed, sector_bullish, setup_invalidated
    threshold: float = Body(65.0),
    db: Session = Depends(get_db)
):
    rule = AlertRule(
        symbol=symbol.upper(),
        trigger_type=trigger_type,
        threshold=threshold
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return {"message": f"Alert created for {symbol}", "rule": rule}

@router.delete("/delete/{rule_id}")
def delete_alert_rule(rule_id: int, db: Session = Depends(get_db)):
    r = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Alert rule not found.")
    db.delete(r)
    db.commit()
    return {"message": "Alert rule deleted"}
