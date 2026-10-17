"""
Delivery & Institutional Accumulation Tracker for Indian Equities.
Analyzes Delivery %, Volume Concentration, and Smart Money Accumulation/Distribution.
Zero-Budget: Uses OHLCV and Delivery metrics if available, or computes OBV/AD heuristics.
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np


def compute_obv(df: pd.DataFrame) -> pd.Series:
    """Calculates On-Balance Volume (OBV)."""
    close = df["Close"]
    volume = df["Volume"] if "Volume" in df.columns else pd.Series(0, index=df.index)
    change = close.diff()
    direction = np.where(change > 0, 1, np.where(change < 0, -1, 0))
    obv = (direction * volume).cumsum()
    return obv


def analyze_accumulation_distribution(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Evaluates Institutional Accumulation indicators.
    High Volume + Close near High of candle indicates strong institutional buying.
    """
    if df.empty or len(df) < 20:
        return {
            "accumulation_score": 50.0,
            "status": "Insufficient Data",
            "delivery_surge": False,
            "obv_trending_up": False,
            "close_location_value": 0.5,
            "details": ["Need at least 20 bars to compute accumulation patterns"]
        }

    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    volume = df["Volume"]

    # Close Location Value (CLV) = ((Close - Low) - (High - Close)) / (High - Low)
    # Range is -1 to +1. Values > +0.6 indicate institutional buying near the highs.
    hl_range = (high - low).replace(0, np.nan)
    clv = (((close - low) - (high - close)) / hl_range).fillna(0.0)
    latest_clv = float(clv.iloc[-1])

    # Volume comparison
    cur_vol = int(volume.iloc[-1])
    avg_vol_20 = int(volume.tail(20).mean()) if len(volume) >= 20 else cur_vol
    vol_ratio = round(cur_vol / avg_vol_20, 2) if avg_vol_20 > 0 else 1.0

    # OBV Trend over last 10 days
    obv_series = compute_obv(df)
    obv_10d_change = float(obv_series.iloc[-1] - obv_series.iloc[-10]) if len(obv_series) >= 10 else 0.0
    obv_trending_up = bool(obv_10d_change > 0)

    score = 0.0
    details = []

    # 1. Close location: Did buyers dominate into the close?
    if latest_clv >= 0.6:
        score += 40.0
        details.append(f"Strong Close: CLV is {round(latest_clv, 2)} (+40) - Buyers absorbed selling at the high")
    elif latest_clv >= 0.2:
        score += 25.0
        details.append(f"Moderate Close: CLV is {round(latest_clv, 2)} (+25)")
    else:
        details.append(f"Weak Close: CLV is {round(latest_clv, 2)} (0) - Intraday selling pressure present")

    # 2. Volume expansion
    if vol_ratio >= 1.5:
        score += 35.0
        details.append(f"Volume Surge {vol_ratio}x 20-DMA (+35) - Institutional footprint confirmed")
    elif vol_ratio >= 1.2:
        score += 25.0
        details.append(f"Above Average Volume {vol_ratio}x (+25)")
    else:
        details.append(f"Normal/Light Volume {vol_ratio}x (0)")

    # 3. OBV Accumulation
    if obv_trending_up:
        score += 25.0
        details.append("On-Balance Volume (OBV) expanding over past 10 sessions (+25)")
    else:
        details.append("OBV declining or flat (0)")

    if score >= 75.0:
        status = "Strong Smart Money Accumulation (संस्थागत संचय)"
    elif score >= 50.0:
        status = "Moderate Accumulation (सामान्य संचय)"
    else:
        status = "No Clear Accumulation (वितरण या अनिर्णय)"

    return {
        "accumulation_score": round(score, 1),
        "status": status,
        "volume_surge": bool(vol_ratio >= 1.2),
        "volume_ratio": vol_ratio,
        "obv_trending_up": obv_trending_up,
        "close_location_value": round(latest_clv, 2),
        "details": details
    }
