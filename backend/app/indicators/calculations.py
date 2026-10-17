import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple

def calculate_sma(series: pd.Series, period: int) -> pd.Series:
    """Calculates Simple Moving Average over a period."""
    return series.rolling(window=period).mean()

def calculate_ema(series: pd.Series, period: int) -> pd.Series:
    """Calculates Exponential Moving Average (EMA) over a period."""
    return series.ewm(span=period, adjust=False).mean()

def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Calculates Relative Strength Index (RSI)."""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)

def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculates Average True Range (ATR)."""
    high = df['High']
    low = df['Low']
    close = df['Close'].shift(1)
    
    tr1 = high - low
    tr2 = (high - close).abs()
    tr3 = (low - close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    atr = tr.rolling(window=period).mean()
    return atr.bfill().fillna(0.0)

def calculate_relative_strength(stock_df: pd.DataFrame, nifty_df: pd.DataFrame, period: int = 20) -> float:
    """
    Calculates Relative Strength of Stock vs NIFTY 50 over a lookback period.
    Returns percentage outperformance of stock vs NIFTY index over period.
    """
    if stock_df.empty or nifty_df.empty or len(stock_df) < period or len(nifty_df) < period:
        return 0.0
    
    stock_return = float((stock_df['Close'].iloc[-1] - stock_df['Close'].iloc[-period]) / stock_df['Close'].iloc[-period] * 100)
    nifty_return = float((nifty_df['Close'].iloc[-1] - nifty_df['Close'].iloc[-period]) / nifty_df['Close'].iloc[-period] * 100)
    
    outperformance = stock_return - nifty_return
    return float(round(outperformance, 2))

def calculate_52w_metrics(df: pd.DataFrame) -> Tuple[float, float, float]:
    """
    Calculates 52-Week High, 52-Week Low, and percentage distance from 52-Week High.
    Lookback is 250 trading sessions (standard Indian market trading year).
    Distance % = ((52W_High - Price) / 52W_High) * 100
    """
    if df.empty:
        return 0.0, 0.0, 0.0
    lookback = min(len(df), 250)
    high_col = df['High'] if 'High' in df.columns else df['Close']
    low_col = df['Low'] if 'Low' in df.columns else df['Close']
    
    high_52w = float(high_col.tail(lookback).max())
    low_52w = float(low_col.tail(lookback).min())
    cur_price = float(df['Close'].iloc[-1])
    
    dist_pct = float(round(((high_52w - cur_price) / high_52w * 100), 2)) if high_52w > 0 else 0.0
    return round(high_52w, 2), round(low_52w, 2), max(0.0, dist_pct)

def detect_rsi_fresh_crossover(rsi_series: pd.Series, threshold: float = 50.0) -> Dict[str, Any]:
    """
    Detects if RSI has a FRESH crossover above the threshold on COMPLETED candles.
    Rule:
    - Previous candle RSI <= threshold AND Current candle RSI > threshold => FRESH CROSSOVER (True)
    - If RSI was already > threshold on previous candle => Not a fresh crossover (Continuation)
    - Stale crossovers are NEVER reported as new signals.
    """
    if len(rsi_series) < 2:
        return {"fresh_crossover": False, "is_above_50": False, "bars_above_50": 0, "status": "Insufficient Data"}
    
    curr_rsi = float(rsi_series.iloc[-1])
    prev_rsi = float(rsi_series.iloc[-2])
    
    # Count consecutive bars above threshold
    bars_above = 0
    for val in reversed(rsi_series.tolist()):
        if val > threshold:
            bars_above += 1
        else:
            break
            
    is_fresh = bool(prev_rsi <= threshold and curr_rsi > threshold)
    
    if is_fresh:
        status = "Fresh Crossover Above 50"
    elif curr_rsi > threshold:
        status = f"Bullish Continuation ({bars_above} sessions above 50)"
    else:
        status = "Below 50 (Bearish Momentum)"
        
    return {
        "fresh_crossover": is_fresh,
        "is_above_50": bool(curr_rsi > threshold),
        "bars_above_50": bars_above,
        "curr_rsi": round(curr_rsi, 2),
        "prev_rsi": round(prev_rsi, 2),
        "status": status
    }

def compute_all_indicators(df: pd.DataFrame, nifty_df: pd.DataFrame = None) -> Dict[str, Any]:
    """
    Computes technical indicators for a given stock price DataFrame.
    Evaluates strictly on completed candles.
    All primitives are strictly native Python float/bool/int for JSON safety.
    """
    if df.empty or len(df) < 10:
        return {
            "price": 0.0, "sma_50": 0.0, "sma_200": 0.0, "ema_50": 0.0, "ema_200": 0.0,
            "rsi_14": 50.0, "rsi_fresh_crossover": False, "rsi_status": "Insufficient Data",
            "volume": 0, "avg_volume_20d": 0, "vol_ratio": 1.0, "is_volume_breakout": False,
            "rs_vs_nifty_20d": 0.0, "atr_14": 0.0, "high_52w": 0.0, "low_52w": 0.0,
            "dist_from_52w_high_pct": 0.0, "sma_50_above_200": False, "ema_50_above_200": False,
            "price_above_50_ema": False, "price_above_200_ema": False
        }

    close = df['Close']
    price = float(close.iloc[-1])
    
    # SMAs and EMAs
    sma_50_series = calculate_sma(close, 50)
    sma_200_series = calculate_sma(close, 200)
    ema_50_series = calculate_ema(close, 50)
    ema_200_series = calculate_ema(close, 200)
    
    rsi_series = calculate_rsi(close, 14)
    atr_series = calculate_atr(df, 14)
    
    # 52-Week High metrics
    high_52w, low_52w, dist_52w_pct = calculate_52w_metrics(df)
    
    # Fresh RSI Crossover check
    rsi_info = detect_rsi_fresh_crossover(rsi_series, 50.0)

    sma_50 = float(sma_50_series.iloc[-1]) if not pd.isna(sma_50_series.iloc[-1]) else price
    sma_200 = float(sma_200_series.iloc[-1]) if not pd.isna(sma_200_series.iloc[-1]) else price
    ema_50 = float(ema_50_series.iloc[-1]) if not pd.isna(ema_50_series.iloc[-1]) else price
    ema_200 = float(ema_200_series.iloc[-1]) if not pd.isna(ema_200_series.iloc[-1]) else price
    
    rsi_14 = float(rsi_series.iloc[-1]) if not pd.isna(rsi_series.iloc[-1]) else 50.0
    atr_14 = float(atr_series.iloc[-1]) if not pd.isna(atr_series.iloc[-1]) else (price * 0.02)

    vol = int(df['Volume'].iloc[-1]) if 'Volume' in df.columns else 0
    # Average of previous 20 sessions
    avg_vol_20 = int(df['Volume'].tail(20).mean()) if 'Volume' in df.columns and len(df) >= 20 else vol
    vol_ratio = float(round((vol / avg_vol_20), 2)) if avg_vol_20 > 0 else 1.0
    is_vol_breakout = bool(vol_ratio >= 1.2)

    rs_20 = calculate_relative_strength(df, nifty_df, 20) if nifty_df is not None else 0.0

    return {
        "price": float(round(price, 2)),
        "sma_50": float(round(sma_50, 2)),
        "sma_200": float(round(sma_200, 2)),
        "ema_50": float(round(ema_50, 2)),
        "ema_200": float(round(ema_200, 2)),
        "rsi_14": float(round(rsi_14, 2)),
        "rsi_fresh_crossover": bool(rsi_info["fresh_crossover"]),
        "rsi_bars_above_50": int(rsi_info["bars_above_50"]),
        "rsi_status": str(rsi_info["status"]),
        "volume": vol,
        "avg_volume_20d": avg_vol_20,
        "vol_ratio": vol_ratio,
        "is_volume_breakout": is_vol_breakout,
        "rs_vs_nifty_20d": rs_20,
        "atr_14": float(round(atr_14, 2)),
        "high_52w": high_52w,
        "low_52w": low_52w,
        "dist_from_52w_high_pct": dist_52w_pct,
        "sma_50_above_200": bool(sma_50 > sma_200),
        "ema_50_above_200": bool(ema_50 > ema_200),
        "price_above_50_ema": bool(price > ema_50),
        "price_above_200_ema": bool(price > ema_200),
        "price_above_50": bool(price > sma_50),
        "price_above_200": bool(price > sma_200)
    }


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


def compute_momentum_pro_indicators(df: pd.DataFrame, nifty_df: pd.DataFrame = None) -> Dict[str, Any]:
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
    
    rs_50 = calculate_relative_strength(df, nifty_df, 50) if nifty_df is not None and len(df) >= 50 else base["rs_vs_nifty_20d"]
    
    rvol = base["vol_ratio"]
    is_price_breakout = bool(price >= resistance and rvol >= 1.15)
    is_pre_breakout = bool(0.0 <= dist_pct <= 3.0 and not is_price_breakout and base["rsi_14"] >= 48.0)
    is_rsi_crossover = bool(base["rsi_fresh_crossover"])
    
    setup_type = "Neutral"
    if is_price_breakout and is_rsi_crossover:
        setup_type = "Confirmed Breakout + Fresh RSI Cross"
    elif is_price_breakout:
        setup_type = "Confirmed Price Breakout"
    elif is_rsi_crossover:
        setup_type = "Fresh RSI Crossover"
    elif is_pre_breakout:
        setup_type = "Pre-Breakout Consolidation (WATCHLIST)"
    elif base["rsi_14"] > 50 and price > ema_20:
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
