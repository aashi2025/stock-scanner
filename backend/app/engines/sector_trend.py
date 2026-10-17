from typing import List, Dict, Any
import pandas as pd
from backend.app.data_providers.base import MarketDataProvider
from backend.app.indicators.calculations import compute_all_indicators, calculate_relative_strength

SECTOR_INDEX_LIST = [
    {"name": "IT", "symbol": "NIFTY IT"},
    {"name": "Auto", "symbol": "NIFTY AUTO"},
    {"name": "Bank", "symbol": "NIFTY BANK"},
    {"name": "Pharma", "symbol": "NIFTY PHARMA"},
    {"name": "FMCG", "symbol": "NIFTY FMCG"},
    {"name": "Metal", "symbol": "NIFTY METAL"},
    {"name": "Energy", "symbol": "NIFTY ENERGY"},
    {"name": "Realty", "symbol": "NIFTY REALTY"},
    {"name": "Infra", "symbol": "NIFTY INFRA"}
]

def analyze_sector_trends(
    provider: MarketDataProvider,
    nifty_df: pd.DataFrame = None
) -> List[Dict[str, Any]]:
    """
    Sector Trend Engine.
    Scans sector indices and scores them (0-100) using transparent rule-based metrics.
    No investment advice - purely objective rule measurements.
    """
    if nifty_df is None or nifty_df.empty:
        nifty_df = provider.get_historical_data("NIFTY 50", period="1y", interval="1d")

    sector_results = []

    for sec in SECTOR_INDEX_LIST:
        sec_name = sec["name"]
        sec_sym = sec["symbol"]

        sec_df = provider.get_historical_data(sec_sym, period="1y", interval="1d")
        
        if sec_df.empty:
            # Fallback for sector calculation if specific index missing
            sector_results.append({
                "sector_name": sec_name,
                "index_symbol": sec_sym,
                "price": 0.0,
                "sma_50": 0.0,
                "sma_200": 0.0,
                "rsi": 50.0,
                "rs_vs_nifty": 0.0,
                "sector_score": 50.0,
                "trend": "Neutral",
                "qualifying_stocks_count": 0
            })
            continue

        ind = compute_all_indicators(sec_df, nifty_df)
        price = ind["price"]
        sma_50 = ind["sma_50"]
        sma_200 = ind["sma_200"]
        rsi = ind["rsi_14"]
        rs_20 = ind["rs_vs_nifty_20d"]

        # Calculate Sector Score (0 - 100)
        score = 0.0
        if price > sma_200:
            score += 25.0
        if price > sma_50:
            score += 25.0
        if sma_50 > sma_200:
            score += 20.0
        if rsi > 50.0:
            score += 15.0
        if rs_20 > 0.0:
            score += 15.0

        score = min(100.0, max(0.0, score))

        if score >= 70.0:
            trend = "Bullish"
        elif score >= 45.0:
            trend = "Neutral"
        else:
            trend = "Bearish"

        sector_results.append({
            "sector_name": sec_name,
            "index_symbol": sec_sym,
            "price": price,
            "sma_50": sma_50,
            "sma_200": sma_200,
            "rsi": rsi,
            "rs_vs_nifty": rs_20,
            "sector_score": round(score, 1),
            "trend": trend,
            "qualifying_stocks_count": 0
        })

    return sector_results
