from fastapi import APIRouter, Depends, Body, HTTPException
from datetime import datetime
from typing import List, Dict, Any, Optional
from backend.app.data_providers.factory import get_market_data_provider
from backend.app.universe.universes import get_universe_stocks
from backend.app.engines.market_trend import analyze_market_trend
from backend.app.engines.sector_trend import analyze_sector_trends
from backend.app.engines.confirmation import calculate_confirmation_score
from backend.app.engines.swing_scanner import analyze_swing_setup
from backend.app.engines.monthly_research import run_monthly_research_scan
from backend.app.schemas import ScanFilterParams, ScanResult, ConfirmationBreakdown

router = APIRouter(prefix="/api/scan", tags=["Scanner Pipeline"])

@router.post("/run", response_model=ScanResult)
def run_full_scan(params: ScanFilterParams = Body(...)):
    """Runs the 6-stage Confirmation Scanner using Upstox / configured provider."""
    provider = get_market_data_provider(force_sample=params.use_sample_mode)

    # 1. MARKET TREND
    market_trend = analyze_market_trend(provider)

    # 2. SECTOR TREND
    nifty_df = provider.get_historical_data("NIFTY 50", period="1y", interval="day")
    sector_trends = analyze_sector_trends(provider, nifty_df)
    sector_scores_map = {s["sector_name"].upper(): s["sector_score"] for s in sector_trends}

    # 3. STOCK UNIVERSE
    stocks = get_universe_stocks(params.universe)

    confirmed_setups: List[ConfirmationBreakdown] = []
    watchlist_setups: List[ConfirmationBreakdown] = []
    not_confirmed_count = 0

    # 4. TECHNICAL & CONFIRMATION SCORING PIPELINE
    for stock in stocks:
        sym = stock["symbol"]
        stock_df = provider.get_historical_data(sym, period="1y", interval="day")
        
        if stock_df.empty:
            not_confirmed_count += 1
            continue

        res = calculate_confirmation_score(
            stock=stock,
            stock_df=stock_df,
            nifty_df=nifty_df,
            sector_scores_map=sector_scores_map,
            market_score=market_trend["market_score"]
        )

        score = res["confirmation_score"]
        sec_name = stock.get("sector", "General").upper()
        sec_score = sector_scores_map.get(sec_name, 60.0)

        # Apply configurable threshold filters
        if score >= params.min_confirmation_score and sec_score >= params.min_sector_score:
            confirmed_setups.append(ConfirmationBreakdown(**res))
        elif score >= 50.0:
            watchlist_setups.append(ConfirmationBreakdown(**res))
        else:
            not_confirmed_count += 1

    # Update sector qualifying stocks count
    for st in sector_trends:
        sec_u = st["sector_name"].upper()
        count = sum(1 for c in confirmed_setups if c.sector.upper() == sec_u)
        st["qualifying_stocks_count"] = count

    # Sort setups descending by score
    confirmed_setups.sort(key=lambda x: x.confirmation_score, reverse=True)
    watchlist_setups.sort(key=lambda x: x.confirmation_score, reverse=True)

    return ScanResult(
        scan_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        data_source=provider.get_provider_name(),
        is_sample_data=provider.is_sample_mode(),
        total_stocks_scanned=len(stocks),
        market_trend=market_trend,
        sector_trends=sector_trends,
        confirmed_setups=confirmed_setups,
        watchlist_setups=watchlist_setups,
        not_confirmed_count=not_confirmed_count
    )

@router.post("/swing")
def run_swing_scan(
    universe: str = Body("NIFTY 50", embed=True),
    only_fresh_crossover: bool = Body(False, embed=True)
):
    """
    Dedicated Swing Trading Scanner endpoint using Upstox real historical data.
    Evaluates:
    - RSI(14) fresh crossover above 50 on completed candle
    - EMA50 and EMA200 trend alignment
    - Volume breakout vs 20 sessions average volume
    - Proximity to 52-Week High
    - Sector strength
    """
    provider = get_market_data_provider()
    stocks = get_universe_stocks(universe)

    nifty_df = provider.get_historical_data("NIFTY 50", period="1y", interval="day")
    market_trend = analyze_market_trend(provider)
    sector_trends = analyze_sector_trends(provider, nifty_df)
    sector_scores_map = {s["sector_name"].upper(): s["sector_score"] for s in sector_trends}

    results = []
    fresh_crossover_count = 0
    volume_breakout_count = 0

    for s in stocks:
        sym = s["symbol"]
        df = provider.get_historical_data(sym, period="1y", interval="day")
        if df.empty or len(df) < 20:
            continue

        setup = analyze_swing_setup(
            stock=s,
            stock_df=df,
            nifty_df=nifty_df,
            sector_scores_map=sector_scores_map,
            market_score=market_trend["market_score"]
        )

        if setup["rsi_fresh_crossover"]:
            fresh_crossover_count += 1
        if setup["volume_breakout"]:
            volume_breakout_count += 1

        if only_fresh_crossover and not setup["rsi_fresh_crossover"]:
            continue

        results.append(setup)

    # Sort descending by swing score
    results.sort(key=lambda x: x["swing_score"], reverse=True)

    return {
        "scan_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "data_source": provider.get_provider_name(),
        "universe": universe,
        "total_scanned": len(stocks),
        "total_results": len(results),
        "fresh_crossover_count": fresh_crossover_count,
        "volume_breakout_count": volume_breakout_count,
        "market_score": market_trend["market_score"],
        "swing_candidates": results
    }

@router.post("/monthly")
def run_monthly_research_endpoint(universe: str = Body("NIFTY 50", embed=True)):
    """
    Monthly Stock Research Scanner Endpoint.
    Produces Buy Candidates, Hold Candidates, and Exit Reviews based on
    Upstox long-term price action and verified financial fundamentals.
    """
    provider = get_market_data_provider()
    stocks = get_universe_stocks(universe)
    results = run_monthly_research_scan(stocks, provider)
    
    return {
        "scan_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "data_source": provider.get_provider_name(),
        "universe": universe,
        "summary": {
            "total_analyzed": results["total_analyzed"],
            "buy_candidates_count": len(results["buy_candidates"]),
            "hold_candidates_count": len(results["hold_candidates"]),
            "exit_reviews_count": len(results["exit_reviews"])
        },
        "buy_candidates": results["buy_candidates"],
        "hold_candidates": results["hold_candidates"],
        "exit_reviews": results["exit_reviews"]
    }
