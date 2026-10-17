from typing import Dict, Any, List
import pandas as pd
from backend.app.indicators.calculations import compute_all_indicators

def check_setup_invalidation(
    confirmation_score: float,
    stock_df: pd.DataFrame,
    sector_score: float,
    min_confirmation_threshold: float = 60.0
) -> Dict[str, Any]:
    """
    Exit / Invalidation Engine.
    Monitors monitored or watchlist stocks for rule breakdowns and flags setup status.
    Statuses: HOLDING SETUP STATUS, SETUP WEAKENING, SETUP INVALIDATED.
    """
    if stock_df.empty or len(stock_df) < 5:
        return {
            "status": "SETUP WEAKENING",
            "reasons": ["Insufficient data available to confirm setup validity"],
            "score": confirmation_score
        }

    ind = compute_all_indicators(stock_df)
    price = ind["price"]
    sma_50 = ind["sma_50"]
    sma_200 = ind["sma_200"]
    rsi = ind["rsi_14"]
    rs_20 = ind["rs_vs_nifty_20d"]

    invalid_reasons = []
    weakening_reasons = []

    # Hard invalidation triggers
    if price < sma_200:
        invalid_reasons.append(f"Price closed below 200 DMA (₹{price} < ₹{sma_200})")
    if sma_50 < sma_200:
        invalid_reasons.append("50 DMA crossed below 200 DMA (Death Cross)")
    if confirmation_score < 50.0:
        invalid_reasons.append(f"Confirmation score fell below critical threshold ({confirmation_score} < 50.0)")

    # Weakening triggers
    if price < sma_50 and price >= sma_200:
        weakening_reasons.append(f"Price closed below 50 DMA (₹{price} < ₹{sma_50})")
    if rsi < 45.0:
        weakening_reasons.append(f"RSI momentum dropped below 45 ({rsi})")
    if rs_20 < 0.0:
        weakening_reasons.append(f"Relative strength vs NIFTY turned negative ({rs_20}%)")
    if sector_score < 45.0:
        weakening_reasons.append(f"Sector trend weakened (Score: {sector_score}/100)")
    if 50.0 <= confirmation_score < min_confirmation_threshold:
        weakening_reasons.append(f"Confirmation score slipped to watchlist level ({confirmation_score})")

    if invalid_reasons:
        status = "SETUP INVALIDATED"
        reasons = invalid_reasons
    elif weakening_reasons:
        status = "SETUP WEAKENING"
        reasons = weakening_reasons
    else:
        status = "HOLDING SETUP STATUS"
        reasons = ["All technical setup rules remain intact"]

    return {
        "status": status,
        "reasons": reasons,
        "score": confirmation_score
    }
