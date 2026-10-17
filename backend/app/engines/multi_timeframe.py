"""
Multi-Timeframe (MTF) Confirmation Engine.
Resamples daily completed candles into weekly candles to evaluate:
1. Weekly Trend (Weekly Close > Weekly 20 EMA)
2. Weekly Momentum (Weekly RSI 14 > 50)
3. Higher Timeframe Alignment Score (0 - 100)
Eliminates daily whipsaws against macro market structure.
"""

from typing import Dict, Any, Tuple
import pandas as pd
import numpy as np

from backend.app.indicators.calculations import calculate_ema, calculate_rsi


def resample_daily_to_weekly(daily_df: pd.DataFrame) -> pd.DataFrame:
    """
    Resamples daily OHLCV DataFrame into weekly completed candles (ending Friday).
    Index must be DatetimeIndex.
    """
    if daily_df.empty:
        return pd.DataFrame()

    df = daily_df.copy()
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)

    # Resample weekly ending Friday
    weekly = df.resample("W-FRI").agg({
        "Open": "first",
        "High": "max",
        "Low": "min",
        "Close": "last",
        "Volume": "sum"
    }).dropna()

    return weekly


def analyze_multi_timeframe_context(daily_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Analyzes higher-timeframe weekly context for a stock.
    Returns weekly indicators and alignment classification.
    """
    if daily_df.empty or len(daily_df) < 50:
        return {
            "is_available": False,
            "weekly_trend_bullish": False,
            "weekly_momentum_bullish": False,
            "weekly_score": 50.0,
            "weekly_close": 0.0,
            "weekly_ema_20": 0.0,
            "weekly_rsi": 50.0,
            "mtf_status": "Insufficient Data for Weekly Resampling",
            "reasons": ["Need at least 50 daily candles to form reliable weekly structure"]
        }

    weekly_df = resample_daily_to_weekly(daily_df)
    if len(weekly_df) < 20:
        return {
            "is_available": False,
            "weekly_trend_bullish": False,
            "weekly_momentum_bullish": False,
            "weekly_score": 50.0,
            "weekly_close": float(weekly_df["Close"].iloc[-1]) if not weekly_df.empty else 0.0,
            "weekly_ema_20": 0.0,
            "weekly_rsi": 50.0,
            "mtf_status": "Insufficient Weekly Candles (<20 weeks)",
            "reasons": ["Less than 20 weeks of historical data available"]
        }

    w_close = weekly_df["Close"]
    cur_w_close = float(w_close.iloc[-1])

    # 20 Weekly EMA (approx 100 daily days)
    w_ema_20_series = calculate_ema(w_close, 20)
    cur_w_ema_20 = float(w_ema_20_series.iloc[-1])

    # Weekly RSI(14)
    w_rsi_series = calculate_rsi(w_close, 14)
    cur_w_rsi = float(w_rsi_series.iloc[-1])

    weekly_trend_bullish = bool(cur_w_close > cur_w_ema_20)
    weekly_mom_bullish = bool(cur_w_rsi >= 50.0)

    score = 0.0
    reasons = []

    if weekly_trend_bullish:
        score += 50.0
        reasons.append(f"Weekly Close (₹{round(cur_w_close, 2)}) is ABOVE Weekly 20 EMA (₹{round(cur_w_ema_20, 2)})")
    else:
        reasons.append(f"Weekly Close is BELOW Weekly 20 EMA (Macro downtrend resistance)")

    if cur_w_rsi >= 55.0:
        score += 50.0
        reasons.append(f"Weekly RSI {round(cur_w_rsi, 1)} shows strong macro bullish momentum (> 55)")
    elif cur_w_rsi >= 50.0:
        score += 35.0
        reasons.append(f"Weekly RSI {round(cur_w_rsi, 1)} holds above 50 bullish threshold")
    else:
        reasons.append(f"Weekly RSI {round(cur_w_rsi, 1)} is in macro bearish territory (< 50)")

    if score >= 85.0:
        mtf_status = "High-Conviction MTF Alignment (मैक्रो अपट्रेंड)"
    elif score >= 50.0:
        mtf_status = "Neutral MTF Structure (तटस्थ मैक्रो ट्रेंड)"
    else:
        mtf_status = "Counter-Trend Caution (सावधान: मैक्रो डाउनट्रेंड)"

    return {
        "is_available": True,
        "weekly_trend_bullish": weekly_trend_bullish,
        "weekly_momentum_bullish": weekly_mom_bullish,
        "weekly_score": round(score, 1),
        "weekly_close": round(cur_w_close, 2),
        "weekly_ema_20": round(cur_w_ema_20, 2),
        "weekly_rsi": round(cur_w_rsi, 1),
        "mtf_status": mtf_status,
        "reasons": reasons
    }
