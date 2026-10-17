from fastapi import APIRouter, Depends, Query
from backend.app.data_providers.factory import get_market_data_provider
from backend.app.engines.market_trend import analyze_market_trend
from backend.app.engines.sector_trend import analyze_sector_trends
from backend.app.schemas import MarketTrendResult, SectorTrendItem
from typing import List

router = APIRouter(prefix="/api/market", tags=["Market & Sector Trends"])

@router.get("/trend", response_model=MarketTrendResult)
def get_market_trend(
    use_sample_mode: bool = Query(False, description="Explicitly enable sample data mode for testing")
):
    provider = get_market_data_provider(force_sample=use_sample_mode)
    res = analyze_market_trend(provider)
    return res

@router.get("/sectors", response_model=List[SectorTrendItem])
def get_sector_trends(
    use_sample_mode: bool = Query(False, description="Explicitly enable sample data mode for testing")
):
    provider = get_market_data_provider(force_sample=use_sample_mode)
    res = analyze_sector_trends(provider)
    return res
