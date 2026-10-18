"""
Intraday Cash Equity Scanner Engine for Indian Equities.
Scans for:
1. Opening Range Breakout (ORB) (High / Low breakout)
2. Previous Day High (PDH) Breakout & Previous Day Low (PDL) Breakdown
3. Relative Volume (RVOL) Expansion
4. VWAP Trend Continuation & Pullbacks
5. Relative Strength vs NIFTY intraday
"""

from typing import List, Dict, Any, Optional
import pandas as pd
from datetime import datetime

from backend.app.data_providers.base import MarketDataProvider
from backend.app.intraday.calculations import (
    calculate_vwap,
    calculate_cpr_and_pivots,
    calculate_opening_range,
    calculate_previous_day_levels
)
from backend.app.indicators.calculations import calculate_relative_strength, calculate_atr

DEFAULT_INTRADAY_UNIVERSE = [
    "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK",
    "SBIN", "BHARTIARTL", "ITC", "LT", "MARUTI"
]

def run_intraday_scan(
    provider: MarketDataProvider,
    symbols: Optional[List[str]] = None,
    min_volume_ratio: float = 1.2,
    min_price: float = 50.0,
    max_price: float = 50000.0
) -> Dict[str, Any]:
    """
    Scans universe for active intraday setups on completed bars.
    """
    if not symbols:
        if hasattr(provider, "list_available_symbols"):
            symbols = provider.list_available_symbols()
        if not symbols:
            symbols = DEFAULT_INTRADAY_UNIVERSE

    # Nifty benchmark for relative strength
    nifty_daily = provider.get_historical_data("NIFTY 50", period="1mo", interval="1d")
    if nifty_daily.empty:
        nifty_daily = provider.get_historical_data("NIFTY_50", period="1mo", interval="1d")

    orb_breakouts = []
    pdh_pdl_breakouts = []
    vwap_trends = []
    all_intraday_candidates = []

    for sym in symbols:
        try:
            # 1. Fetch daily data for prior day levels & baseline
            daily_df = provider.get_historical_data(sym, period="1mo", interval="1d")
            if daily_df.empty or len(daily_df) < 5:
                continue

            last_close = float(daily_df["Close"].iloc[-1])
            if last_close < min_price or last_close > max_price:
                continue

            # Prior day levels
            pd_levels = calculate_previous_day_levels(daily_df)
            pdh = pd_levels["pdh"]
            pdl = pd_levels["pdl"]
            pdc = pd_levels["pdc"]

            # CPR and Pivots
            pivots = calculate_cpr_and_pivots(pdh, pdl, pdc)

            # 2. Daily ATR & Relative Strength
            atr_val = float(calculate_atr(daily_df, 14).iloc[-1]) if len(daily_df) >= 14 else (last_close * 0.02)
            rs_val = calculate_relative_strength(daily_df, nifty_daily, 5)

            # Volume ratio vs 20 session average
            vol_curr = int(daily_df["Volume"].iloc[-1]) if "Volume" in daily_df.columns else 0
            vol_avg = int(daily_df["Volume"].tail(20).mean()) if len(daily_df) >= 20 else vol_curr
            rvol = round(vol_curr / vol_avg, 2) if vol_avg > 0 else 1.0

            # 3. Simulated/Derived Intraday levels (ORB & VWAP)
            # Use current day high/low/close as reference for completed setup check
            curr_high = float(daily_df["High"].iloc[-1])
            curr_low = float(daily_df["Low"].iloc[-1])
            curr_open = float(daily_df["Open"].iloc[-1])

            # Opening range estimate: first 30% of daily range around Open
            orb_h = round(curr_open + (curr_high - curr_open) * 0.45, 2)
            orb_l = round(curr_open - (curr_open - curr_low) * 0.45, 2)
            vwap_est = round((curr_high + curr_low + last_close) / 3.0, 2)

            # Check setup triggers
            is_orb_bull = bool(last_close > orb_h and rvol >= min_volume_ratio)
            is_orb_bear = bool(last_close < orb_l and rvol >= min_volume_ratio)
            
            is_pdh_breakout = bool(last_close > pdh and pdh > 0)
            is_pdl_breakdown = bool(last_close < pdl and pdl > 0)

            is_vwap_bull = bool(last_close > vwap_est and curr_open > vwap_est)
            is_vwap_pullback = bool(abs(last_close - vwap_est) / vwap_est < 0.005 and rvol >= 1.0)

            candidate = {
                "symbol": sym,
                "price": last_close,
                "pdh": pdh,
                "pdl": pdl,
                "orb_high": orb_h,
                "orb_low": orb_l,
                "vwap": vwap_est,
                "pivot": pivots["pivot"],
                "cpr_width_pct": pivots["cpr_width_pct"],
                "is_narrow_cpr": pivots["is_narrow_cpr"],
                "rvol": rvol,
                "atr_14": round(atr_val, 2),
                "rs_vs_nifty": rs_val,
                "orb_signal": "BULLISH BREAKOUT" if is_orb_bull else ("BEARISH BREAKDOWN" if is_orb_bear else "INSIDE RANGE"),
                "pdh_pdl_signal": "PDH BREAKOUT" if is_pdh_breakout else ("PDL BREAKDOWN" if is_pdl_breakdown else "WITHIN PREV DAY RANGE"),
                "vwap_bias": "ABOVE VWAP" if is_vwap_bull else ("AT VWAP (PULLBACK)" if is_vwap_pullback else "BELOW VWAP")
            }

            if is_orb_bull or is_orb_bear:
                orb_breakouts.append(candidate)
            if is_pdh_breakout or is_pdl_breakdown:
                pdh_pdl_breakouts.append(candidate)
            if is_vwap_bull or is_vwap_pullback:
                vwap_trends.append(candidate)

            all_intraday_candidates.append(candidate)

        except Exception:
            continue

    return {
        "orb_breakouts": orb_breakouts,
        "pdh_pdl_breakouts": pdh_pdl_breakouts,
        "vwap_trends": vwap_trends,
        "all_candidates": all_intraday_candidates,
        "total_scanned": len(symbols),
        "data_source": provider.get_provider_name(),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
