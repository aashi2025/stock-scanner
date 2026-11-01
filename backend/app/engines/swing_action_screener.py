"""
Indian Stocks Swing Trading Action Screener Engine (Nifty 100).
Evaluates daily End-of-Day (EOD) candlesticks against 4 Core Screening Rules:
1. Primary Trend: Close > 200 EMA and Close > Supertrend (7, 3) Bullish.
2. Pullback / Breakout Setup:
   - Setup A (EMA Pullback / Support Test): Consolidating near 200 EMA / Supertrend support with green reversal candle.
   - Setup B (Solid Breakout): Solid body green candle (upper wick <= 25% of candle range) breaking out above 20-day swing resistance.
3. Momentum Filter: Daily RSI(14) between 50.0 and 68.0 (avoids weak < 50 and overbought > 68).
4. Auto Levels Calculation:
   - Entry Price: CMP / Breakout High trigger.
   - Stop Loss (SL): Recent swing low / 0.5% below support EMA (2-5% risk).
   - Target: Minimum 1:2 Risk-to-Reward ratio (+4% to +8% upside potential).
   - Signal: 🟢 READY TO BUY vs ⏳ WAIT FOR CONFIRMATION.
"""

import os
import json
import time
import logging
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, date
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# 100 Liquid Indian Stocks (Nifty 50 + Nifty Next 50) on NSE
NIFTY_100_SYMBOLS = [
    # Top 50 Largecaps
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "BHARTIARTL.NS", "ICICIBANK.NS",
    "INFY.NS", "ITC.NS", "SBIN.NS", "COFORGE.NS", "LT.NS",
    "HINDUNILVR.NS", "M&M.NS", "SUNPHARMA.NS", "NTPC.NS", "ONGC.NS",
    "TITAN.NS", "MARUTI.NS", "POWERGRID.NS", "AXISBANK.NS", "KOTAKBANK.NS",
    "ADANIENT.NS", "ADANIPORTS.NS", "TATASTEEL.NS", "JSWSTEEL.NS", "HCLTECH.NS",
    "WIPRO.NS", "TECHM.NS", "BAJFINANCE.NS", "BAJAJFINSV.NS", "ASIANPAINT.NS",
    "ULTRACEMCO.NS", "NESTLEIND.NS", "COALINDIA.NS", "GRASIM.NS", "CIPLA.NS",
    "DRREDDY.NS", "EICHERMOT.NS", "HEROMOTOCO.NS", "APOLLOHOSP.NS", "DIVISLAB.NS",
    "TATACONSUM.NS", "BPCL.NS", "HDFCLIFE.NS", "SBILIFE.NS", "BEL.NS",
    "TRENT.NS", "HINDALCO.NS", "SHRIRAMFIN.NS", "BAJAJ-AUTO.NS", "INDUSINDBK.NS",
    # Next 50 Liquid Giants
    "ABB.NS", "ACC.NS", "ADANIENSOL.NS", "ADANIGREEN.NS", "ADANIPOWER.NS",
    "ATGL.NS", "AMBUJACEM.NS", "BANKBARODA.NS", "BERGEPAINT.NS", "BHEL.NS",
    "BOSCHLTD.NS", "CANBK.NS", "CHOLAFIN.NS", "COLPAL.NS", "CONCOR.NS",
    "DABUR.NS", "DLF.NS", "GAIL.NS", "GODREJCP.NS", "HAVELLS.NS",
    "HAL.NS", "HINDZINC.NS", "ICICIGI.NS", "ICICIPRULI.NS", "IOC.NS",
    "IRCTC.NS", "IRFC.NS", "JINDALSTEL.NS", "JIOFIN.NS", "MARICO.NS",
    "MOTHERSON.NS", "NAUKRI.NS", "NHPC.NS", "PFC.NS", "PIDILITIND.NS",
    "PNB.NS", "RECLTD.NS", "SBICARD.NS", "SIEMENS.NS", "SRF.NS",
    "TATAPOWER.NS", "TORNTPHARM.NS", "TVSMOTOR.NS", "UNITDSPR.NS", "VBL.NS",
    "VEDL.NS", "DIXON.NS", "ZYDUSLIFE.NS", "POLYCAB.NS", "PERSISTENT.NS"
]

CACHE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "data", "swing_screener_cache.json")


def calculate_supertrend(df: pd.DataFrame, period: int = 7, multiplier: float = 3.0):
    """
    Pure Python/Numpy calculation of Supertrend (7, 3).
    Returns (supertrend_series, direction_series) where direction == 1 is Bullish.
    """
    high = df['High']
    low = df['Low']
    close = df['Close']
    
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean().bfill()
    
    hl2 = (high + low) / 2.0
    upper_basic = hl2 + (multiplier * atr)
    lower_basic = hl2 - (multiplier * atr)
    
    upper_final = upper_basic.copy()
    lower_final = lower_basic.copy()
    supertrend = pd.Series(index=df.index, dtype=float)
    direction = pd.Series(index=df.index, dtype=int)
    
    for i in range(1, len(df)):
        # Lower band: rises as price increases, stays locked
        if lower_basic.iloc[i] > lower_final.iloc[i-1] or close.iloc[i-1] < lower_final.iloc[i-1]:
            lower_final.iloc[i] = lower_basic.iloc[i]
        else:
            lower_final.iloc[i] = lower_final.iloc[i-1]
            
        # Upper band: falls as price drops, stays locked
        if upper_basic.iloc[i] < upper_final.iloc[i-1] or close.iloc[i-1] > upper_final.iloc[i-1]:
            upper_final.iloc[i] = upper_basic.iloc[i]
        else:
            upper_final.iloc[i] = upper_final.iloc[i-1]
            
        prev_dir = direction.iloc[i-1] if not pd.isna(direction.iloc[i-1]) else 1
        if prev_dir == 1:
            if close.iloc[i] < lower_final.iloc[i]:
                direction.iloc[i] = -1
                supertrend.iloc[i] = upper_final.iloc[i]
            else:
                direction.iloc[i] = 1
                supertrend.iloc[i] = lower_final.iloc[i]
        else:
            if close.iloc[i] > upper_final.iloc[i]:
                direction.iloc[i] = 1
                supertrend.iloc[i] = lower_final.iloc[i]
            else:
                direction.iloc[i] = -1
                supertrend.iloc[i] = upper_final.iloc[i]
                
    return supertrend, direction


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Calculates standard 14-period RSI."""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.bfill().fillna(50.0)


def analyze_stock_swing_action(symbol: str, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """
    Applies the 4 Core Screening Rules on 1-year daily OHLCV data.
    """
    if df.empty or len(df) < 50:
        return None
        
    close = df['Close']
    high = df['High']
    low = df['Low']
    open_p = df['Open']
    
    cmp = float(close.iloc[-1])
    if cmp <= 0 or pd.isna(cmp):
        return None
        
    # Moving Averages
    ema_200 = close.ewm(span=200, adjust=False).mean()
    ema_200_val = float(ema_200.iloc[-1])
    
    # Supertrend (7, 3)
    st_series, st_dir = calculate_supertrend(df, period=7, multiplier=3.0)
    st_val = float(st_series.iloc[-1])
    st_bullish = bool(st_dir.iloc[-1] == 1 and cmp > st_val)
    
    # RSI (14)
    rsi_series = calculate_rsi(close, 14)
    rsi_val = float(rsi_series.iloc[-1])
    
    # Filter 1: Primary Trend Check
    # Close > 200 EMA AND Supertrend (7, 3) Bullish
    is_trend_bullish = bool(cmp > ema_200_val and st_bullish)
    if not is_trend_bullish:
        return None
        
    # Filter 3: Momentum Filter
    # Daily RSI between 50.0 and 68.0
    is_rsi_valid = bool(50.0 <= rsi_val <= 68.0)
    if not is_rsi_valid:
        return None

    # Filter 2: Pullback / Breakout Setup
    support = max(ema_200_val, st_val)
    
    # Setup A (EMA Pullback / Support Test):
    # Stock within 3.5% of 200 EMA or Supertrend support in last 1-3 bars,
    # and formed green reversal candle (Close > Open and Close in upper 50% of day's range)
    near_support = any(
        (low.iloc[-i] <= support * 1.035 and close.iloc[-i] >= support * 0.985)
        for i in range(1, min(4, len(df)))
    )
    is_green_reversal = (close.iloc[-1] > open_p.iloc[-1]) and (close.iloc[-1] >= (high.iloc[-1] + low.iloc[-1]) / 2.0)
    setup_a = near_support and is_green_reversal
    
    # Setup B (Solid Breakout):
    # Recent 1-3 days solid body green candle broke 20-day swing resistance without large upper rejection wick
    lookback_res = float(high.iloc[-22:-2].max()) if len(df) >= 25 else float(high.iloc[:-1].max())
    recent_breakout = False
    solid_candle = False
    breakout_price = lookback_res
    
    for i in range(1, min(4, len(df))):
        c_i = close.iloc[-i]
        o_i = open_p.iloc[-i]
        h_i = high.iloc[-i]
        l_i = low.iloc[-i]
        rng_i = h_i - l_i
        upper_wick = h_i - max(c_i, o_i)
        if c_i > lookback_res and c_i > o_i:
            # Rejection wick <= 28% of total candle range
            if rng_i > 0 and (upper_wick / rng_i) <= 0.28:
                recent_breakout = True
                solid_candle = True
                breakout_price = float(h_i)
                break
                
    setup_b = recent_breakout and solid_candle
    
    if not (setup_a or setup_b):
        return None
        
    setup_type = "Setup B: Solid Breakout" if setup_b else "Setup A: EMA Pullback / Support Test"
    
    # Filter 4: Auto Levels Calculation
    entry = round(cmp, 2)
    recent_swing_low = float(low.tail(5).min())
    # Stop loss placed at recent swing low or 0.5% below support line
    sl_raw = min(recent_swing_low, support * 0.995)
    
    # Enforce prudent swing trading risk bounds (2% to 5%)
    risk = entry - sl_raw
    if risk < entry * 0.015:
        sl = round(entry * 0.97, 2) # minimum 3.0% buffer
    elif risk > entry * 0.055:
        sl = round(entry * 0.95, 2) # max 5.0% risk cap
    else:
        sl = round(sl_raw, 2)
        
    risk_final = max(entry - sl, entry * 0.015)
    # Target: Minimum 1:2 Risk-to-Reward ratio (+4% to +8% upside potential)
    target = round(entry + (2.0 * risk_final), 2)
    target_pct = round(((target - entry) / entry) * 100, 2)
    sl_pct = round(((entry - sl) / entry) * 100, 2)
    rr_ratio_val = round((target - entry) / risk_final, 1)
    rr_str = f"1:{rr_ratio_val}"
    
    # Signal Labeling
    if setup_b or (setup_a and is_green_reversal):
        signal = "🟢 READY TO BUY"
        status_note = "Confirmed pattern alignment. Entry triggered at market/breakout."
    else:
        signal = "⏳ WAIT FOR CONFIRMATION"
        status_note = "Testing support. Wait for green breakout candle close above trigger."
        
    clean_sym = symbol.replace(".NS", "").replace(".BO", "")
    
    return {
        "symbol": clean_sym,
        "cmp": entry,
        "signal": signal,
        "setup_type": setup_type,
        "entry_level": entry,
        "stop_loss": sl,
        "sl_pct": sl_pct,
        "target_level": target,
        "target_pct": target_pct,
        "risk_reward_ratio": rr_str,
        "rr_numeric": rr_ratio_val,
        "rsi_14": round(rsi_val, 1),
        "ema_200": round(ema_200_val, 2),
        "supertrend": round(st_val, 2),
        "candle_date": df.index[-1].strftime("%Y-%m-%d") if hasattr(df.index[-1], "strftime") else str(df.index[-1])[:10],
        "status_note": status_note
    }


def scan_nifty_100_market(force_refresh: bool = False) -> List[Dict[str, Any]]:
    """
    Scans the Nifty 100 stock universe using yfinance.
    Utilizes local cache for instant reload if already scanned today.
    """
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    today_str = date.today().isoformat()
    
    # Check cache if not forcing refresh
    if not force_refresh and os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cached = json.load(f)
                if cached.get("scan_date") == today_str and cached.get("results"):
                    logger.info("Serving Nifty 100 scan from today's cache.")
                    return cached["results"]
        except Exception as e:
            logger.warning(f"Error reading cache: {e}")
            
    logger.info(f"Starting fresh scan of {len(NIFTY_100_SYMBOLS)} Nifty 100 stocks...")
    
    # Download in two batches of 50 for optimal reliability and speed
    batch1 = NIFTY_100_SYMBOLS[:50]
    batch2 = NIFTY_100_SYMBOLS[50:]
    
    results = []
    
    for batch in [batch1, batch2]:
        try:
            data = yf.download(batch, period="1y", interval="1d", group_by="ticker", progress=False, threads=True)
            for sym in batch:
                try:
                    df = data[sym].dropna(subset=['Close']) if len(batch) > 1 else data.dropna(subset=['Close'])
                    res = analyze_stock_swing_action(sym, df)
                    if res:
                        results.append(res)
                except Exception as sym_err:
                    logger.debug(f"Error analyzing {sym}: {sym_err}")
        except Exception as batch_err:
            logger.error(f"Error downloading batch: {batch_err}")
            
    # Sort by Risk-Reward and RSI by default
    results.sort(key=lambda x: (x["signal"] == "🟢 READY TO BUY", x["rr_numeric"], -x["rsi_14"]), reverse=True)
    
    # Save to cache
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "scan_date": today_str,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_scanned": len(NIFTY_100_SYMBOLS),
                "total_matches": len(results),
                "results": results
            }, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving scan cache: {e}")
        
    return results
