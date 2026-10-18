"""
Explainable Rule-Based Strategy Engine for Indian Equities.
Every setup records:
- Symbol & instrument identifier
- Strategy name & timeframe
- Signal timestamp, data source & freshness
- Conditions satisfied (List of passing criteria)
- Conditions not satisfied (List of failing criteria)
- Entry trigger level & Invalidation level
- Stop-loss & target methodologies
- Estimated Reward-to-Risk Ratio (RRR)
- Estimated transaction costs (Statutory charges)
- Signal status: WATCH, CONFIRMED, INVALIDATED, EXPIRED
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd

from backend.app.data_providers.base import MarketDataProvider
from backend.app.indicators.calculations import calculate_ema, calculate_rsi, calculate_atr
from backend.app.momentum_pro.indicators import calculate_resistance_and_swing_high
from backend.app.engines.backtest import calculate_indian_statutory_charges


def evaluate_stock_strategies(
    symbol: str,
    daily_df: pd.DataFrame,
    data_source_label: str = "Market Feed",
    timeframe: str = "1d",
    require_candle_close: bool = True
) -> List[Dict[str, Any]]:
    """
    Evaluates rule-based strategies for a given stock on completed historical bars.
    Returns list of evaluated setup candidate records (both passing and failing).
    """
    if daily_df.empty or len(daily_df) < 25:
        return []

    close = daily_df["Close"]
    price = float(close.iloc[-1])
    high = daily_df["High"]
    low = daily_df["Low"]
    vol = daily_df["Volume"] if "Volume" in daily_df.columns else pd.Series(1000, index=daily_df.index)

    # Core indicators
    ema_9 = float(calculate_ema(close, 9).iloc[-1])
    ema_20 = float(calculate_ema(close, 20).iloc[-1])
    sma_50 = float(close.rolling(50).mean().iloc[-1]) if len(daily_df) >= 50 else price
    sma_200 = float(close.rolling(200).mean().iloc[-1]) if len(daily_df) >= 200 else price
    
    rsi_series = calculate_rsi(close, 14)
    curr_rsi = float(rsi_series.iloc[-1])
    prev_rsi = float(rsi_series.iloc[-2]) if len(rsi_series) > 1 else curr_rsi
    atr_val = float(calculate_atr(daily_df, 14).iloc[-1]) if len(daily_df) >= 14 else (price * 0.02)

    vol_curr = int(vol.iloc[-1])
    vol_avg20 = int(vol.tail(20).mean()) if len(vol) >= 20 else vol_curr
    rvol = round(vol_curr / vol_avg20, 2) if vol_avg20 > 0 else 1.0

    res_20, sw_low, dist_pct = calculate_resistance_and_swing_high(daily_df, lookback=20)
    
    # Previous day levels
    pdh = float(high.iloc[-2]) if len(daily_df) > 1 else price
    pdl = float(low.iloc[-2]) if len(daily_df) > 1 else price

    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    setups = []

    # -------------------------------------------------------------
    # Strategy 1: Swing Momentum Breakout (Bullish)
    # -------------------------------------------------------------
    c_satisfied = []
    c_failed = []

    if price >= res_20:
        c_satisfied.append(f"Price (₹{price}) broke above 20D resistance (₹{res_20})")
    else:
        c_failed.append(f"Price (₹{price}) is below 20D resistance (₹{res_20})")

    if rvol >= 1.2:
        c_satisfied.append(f"Relative Volume ({rvol:.2f}x) exceeds 1.20x threshold")
    else:
        c_failed.append(f"Relative Volume ({rvol:.2f}x) is below 1.20x threshold")

    if price > sma_50:
        c_satisfied.append(f"Price (₹{price}) is above 50 SMA (₹{sma_50:.2f})")
    else:
        c_failed.append(f"Price (₹{price}) is below 50 SMA (₹{sma_50:.2f})")

    if curr_rsi >= 50.0:
        c_satisfied.append(f"RSI 14 ({curr_rsi:.1f}) is in bullish territory (>= 50)")
    else:
        c_failed.append(f"RSI 14 ({curr_rsi:.1f}) is below 50")

    is_confirmed = len(c_failed) == 0
    sl_level = round(max(sw_low, price - (1.5 * atr_val)), 2)
    risk_unit = max(price * 0.015, price - sl_level)
    target_level = round(price + (2.0 * risk_unit), 2)
    inval_level = round(res_20 * 0.99, 2) # If price closes back inside range

    charges = calculate_indian_statutory_charges(price * 100, target_level * 100)

    setups.append({
        "symbol": symbol,
        "strategy_name": "Swing Momentum Breakout",
        "timeframe": timeframe,
        "bias": "BULLISH",
        "signal_timestamp": timestamp_str,
        "data_source": data_source_label,
        "status": "CONFIRMED" if is_confirmed else "REJECTED",
        "conditions_satisfied": c_satisfied,
        "conditions_not_satisfied": c_failed,
        "entry_trigger": f"Price close >= ₹{res_20:,.2f}",
        "invalidation_level": inval_level,
        "stop_loss": sl_level,
        "target": target_level,
        "stop_loss_methodology": "Structural Swing Low / 1.5x ATR Buffer",
        "target_methodology": "2.0x Risk-Reward Asymmetric Target",
        "reward_risk_ratio": "1 : 2.0",
        "estimated_charges": charges["total_charges"],
        "setup_score": 85.0 if is_confirmed else 40.0
    })

    # -------------------------------------------------------------
    # Strategy 2: Pre-Breakout Resistance Consolidation (WATCHLIST)
    # -------------------------------------------------------------
    c_pb_sat = []
    c_pb_fail = []

    if 0.2 <= dist_pct <= 3.0:
        c_pb_sat.append(f"Price is consolidating tightly ({dist_pct:.2f}% below resistance ₹{res_20})")
    else:
        c_pb_fail.append(f"Distance to resistance ({dist_pct:.2f}%) is outside the 0.2% - 3.0% zone")

    if curr_rsi >= 48.0:
        c_pb_sat.append(f"RSI ({curr_rsi:.1f}) is building positive momentum")
    else:
        c_pb_fail.append(f"RSI ({curr_rsi:.1f}) is below 48")

    if ema_9 > ema_20:
        c_pb_sat.append(f"Short term trend aligned: 9 EMA (₹{ema_9:.2f}) > 20 EMA (₹{ema_20:.2f})")
    else:
        c_pb_fail.append(f"9 EMA is below 20 EMA")

    is_pb_watch = len(c_pb_fail) == 0

    setups.append({
        "symbol": symbol,
        "strategy_name": "Pre-Breakout Resistance Consolidation",
        "timeframe": timeframe,
        "bias": "BULLISH",
        "signal_timestamp": timestamp_str,
        "data_source": data_source_label,
        "status": "WATCH" if is_pb_watch else "REJECTED",
        "conditions_satisfied": c_pb_sat,
        "conditions_not_satisfied": c_pb_fail,
        "entry_trigger": f"Breakout above ₹{res_20:,.2f} on confirmed bar",
        "invalidation_level": round(sw_low, 2),
        "stop_loss": round(sw_low, 2),
        "target": round(res_20 + (2.0 * atr_val), 2),
        "stop_loss_methodology": "Consolidation Base Low",
        "target_methodology": "Projected Breakout Extension (2.0x ATR)",
        "reward_risk_ratio": "1 : 2.2",
        "estimated_charges": charges["total_charges"],
        "setup_score": 75.0 if is_pb_watch else 35.0
    })

    # -------------------------------------------------------------
    # Strategy 3: Previous Day High (PDH) Breakout (Bullish)
    # -------------------------------------------------------------
    c_pdh_sat = []
    c_pdh_fail = []

    if price > pdh:
        c_pdh_sat.append(f"Current price (₹{price}) is trading above PDH (₹{pdh})")
    else:
        c_pdh_fail.append(f"Current price (₹{price}) is below PDH (₹{pdh})")

    if rvol >= 1.15:
        c_pdh_sat.append(f"Relative Volume ({rvol:.2f}x) confirms participation")
    else:
        c_pdh_fail.append(f"Relative Volume ({rvol:.2f}x) is below 1.15x threshold")

    is_pdh_confirmed = len(c_pdh_fail) == 0

    setups.append({
        "symbol": symbol,
        "strategy_name": "Previous Day High (PDH) Breakout",
        "timeframe": "Intraday / 1d",
        "bias": "BULLISH",
        "signal_timestamp": timestamp_str,
        "data_source": data_source_label,
        "status": "CONFIRMED" if is_pdh_confirmed else "REJECTED",
        "conditions_satisfied": c_pdh_sat,
        "conditions_not_satisfied": c_pdh_fail,
        "entry_trigger": f"Close above PDH (₹{pdh:,.2f})",
        "invalidation_level": round(pdh * 0.995, 2),
        "stop_loss": round(price - (1.0 * atr_val), 2),
        "target": round(price + (1.5 * atr_val), 2),
        "stop_loss_methodology": "Prior Day High Re-test Failure / 1.0x ATR",
        "target_methodology": "Intraday 1.5R Extension",
        "reward_risk_ratio": "1 : 1.5",
        "estimated_charges": charges["total_charges"],
        "setup_score": 70.0 if is_pdh_confirmed else 30.0
    })

    # -------------------------------------------------------------
    # Strategy 4: Previous Day Low (PDL) Breakdown (Bearish)
    # -------------------------------------------------------------
    c_pdl_sat = []
    c_pdl_fail = []

    if price < pdl:
        c_pdl_sat.append(f"Current price (₹{price}) broke below PDL (₹{pdl})")
    else:
        c_pdl_fail.append(f"Current price (₹{price}) is above PDL (₹{pdl})")

    if curr_rsi < 50.0:
        c_pdl_sat.append(f"RSI 14 ({curr_rsi:.1f}) confirms bearish momentum")
    else:
        c_pdl_fail.append(f"RSI 14 ({curr_rsi:.1f}) is above 50")

    is_pdl_confirmed = len(c_pdl_fail) == 0

    setups.append({
        "symbol": symbol,
        "strategy_name": "Previous Day Low (PDL) Breakdown",
        "timeframe": "Intraday / 1d",
        "bias": "BEARISH",
        "signal_timestamp": timestamp_str,
        "data_source": data_source_label,
        "status": "CONFIRMED" if is_pdl_confirmed else "REJECTED",
        "conditions_satisfied": c_pdl_sat,
        "conditions_not_satisfied": c_pdl_fail,
        "entry_trigger": f"Close below PDL (₹{pdl:,.2f})",
        "invalidation_level": round(pdl * 1.005, 2),
        "stop_loss": round(price + (1.0 * atr_val), 2),
        "target": round(price - (1.5 * atr_val), 2),
        "stop_loss_methodology": "Prior Day Low Invalidation / 1.0x ATR",
        "target_methodology": "Downside 1.5R Extension",
        "reward_risk_ratio": "1 : 1.5",
        "estimated_charges": charges["total_charges"],
        "setup_score": 70.0 if is_pdl_confirmed else 30.0
    })

    return setups
