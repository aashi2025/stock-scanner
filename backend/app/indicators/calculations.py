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
