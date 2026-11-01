"""
Swing Delivery Trade Screener Engine (Nifty 100).
Core screening filters:
- Filter 1: Primary Trend (Close > 200 EMA and Supertrend 7,3 Bullish)
- Filter 2: Setup A (EMA Pullback / Support Test) or Setup B (Solid Breakout)
- Filter 3: Momentum Filter (50.0 <= RSI 14 <= 68.0)
- Filter 4: Auto Levels (Entry, SL, Target with min 1:2 R:R)
"""

import pandas as pd
import numpy as np
import yfinance as yf
from typing import List, Dict, Any, Optional

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


def calculate_supertrend(df: pd.DataFrame, period: int = 7, multiplier: float = 3.0):
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
        if lower_basic.iloc[i] > lower_final.iloc[i-1] or close.iloc[i-1] < lower_final.iloc[i-1]:
            lower_final.iloc[i] = lower_basic.iloc[i]
        else:
            lower_final.iloc[i] = lower_final.iloc[i-1]
            
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
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.bfill().fillna(50.0)


def evaluate_stock_setup(symbol: str, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    if df.empty or len(df) < 50:
        return None
        
    close = df['Close']
    high = df['High']
    low = df['Low']
    open_p = df['Open']
    
    cmp = float(close.iloc[-1])
    if cmp <= 0 or pd.isna(cmp):
        return None
        
    ema_200 = close.ewm(span=200, adjust=False).mean()
    ema_200_val = float(ema_200.iloc[-1])
    
    st_series, st_dir = calculate_supertrend(df, period=7, multiplier=3.0)
    st_val = float(st_series.iloc[-1])
    st_bullish = bool(st_dir.iloc[-1] == 1 and cmp > st_val)
    
    rsi_series = calculate_rsi(close, 14)
    rsi_val = float(rsi_series.iloc[-1])
    
    # Filter 1: Primary Trend Check
    if not (cmp > ema_200_val and st_bullish):
        return None
        
    # Filter 3: Momentum Filter
    if not (50.0 <= rsi_val <= 68.0):
        return None
        
    # Filter 2: Pullback / Breakout Setup
    support = max(ema_200_val, st_val)
    
    near_support = any(
        (low.iloc[-i] <= support * 1.035 and close.iloc[-i] >= support * 0.985)
        for i in range(1, min(4, len(df)))
    )
    is_green_reversal = (close.iloc[-1] > open_p.iloc[-1]) and (close.iloc[-1] >= (high.iloc[-1] + low.iloc[-1]) / 2.0)
    setup_a = near_support and is_green_reversal
    
    lookback_res = float(high.iloc[-22:-2].max()) if len(df) >= 25 else float(high.iloc[:-1].max())
    recent_breakout = False
    solid_candle = False
    
    for i in range(1, min(4, len(df))):
        c_i = close.iloc[-i]
        o_i = open_p.iloc[-i]
        h_i = high.iloc[-i]
        l_i = low.iloc[-i]
        rng_i = h_i - l_i
        upper_wick = h_i - max(c_i, o_i)
        if c_i > lookback_res and c_i > o_i:
            if rng_i > 0 and (upper_wick / rng_i) <= 0.28:
                recent_breakout = True
                solid_candle = True
                break
                
    setup_b = recent_breakout and solid_candle
    
    if not (setup_a or setup_b):
        return None
        
    setup_type = "Setup B: Solid Breakout" if setup_b else "Setup A: EMA Pullback / Support Test"
    
    # Filter 4: Auto Levels
    entry = round(cmp, 2)
    recent_swing_low = float(low.tail(5).min())
    sl_raw = min(recent_swing_low, support * 0.995)
    
    risk = entry - sl_raw
    if risk < entry * 0.015:
        sl = round(entry * 0.97, 2)
    elif risk > entry * 0.055:
        sl = round(entry * 0.95, 2)
    else:
        sl = round(sl_raw, 2)
        
    risk_final = max(entry - sl, entry * 0.015)
    target = round(entry + (2.0 * risk_final), 2)
    target_pct = round(((target - entry) / entry) * 100, 2)
    sl_pct = round(((entry - sl) / entry) * 100, 2)
    rr_num = round((target - entry) / risk_final, 1)
    
    signal = "🟢 READY TO BUY" if (setup_b or (setup_a and is_green_reversal)) else "⏳ WAIT FOR CONFIRMATION"
    
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
        "risk_reward_ratio": f"1:{rr_num}",
        "rr_numeric": rr_num,
        "rsi_14": round(rsi_val, 1),
        "ema_200": round(ema_200_val, 2),
        "supertrend": round(st_val, 2)
    }


def execute_market_scan() -> List[Dict[str, Any]]:
    batch1 = NIFTY_100_SYMBOLS[:50]
    batch2 = NIFTY_100_SYMBOLS[50:]
    results = []
    
    for batch in [batch1, batch2]:
        try:
            data = yf.download(batch, period="1y", interval="1d", group_by="ticker", progress=False, threads=True)
            for sym in batch:
                try:
                    df = data[sym].dropna(subset=['Close']) if len(batch) > 1 else data.dropna(subset=['Close'])
                    res = evaluate_stock_setup(sym, df)
                    if res:
                        results.append(res)
                except Exception:
                    pass
        except Exception:
            pass
            
    results.sort(key=lambda x: (x["signal"] == "🟢 READY TO BUY", x["rr_numeric"], -x["rsi_14"]), reverse=True)
    return results
