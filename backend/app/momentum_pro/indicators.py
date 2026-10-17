"""
Momentum Pro — Specialized Technical Indicators & Price Structure Calculations.
Calculates:
- EMA 9, EMA 20, SMA 50, SMA 200
- RSI 14 and Fresh Crossover detection on completed candles
- 20-Day Swing High Resistance & Swing Low
- Relative Volume (RVOL) vs 20 session average
- ATR 14
- Relative Strength vs NIFTY benchmark (20D & 50D)
- Setup classification (Confirmed Breakout, Pre-Breakout Watchlist, Fresh RSI Crossover)
"""

from typing import Dict, Any, Tuple, Optional
import pandas as pd
import numpy as np

from backend.app.indicators.calculations import (
    calculate_sma,
    calculate_ema,
    calculate_rsi,
    calculate_atr,
    calculate_relative_strength,
    detect_rsi_fresh_crossover,
    compute_all_indicators
)


def calculate_resistance_and_swing_high(df: pd.DataFrame, lookback: int = 20) -> Tuple[float, float, float]:
    """
    Calculates 20-period swing high resistance and distance percentage.
    Looks at high of prior (lookback) completed candles, excluding current candle.
    Distance % = ((resistance - current_price) / resistance) * 100
    """
    if df.empty or len(df) < 5:
        return 0.0, 0.0, 0.0

    high_col = df['High'] if 'High' in df.columns else df['Close']
    low_col = df['Low'] if 'Low' in df.columns else df['Close']

    # Prior completed candles
    prior_highs = high_col.iloc[-(lookback+1):-1] if len(df) > lookback else high_col.iloc[:-1]
    prior_lows = low_col.iloc[-(lookback+1):-1] if len(df) > lookback else low_col.iloc[:-1]

    resistance = float(prior_highs.max()) if not prior_highs.empty else float(high_col.max())
    swing_low = float(prior_lows.min()) if not prior_lows.empty else float(low_col.min())
    curr_price = float(df['Close'].iloc[-1])

    dist_pct = float(round(((resistance - curr_price) / resistance * 100), 2)) if resistance > 0 else 0.0
    return round(resistance, 2), round(swing_low, 2), dist_pct


def compute_momentum_pro_indicators(df: pd.DataFrame, nifty_df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
    """
    Comprehensive indicators for Momentum Pro:
    - EMA 9, EMA 20
    - SMA 50, SMA 200
    - RSI 14 & fresh crossover detection
    - Relative Volume (RVOL) vs 20 session average
    - ATR 14
    - Resistance (20-period swing high) and Swing Low
    - Relative Strength vs NIFTY (20d and 50d)
    - Distance from breakout
    - Setup classification (Confirmed Breakout, Pre-Breakout Watchlist, Fresh RSI Crossover, Neutral)
    """
    base = compute_all_indicators(df, nifty_df)
    if df.empty or len(df) < 10:
        return {
            **base,
            "ema_9": 0.0,
            "ema_20": 0.0,
            "ema_9_above_20": False,
            "resistance_20d": 0.0,
            "swing_low_20d": 0.0,
            "dist_to_resistance_pct": 0.0,
            "rvol": 1.0,
            "rs_vs_nifty_50d": 0.0,
            "is_price_breakout": False,
            "is_pre_breakout": False,
            "is_rsi_crossover": False,
            "momentum_setup_type": "Insufficient Data"
        }

    close = df['Close']
    price = float(close.iloc[-1])

    ema_9_series = calculate_ema(close, 9)
    ema_20_series = calculate_ema(close, 20)

    ema_9 = float(ema_9_series.iloc[-1]) if not pd.isna(ema_9_series.iloc[-1]) else price
    ema_20 = float(ema_20_series.iloc[-1]) if not pd.isna(ema_20_series.iloc[-1]) else price

    resistance, swing_low, dist_pct = calculate_resistance_and_swing_high(df, lookback=20)

    rs_50 = calculate_relative_strength(df, nifty_df, 50) if nifty_df is not None and len(df) >= 50 else base.get("rs_vs_nifty_20d", 0.0)

    rvol = base.get("vol_ratio", 1.0)
    is_price_breakout = bool(price >= resistance and rvol >= 1.15)
    is_pre_breakout = bool(0.0 <= dist_pct <= 3.0 and not is_price_breakout and base.get("rsi_14", 50.0) >= 48.0)
    is_rsi_crossover = bool(base.get("rsi_fresh_crossover", False))

    setup_type = "Neutral"
    if is_price_breakout and is_rsi_crossover:
        setup_type = "Confirmed Breakout + Fresh RSI Cross"
    elif is_price_breakout:
        setup_type = "Confirmed Price Breakout"
    elif is_rsi_crossover:
        setup_type = "Fresh RSI Crossover"
    elif is_pre_breakout:
        setup_type = "Pre-Breakout Consolidation (WATCHLIST)"
    elif base.get("rsi_14", 50.0) > 50 and price > ema_20:
        setup_type = "Momentum Continuation"

    return {
        **base,
        "ema_9": round(ema_9, 2),
        "ema_20": round(ema_20, 2),
        "ema_9_above_20": bool(ema_9 > ema_20),
        "resistance_20d": round(resistance, 2),
        "swing_low_20d": round(swing_low, 2),
        "dist_to_resistance_pct": round(dist_pct, 2),
        "rvol": rvol,
        "rs_vs_nifty_50d": round(rs_50, 2),
        "is_price_breakout": is_price_breakout,
        "is_pre_breakout": is_pre_breakout,
        "is_rsi_crossover": is_rsi_crossover,
        "momentum_setup_type": setup_type
    }
