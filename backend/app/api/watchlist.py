from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from backend.app.database import get_db
from backend.app.models import WatchlistItem
from backend.app.schemas import WatchlistItemSchema
from backend.app.data_providers.factory import get_market_data_provider
from backend.app.engines.confirmation import calculate_confirmation_score
from backend.app.engines.invalidation import check_setup_invalidation
from backend.app.engines.market_trend import analyze_market_trend
from backend.app.engines.sector_trend import analyze_sector_trends

router = APIRouter(prefix="/api/watchlist", tags=["Watchlist Management"])

@router.get("/", response_model=List[WatchlistItemSchema])
def get_watchlist(use_sample_mode: bool = False, db: Session = Depends(get_db)):
    items = db.query(WatchlistItem).all()
    if not items:
        return []

    provider = get_market_data_provider(force_sample=use_sample_mode)
    nifty_df = provider.get_historical_data("NIFTY 50", period="1y", interval="1d")
    mkt = analyze_market_trend(provider)
    sec_trends = analyze_sector_trends(provider, nifty_df)
    sec_scores_map = {s["sector_name"].upper(): s["sector_score"] for s in sec_trends}

    result = []
    for item in items:
        df = provider.get_historical_data(item.symbol, period="1y", interval="1d")
        
        if not df.empty:
            conf = calculate_confirmation_score(
                stock={"symbol": item.symbol, "name": item.company_name, "sector": item.sector},
                stock_df=df,
                nifty_df=nifty_df,
                sector_scores_map=sec_scores_map,
                market_score=mkt["market_score"]
            )
            new_score = conf["confirmation_score"]
            inv = check_setup_invalidation(new_score, df, sec_scores_map.get(item.sector.upper(), 60.0))

            item.previous_score = item.current_score if item.current_score > 0 else new_score
            item.current_score = new_score
            item.status = inv["status"]
            db.commit()

        delta = round(item.current_score - item.previous_score, 1)

        result.append(WatchlistItemSchema(
            id=item.id,
            symbol=item.symbol,
            company_name=item.company_name,
            sector=item.sector,
            added_at=item.added_at,
            initial_score=item.initial_score,
            current_score=item.current_score,
            previous_score=item.previous_score,
            score_change=delta,
            status=item.status,
            notes=item.notes
        ))

    return result

@router.post("/add")
def add_to_watchlist(symbol: str, company_name: str, sector: str, initial_score: float = 0.0, db: Session = Depends(get_db)):
    existing = db.query(WatchlistItem).filter(WatchlistItem.symbol == symbol.upper()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Stock already exists in watchlist.")

    item = WatchlistItem(
        symbol=symbol.upper(),
        company_name=company_name,
        sector=sector,
        initial_score=initial_score,
        current_score=initial_score,
        previous_score=initial_score,
        status="HOLDING SETUP STATUS"
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"message": f"Successfully added {symbol} to watchlist", "item": item}

@router.delete("/remove/{symbol}")
def remove_from_watchlist(symbol: str, db: Session = Depends(get_db)):
    item = db.query(WatchlistItem).filter(WatchlistItem.symbol == symbol.upper()).first()
    if not item:
        raise HTTPException(status_code=44, detail="Stock not found in watchlist.")
    db.delete(item)
    db.commit()
    return {"message": f"Removed {symbol} from watchlist"}
