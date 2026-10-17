"""
Momentum Pro — Multi-Stage Scanner Engine.
Identifies:
1. Fresh RSI 14 Crossovers above 50 (Completed candle)
2. Confirmed Price Breakouts with Relative Volume Expansion (RVOL)
3. Pre-Breakout Watchlist (Tight consolidation near 20D resistance, labeled WATCHLIST)
4. Comprehensive Composite Setup Scores (0-100)
"""

from typing import List, Dict, Any, Optional
import pandas as pd
from datetime import datetime

from backend.app.data_providers.base import MarketDataProvider
from backend.app.indicators.calculations import compute_momentum_pro_indicators
from backend.app.momentum_pro.scoring import calculate_momentum_setup_score
from backend.app.momentum_pro.trade_planner import calculate_trade_plan

DEFAULT_UNIVERSE = [
    "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK",
    "SBIN", "BHARTIARTL", "ITC", "LT", "MARUTI"
]

def run_momentum_pro_scan(
    provider: MarketDataProvider,
    symbols: Optional[List[str]] = None,
    account_capital: float = 100000.0,
    risk_per_trade_pct: float = 1.0,
    min_setup_score: float = 40.0
) -> Dict[str, Any]:
    """
    Executes complete Momentum Pro scan across universe.
    Returns:
    - confirmed_breakouts
    - fresh_rsi_crossovers
    - pre_breakout_watchlist
    - all_candidates (ranked by score)
    - market_context (Nifty 50 status)
    - scan_timestamp
    - data_source
    """
    if symbols is None or len(symbols) == 0:
        if hasattr(provider, "list_available_symbols"):
            symbols = provider.list_available_symbols()
        if not symbols:
            symbols = DEFAULT_UNIVERSE

    # 1. Fetch Nifty 50 for benchmark comparison
    nifty_df = provider.get_historical_data("NIFTY 50", period="1y", interval="1d")
    if nifty_df.empty:
        nifty_df = provider.get_historical_data("NIFTY_50", period="1y", interval="1d")

    confirmed_breakouts = []
    fresh_rsi_crossovers = []
    pre_breakout_watchlist = []
    all_candidates = []

    for sym in symbols:
        try:
            df = provider.get_historical_data(sym, period="1y", interval="1d")
            if df.empty or len(df) < 15:
                continue

            ind = compute_momentum_pro_indicators(df, nifty_df)
            score_data = calculate_momentum_setup_score(ind)
            plan = calculate_trade_plan(
                symbol=sym,
                price=ind["price"],
                atr_14=ind["atr_14"],
                swing_low=ind["swing_low_20d"],
                resistance=ind["resistance_20d"],
                account_capital=account_capital,
                risk_per_trade_pct=risk_per_trade_pct
            )

            candidate_row = {
                "symbol": sym,
                "price": ind["price"],
                "ema_9": ind["ema_9"],
                "ema_20": ind["ema_20"],
                "sma_50": ind["sma_50"],
                "sma_200": ind["sma_200"],
                "rsi_14": ind["rsi_14"],
                "rsi_fresh_crossover": ind["rsi_fresh_crossover"],
                "rsi_status": ind["rsi_status"],
                "rvol": ind["rvol"],
                "volume": ind["volume"],
                "resistance_20d": ind["resistance_20d"],
                "dist_to_resistance_pct": ind["dist_to_resistance_pct"],
                "rs_vs_nifty_20d": ind["rs_vs_nifty_20d"],
                "rs_vs_nifty_50d": ind["rs_vs_nifty_50d"],
                "is_price_breakout": ind["is_price_breakout"],
                "is_pre_breakout": ind["is_pre_breakout"],
                "momentum_setup_type": ind["momentum_setup_type"],
                "setup_score": score_data["setup_score"],
                "grade": score_data["grade"],
                "badge_color": score_data["badge_color"],
                "score_breakdown": score_data["breakdown"],
                "trade_plan": plan
            }

            # Group into specialized tabs/buckets
            if ind["is_price_breakout"]:
                confirmed_breakouts.append(candidate_row)

            if ind["rsi_fresh_crossover"]:
                fresh_rsi_crossovers.append(candidate_row)

            if ind["is_pre_breakout"]:
                candidate_row["watchlist_label"] = "WATCHLIST (Pre-Breakout)"
                pre_breakout_watchlist.append(candidate_row)

            if score_data["setup_score"] >= min_setup_score:
                all_candidates.append(candidate_row)

        except Exception as e:
            continue

    # Sort all candidates by setup score descending
    all_candidates.sort(key=lambda x: x["setup_score"], reverse=True)
    confirmed_breakouts.sort(key=lambda x: x["setup_score"], reverse=True)
    fresh_rsi_crossovers.sort(key=lambda x: x["setup_score"], reverse=True)
    pre_breakout_watchlist.sort(key=lambda x: x["dist_to_resistance_pct"])

    return {
        "confirmed_breakouts": confirmed_breakouts,
        "fresh_rsi_crossovers": fresh_rsi_crossovers,
        "pre_breakout_watchlist": pre_breakout_watchlist,
        "all_candidates": all_candidates,
        "total_scanned": len(symbols),
        "data_source": provider.get_provider_name(),
        "is_sample_data": provider.is_sample_mode(),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
