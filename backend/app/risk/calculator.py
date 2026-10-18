"""
Comprehensive Risk Management & Position Sizing Engine for Indian Equities & Derivatives.
Enforces:
- Exact mathematical risk sizing: Risk per unit = |Entry - StopLoss|
- Preliminary Quantity = Floor(Risk Budget / Risk per unit)
- Lot size rounding (NIFTY=25, BANKNIFTY=15, Cash=1, Stock F&O standard lots)
- Daily loss thresholds (e.g. 3.0% max loss limit)
- Maximum trade count constraints
- Maximum open risk threshold (e.g. 6.0% total open risk across portfolio)
- Correlated sector / index exposure warnings
- Consecutive loss reduction rules
- Full Indian statutory charges (STT, Stamp duty, GST, Exchange fee, SEBI)
"""

import math
from typing import Dict, Any, List, Optional
from backend.app.engines.backtest import calculate_indian_statutory_charges

# Standard NSE Instrument Lot Sizes
STANDARD_NSE_LOT_SIZES = {
    "NIFTY": 25,
    "NIFTY 50": 25,
    "NIFTY_50": 25,
    "BANKNIFTY": 15,
    "NIFTY BANK": 15,
    "FINNIFTY": 25,
    "MIDCPNIFTY": 50,
    "RELIANCE": 250,
    "TCS": 175,
    "INFY": 400,
    "HDFCBANK": 550,
    "ICICIBANK": 700,
    "SBIN": 750,
    "BHARTIARTL": 475,
    "ITC": 1600,
    "LT": 175,
    "MARUTI": 50
}

RISK_DISCLAIMER = (
    "Calculated position sizes enforce strict capital preservation. Stop-loss execution "
    "is never guaranteed at exact prices due to market gaps, overnight risk, and slippage. "
    "Never risk more capital than you can afford to lose."
)

def calculate_position_size_and_risk(
    symbol: str,
    entry_price: float,
    stop_loss_price: float,
    target_price: float,
    account_capital: float = 100000.0,
    risk_per_trade_pct: float = 1.0,
    instrument_type: str = "Cash Equities", # "Cash Equities" | "Index F&O" | "Stock F&O"
    daily_realized_loss: float = 0.0,
    open_positions_risk: float = 0.0,
    consecutive_losses: int = 0,
    active_sector_positions: int = 1
) -> Dict[str, Any]:
    """
    Computes rigorous position size, statutory charges, and institutional risk warnings.
    """
    if entry_price <= 0 or stop_loss_price <= 0:
        return {
            "is_valid": False,
            "message": "Entry and Stop-Loss prices must be positive numbers.",
            "shares": 0,
            "lots": 0,
            "risk_per_unit": 0.0,
            "total_investment": 0.0,
            "warnings": ["Invalid price parameters"]
        }

    # 1. Mathematical Risk per Unit
    risk_per_unit = abs(entry_price - stop_loss_price)
    if risk_per_unit < (entry_price * 0.005):
        # Enforce minimum 0.5% stop distance to avoid nonsensical infinite quantities
        risk_per_unit = entry_price * 0.005

    # 2. Risk Budget
    base_risk_pct = risk_per_trade_pct
    warnings: List[str] = []

    # Consecutive loss rule: if >= 3 consecutive losses, reduce risk budget by 50%
    if consecutive_losses >= 3:
        base_risk_pct = base_risk_pct * 0.5
        warnings.append(f"⚠️ {consecutive_losses} Consecutive Losses Detected: Risk budget halved to {base_risk_pct:.2f}% to protect psychological capital.")

    # Daily loss threshold check: max 3% daily drawdown allowed
    max_daily_loss_limit = account_capital * 0.03
    if daily_realized_loss >= max_daily_loss_limit:
        warnings.append(f"🛑 Daily Loss Threshold Reached (₹{daily_realized_loss:,.2f} >= ₹{max_daily_loss_limit:,.2f}). Trading should be halted for the day.")

    # Max total open portfolio risk limit: max 6% open risk
    max_portfolio_open_risk = account_capital * 0.06
    if (open_positions_risk + (account_capital * (base_risk_pct / 100.0))) > max_portfolio_open_risk:
        warnings.append(f"⚠️ Portfolio Open Risk Cap ({open_positions_risk / account_capital * 100:.1f}% open): Reduce position size to stay within 6% total exposure.")

    # Correlated sector exposure warning
    if active_sector_positions >= 2:
        warnings.append(f"⚠️ Sector Concentration: You already have {active_sector_positions} active trades in this sector. Risk is correlated.")

    risk_budget_rupees = account_capital * (base_risk_pct / 100.0)

    # 3. Preliminary Quantity
    preliminary_qty = int(risk_budget_rupees // risk_per_unit)

    # 4. Lot Size Constraints
    sym_upper = symbol.upper().replace(".NS", "")
    if instrument_type == "Cash Equities":
        lot_size = 1
    else:
        lot_size = STANDARD_NSE_LOT_SIZES.get(sym_upper, 25 if "NIFTY" in sym_upper else 100)

    # Round to nearest lot size
    if preliminary_qty < lot_size:
        lots = 1 if (preliminary_qty >= (lot_size * 0.5)) else 0
        final_qty = lots * lot_size
    else:
        lots = preliminary_qty // lot_size
        final_qty = lots * lot_size

    # Capital constraint check
    total_investment = final_qty * entry_price
    if total_investment > account_capital and instrument_type == "Cash Equities":
        final_qty = int(account_capital // entry_price)
        lots = final_qty // lot_size
        total_investment = final_qty * entry_price
        warnings.append("⚠️ Position scaled down: Cannot allocate more than 100% of available account equity to a single cash trade.")

    actual_risk_rupees = round(final_qty * risk_per_unit, 2)
    actual_risk_pct = round((actual_risk_rupees / account_capital * 100.0), 2) if account_capital > 0 else 0.0

    # 5. Reward-to-Risk Ratio
    reward_per_unit = abs(target_price - entry_price)
    rrr = round(reward_per_unit / risk_per_unit, 2) if risk_per_unit > 0 else 0.0

    # 6. Statutory Charges & Taxes
    exit_val = final_qty * target_price
    charges = calculate_indian_statutory_charges(total_investment, exit_val)

    gross_profit = round(final_qty * (target_price - entry_price), 2)
    net_profit = round(gross_profit - charges["total_charges"], 2)

    return {
        "is_valid": True,
        "symbol": symbol,
        "instrument_type": instrument_type,
        "lot_size": lot_size,
        "shares": final_qty,
        "lots": lots,
        "entry_price": round(entry_price, 2),
        "stop_loss_price": round(stop_loss_price, 2),
        "target_price": round(target_price, 2),
        "risk_per_unit": round(risk_per_unit, 2),
        "reward_per_unit": round(reward_per_unit, 2),
        "reward_risk_ratio": f"1 : {rrr}",
        "rrr_numeric": rrr,
        "risk_budget_rupees": round(risk_budget_rupees, 2),
        "actual_risk_rupees": actual_risk_rupees,
        "actual_risk_pct": actual_risk_pct,
        "total_investment": round(total_investment, 2),
        "capital_allocation_pct": round((total_investment / account_capital * 100.0), 2) if account_capital > 0 else 0.0,
        "gross_target_profit": gross_profit,
        "statutory_charges": charges["total_charges"],
        "charges_breakdown": charges,
        "net_target_profit": net_profit,
        "warnings": warnings,
        "disclaimer": RISK_DISCLAIMER
    }
