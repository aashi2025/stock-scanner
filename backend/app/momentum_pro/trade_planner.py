"""
Momentum Pro — Systematic Trade Planner & Position Sizing Calculator.
Calculates objective entry levels, structural ATR stop-loss, asymmetric targets,
and risk-managed position sizing based on account capital.

Disclaimer: All values are mathematical risk plans for educational/research purposes,
NOT financial advice or buy/sell orders.
"""

from typing import Dict, Any

TRADE_PLAN_DISCLAIMER = (
    "The trade levels and position sizes below are calculated systematically using "
    "volatility (ATR) and price structure. They are strictly research heuristics and "
    "risk-management guidelines, NOT guaranteed targets, financial advice, or buy recommendations."
)

def calculate_trade_plan(
    symbol: str,
    price: float,
    atr_14: float,
    swing_low: float,
    resistance: float,
    account_capital: float = 100000.0,
    risk_per_trade_pct: float = 1.0,
    target_1_multiplier: float = 1.5,
    target_2_multiplier: float = 2.0,
    target_3_multiplier: float = 3.0
) -> Dict[str, Any]:
    """
    Computes complete risk plan and position sizing for a stock setup.
    """
    if price <= 0.0:
        return {
            "symbol": symbol,
            "entry_reference": 0.0,
            "stop_loss": 0.0,
            "risk_per_share": 0.0,
            "risk_pct_of_price": 0.0,
            "target_1": 0.0,
            "target_2": 0.0,
            "target_3": 0.0,
            "reward_risk_ratio": 0.0,
            "position_shares": 0,
            "total_investment": 0.0,
            "capital_allocation_pct": 0.0,
            "max_risk_amount": 0.0,
            "disclaimer": TRADE_PLAN_DISCLAIMER
        }

    # 1. Entry zone
    entry = round(price, 2)

    # 2. Structural Stop Loss:
    # Use max of (Swing Low, Entry - 1.5 * ATR_14)
    # Ensure minimum risk of 1.5% and maximum risk of 8% to keep realistic swing trade parameters
    atr_buffer = 1.5 * (atr_14 if atr_14 > 0 else (price * 0.02))
    sl_structural = swing_low if (swing_low > 0 and swing_low < entry) else (entry - atr_buffer)
    sl_atr = entry - atr_buffer

    # Pick the tighter between structural and ATR stop to protect capital, but not tighter than 1.5%
    raw_sl = max(sl_structural, sl_atr)
    
    # Floor check: stop loss should not be above 98.5% of price or below 90%
    if raw_sl >= (entry * 0.985):
        stop_loss = round(entry * 0.975, 2) # Default 2.5% stop
    elif raw_sl < (entry * 0.90):
        stop_loss = round(entry * 0.92, 2) # Cap at 8% maximum stop
    else:
        stop_loss = round(raw_sl, 2)

    risk_per_share = round(entry - stop_loss, 2)
    risk_pct = round((risk_per_share / entry) * 100, 2) if entry > 0 else 0.0

    # 3. Targets based on R-multiples
    target_1 = round(entry + (risk_per_share * target_1_multiplier), 2)
    target_2 = round(entry + (risk_per_share * target_2_multiplier), 2)
    target_3 = round(entry + (risk_per_share * target_3_multiplier), 2)

    # 4. Position Sizing based on Account Capital & User Risk %
    max_risk_capital = round(account_capital * (risk_per_trade_pct / 100.0), 2)
    
    if risk_per_share > 0:
        shares = int(max_risk_capital // risk_per_share)
    else:
        shares = 0

    # Capital constraint: cannot allocate more than 100% of capital to a single trade
    if (shares * entry) > account_capital:
        shares = int(account_capital // entry)

    total_investment = round(shares * entry, 2)
    capital_allocation = round((total_investment / account_capital * 100), 2) if account_capital > 0 else 0.0

    rrr_target_2 = round(target_2_multiplier, 2)

    return {
        "symbol": symbol,
        "entry_reference": entry,
        "entry_zone": f"₹{entry:,.2f} - ₹{(entry * 1.008):,.2f}",
        "stop_loss": stop_loss,
        "stop_loss_pct": f"-{risk_pct}%",
        "risk_per_share": risk_per_share,
        "risk_pct_of_price": risk_pct,
        "target_1": target_1,
        "target_1_gain_pct": f"+{round(((target_1 - entry) / entry * 100), 2)}%",
        "target_2": target_2,
        "target_2_gain_pct": f"+{round(((target_2 - entry) / entry * 100), 2)}%",
        "target_3": target_3,
        "target_3_gain_pct": f"+{round(((target_3 - entry) / entry * 100), 2)}%",
        "reward_risk_ratio": f"1 : {rrr_target_2}",
        "position_shares": shares,
        "total_investment": total_investment,
        "capital_allocation_pct": capital_allocation,
        "max_risk_amount": max_risk_capital,
        "disclaimer": TRADE_PLAN_DISCLAIMER
    }
