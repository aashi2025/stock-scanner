from fastapi import APIRouter, Depends, Query, UploadFile, File, HTTPException
from typing import List, Dict, Any, Optional
from backend.app.data_providers.factory import get_market_data_provider
from backend.app.universe.universes import get_universe_stocks, get_available_universes
from backend.app.universe.csv_importer import parse_custom_csv_universe
from backend.app.indicators.calculations import compute_all_indicators
from backend.app.engines.confirmation import calculate_confirmation_score
from backend.app.engines.market_trend import analyze_market_trend
from backend.app.engines.sector_trend import analyze_sector_trends

router = APIRouter(prefix="/api/stocks", tags=["Stock Details & Data"])

@router.get("/universes", response_model=List[str])
def list_available_universes():
    return get_available_universes()

@router.get("/universe/{universe_name}")
def get_universe_stock_list(universe_name: str):
    return get_universe_stocks(universe_name)

@router.post("/upload_csv")
async def upload_custom_universe_csv(file: UploadFile = File(...)):
    content = await file.read()
    try:
        csv_text = content.decode("utf-8")
        stocks = parse_custom_csv_universe(csv_text)
        return {
            "message": f"Successfully parsed {len(stocks)} stocks from CSV",
            "stock_count": len(stocks),
            "stocks": stocks
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV file: {str(e)}")

@router.get("/quote/{symbol}")
def get_stock_quote(
    symbol: str,
    use_sample_mode: bool = Query(False)
):
    provider = get_market_data_provider(force_sample=use_sample_mode)
    quote = provider.get_quote(symbol)
    return quote

@router.get("/detail/{symbol}")
def get_stock_detail(
    symbol: str,
    use_sample_mode: bool = Query(False)
):
    """
    Requirement #8: Stock Detail Page.
    Fetches full quote, technical metrics, confirmation score, passed/failed breakdown,
    plain-English rule explanation, and reference levels.
    """
    provider = get_market_data_provider(force_sample=use_sample_mode)
    
    # Historical data
    df = provider.get_historical_data(symbol, period="1y", interval="1d")
    nifty_df = provider.get_historical_data("NIFTY 50", period="1y", interval="1d")
    
    if df.empty:
        raise HTTPException(status_code=404, detail=f"Stock data for '{symbol}' not found.")

    quote = provider.get_quote(symbol)
    indicators = compute_all_indicators(df, nifty_df)
    
    # Sector & Market Trend
    mkt = analyze_market_trend(provider)
    sec_trends = analyze_sector_trends(provider, nifty_df)
    sec_scores_map = {s["sector_name"].upper(): s["sector_score"] for s in sec_trends}

    stock_meta = {"symbol": symbol.upper(), "name": quote["company_name"], "sector": quote.get("sector", "General")}
    
    confirmation = calculate_confirmation_score(
        stock=stock_meta,
        stock_df=df,
        nifty_df=nifty_df,
        sector_scores_map=sec_scores_map,
        market_score=mkt["market_score"]
    )

    # OHLCV Chart series data
    chart_series = []
    for idx, row in df.iterrows():
        date_str = idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)[:10]
        chart_series.append({
            "time": date_str,
            "open": round(float(row["Open"]), 2),
            "high": round(float(row["High"]), 2),
            "low": round(float(row["Low"]), 2),
            "close": round(float(row["Close"]), 2),
            "volume": int(row["Volume"]) if "Volume" in row else 0
        })

    return {
        "quote": quote,
        "indicators": indicators,
        "confirmation": confirmation,
        "chart_series": chart_series,
        "data_freshness": {
            "timestamp": quote["timestamp"],
            "data_source": quote["data_source"],
            "is_sample_data": quote["is_sample_data"]
        }
    }
