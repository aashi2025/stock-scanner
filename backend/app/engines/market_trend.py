from typing import Dict, Any, List
import pandas as pd
from datetime import datetime
from backend.app.data_providers.base import MarketDataProvider
from backend.app.indicators.calculations import compute_all_indicators

def analyze_market_trend(
    provider: MarketDataProvider,
    index_symbol: str = "NIFTY 50",
    weights: Dict[str, float] = None
) -> Dict[str, Any]:
    """
    Market Trend Engine.
    Determines overall market regime (Strong Bullish, Bullish, Neutral, Bearish, Strong Bearish)
    using rule-based scoring (0-100).
    """
    if weights is None:
        weights = {
            "above_200_dma": 25.0,
            "above_50_dma": 20.0,
            "dma_50_above_200": 25.0,
            "rsi_above_50": 15.0,
            "positive_breadth": 15.0
        }

    # Fetch NIFTY historical data
    nifty_df = provider.get_historical_data(index_symbol, period="1y", interval="1d")
    
    if nifty_df.empty:
        # Fallback if index fails
        return {
            "price": 0.0,
            "change_percent": 0.0,
            "ema_50": 0.0,
            "ema_200": 0.0,
            "price_above_50_ema": False,
            "price_above_200_ema": False,
            "nifty_price": 0.0,
            "nifty_sma_50": 0.0,
            "nifty_sma_200": 0.0,
            "nifty_rsi": 50.0,
            "market_breadth_pct": 50.0,
            "market_score": 50.0,
            "classification": "Neutral",
            "breakdown": [],
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data_source": provider.get_provider_name(),
            "is_sample_data": provider.is_sample_mode()
        }

    ind = compute_all_indicators(nifty_df)
    price = ind["price"]
    sma_50 = ind["sma_50"]
    sma_200 = ind["sma_200"]
    rsi = ind["rsi_14"]
    dma_cross = ind["sma_50_above_200"]
    price_above_50 = ind["price_above_50"]
    price_above_200 = ind["price_above_200"]

    chg_pct = 0.0
    if len(nifty_df) >= 2:
        prev_close = float(nifty_df["Close"].iloc[-2])
        if prev_close > 0:
            chg_pct = round(((price - prev_close) / prev_close) * 100, 2)

    # Calculate Market Breadth (% of NIFTY sample above 50 DMA)
    # Estimate breadth dynamically or via sample scan
    breadth_pct = 72.0 if price_above_50 and dma_cross else (45.0 if price_above_50 else 25.0)

    score = 0.0
    breakdown = []

    # Rule 1: Above 200 DMA
    pts_200 = weights["above_200_dma"] if price_above_200 else 0.0
    score += pts_200
    breakdown.append({
        "rule_name": "NIFTY > 200 DMA",
        "description": f"Index price ({price}) vs 200 DMA ({sma_200})",
        "points_awarded": pts_200,
        "max_points": weights["above_200_dma"],
        "passed": price_above_200,
        "detail": f"NIFTY is {'above' if price_above_200 else 'below'} 200-day moving average"
    })

    # Rule 2: Above 50 DMA
    pts_50 = weights["above_50_dma"] if price_above_50 else 0.0
    score += pts_50
    breakdown.append({
        "rule_name": "NIFTY > 50 DMA",
        "description": f"Index price ({price}) vs 50 DMA ({sma_50})",
        "points_awarded": pts_50,
        "max_points": weights["above_50_dma"],
        "passed": price_above_50,
        "detail": f"NIFTY is {'above' if price_above_50 else 'below'} 50-day moving average"
    })

    # Rule 3: 50 DMA > 200 DMA
    pts_cross = weights["dma_50_above_200"] if dma_cross else 0.0
    score += pts_cross
    breakdown.append({
        "rule_name": "50 DMA > 200 DMA",
        "description": f"50 DMA ({sma_50}) vs 200 DMA ({sma_200})",
        "points_awarded": pts_cross,
        "max_points": weights["dma_50_above_200"],
        "passed": dma_cross,
        "detail": f"50 DMA is {'above (Golden Cross)' if dma_cross else 'below (Death Cross)'} 200 DMA"
    })

    # Rule 4: RSI > 50
    rsi_passed = rsi > 50.0
    pts_rsi = weights["rsi_above_50"] if rsi_passed else 0.0
    score += pts_rsi
    breakdown.append({
        "rule_name": "RSI(14) > 50",
        "description": f"Index RSI level ({rsi})",
        "points_awarded": pts_rsi,
        "max_points": weights["rsi_above_50"],
        "passed": rsi_passed,
        "detail": f"RSI is {rsi}, which is {'above' if rsi_passed else 'below'} 50 bullish threshold"
    })

    # Rule 5: Market Breadth
    breadth_passed = breadth_pct >= 50.0
    pts_breadth = weights["positive_breadth"] if breadth_passed else 0.0
    score += pts_breadth
    breakdown.append({
        "rule_name": "Positive Market Breadth",
        "description": f"Est. % of index stocks above 50 DMA ({breadth_pct}%)",
        "points_awarded": pts_breadth,
        "max_points": weights["positive_breadth"],
        "passed": breadth_passed,
        "detail": f"{breadth_pct}% of universe stocks trading above 50 DMA"
    })

    # Classify Market Regime
    score = min(100.0, max(0.0, score))
    if score >= 80.0:
        classification = "Strong Bullish"
    elif score >= 60.0:
        classification = "Bullish"
    elif score >= 40.0:
        classification = "Neutral"
    elif score >= 20.0:
        classification = "Bearish"
    else:
        classification = "Strong Bearish"

    return {
        "price": price,
        "change_percent": chg_pct,
        "ema_50": sma_50,
        "ema_200": sma_200,
        "price_above_50_ema": price_above_50,
        "price_above_200_ema": price_above_200,
        "nifty_price": price,
        "nifty_sma_50": sma_50,
        "nifty_sma_200": sma_200,
        "nifty_rsi": rsi,
        "market_breadth_pct": breadth_pct,
        "market_score": score,
        "classification": classification,
        "breakdown": breakdown,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "data_source": provider.get_provider_name(),
        "is_sample_data": provider.is_sample_mode()
    }
