"""
Intraday Technical Indicator and Structural Calculations for Indian Equities.
Calculates:
- Volume Weighted Average Price (VWAP)
- Central Pivot Range (CPR: Pivot, TC, BC) & Standard Pivots (R1, S1, R2, S2)
- Previous Day High (PDH) and Previous Day Low (PDL)
- Opening Range (First 15-minute / 30-minute high & low)
- Relative Volume (RVOL) vs historical intraday baseline
"""

from typing import Dict, Any, Tuple, Optional
import pandas as pd
import numpy as np


def calculate_vwap(df: pd.DataFrame) -> pd.Series:
    """
    Calculates Volume Weighted Average Price (VWAP) for intraday bars.
    VWAP = Cumulative(Typical Price * Volume) / Cumulative(Volume)
    Typical Price = (High + Low + Close) / 3
    """
    if df.empty or "Volume" not in df.columns:
        return pd.Series(dtype=float)

    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    vol = df["Volume"].replace(0, 1)

    typical_price = (high + low + close) / 3.0
    cum_vol_price = (typical_price * vol).cumsum()
    cum_vol = vol.cumsum()

    vwap = cum_vol_price / cum_vol
    return vwap.bfill().fillna(close)


def calculate_cpr_and_pivots(prev_high: float, prev_low: float, prev_close: float) -> Dict[str, float]:
    """
    Calculates Classical Pivot Points and Central Pivot Range (CPR).
    - Pivot (P) = (High + Low + Close) / 3
    - Bottom Central (BC) = (High + Low) / 2
    - Top Central (TC) = (Pivot - BC) + Pivot = 2 * Pivot - BC
    - R1 = (2 * P) - Low, S1 = (2 * P) - High
    - R2 = P + (High - Low), S2 = P - (High - Low)
    """
    p = (prev_high + prev_low + prev_close) / 3.0
    bc = (prev_high + prev_low) / 2.0
    tc = (2.0 * p) - bc

    cpr_tc = max(tc, bc)
    cpr_bc = min(tc, bc)
    cpr_width_pct = round(((cpr_tc - cpr_bc) / p * 100.0), 3) if p > 0 else 0.0

    r1 = (2.0 * p) - prev_low
    s1 = (2.0 * p) - prev_high
    r2 = p + (prev_high - prev_low)
    s2 = p - (prev_high - prev_low)

    return {
        "pivot": round(p, 2),
        "cpr_tc": round(cpr_tc, 2),
        "cpr_bc": round(cpr_bc, 2),
        "cpr_width_pct": cpr_width_pct,
        "is_narrow_cpr": bool(cpr_width_pct < 0.25), # High trending probability
        "r1": round(r1, 2),
        "s1": round(s1, 2),
        "r2": round(r2, 2),
        "s2": round(s2, 2)
    }


def calculate_opening_range(df: pd.DataFrame, bars_count: int = 3) -> Tuple[float, float]:
    """
    Calculates Opening Range High and Low.
    For 5-min bars: bars_count=3 yields 15-minute Opening Range (9:15 - 9:30 AM).
    """
    if df.empty:
        return 0.0, 0.0

    subset = df.iloc[:bars_count]
    orb_high = float(subset["High"].max())
    orb_low = float(subset["Low"].min())
    return round(orb_high, 2), round(orb_low, 2)


def calculate_previous_day_levels(daily_df: pd.DataFrame) -> Dict[str, float]:
    """
    Extracts Previous Day High (PDH), Previous Day Low (PDL), and Previous Day Close (PDC).
    """
    if daily_df.empty or len(daily_df) < 2:
        return {"pdh": 0.0, "pdl": 0.0, "pdc": 0.0}

    prev_bar = daily_df.iloc[-2]
    return {
        "pdh": round(float(prev_bar["High"]), 2),
        "pdl": round(float(prev_bar["Low"]), 2),
        "pdc": round(float(prev_bar["Close"]), 2)
    }
