"""
Advanced Historical Backtesting Engine for Indian Equities.
Zero look-ahead bias: Signal generated at Day T Close -> Execution at Day T+1 Open.
Includes realistic Indian tax structure (STT, Stamp Duty, GST, Exchange Fees, Brokerage).
Reports CAGR, Max Drawdown, Win Rate, Profit Factor, Benchmark Comparison, and Data Limitation Warnings.
"""

from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from datetime import datetime

from backend.app.data_providers.base import MarketDataProvider
from backend.app.universe.universes import get_universe_stocks
from backend.app.indicators.calculations import calculate_ema, calculate_rsi

INDIAN_TAX_DEFAULTS = {
    "stt_delivery_pct": 0.1,         # 0.1% on Buy and Sell
    "stamp_duty_buy_pct": 0.015,     # 0.015% on Buy only
    "exchange_turnover_pct": 0.00345,# NSE turnover fee
    "sebi_turnover_pct": 0.0001,     # SEBI turnover fee
    "gst_pct": 18.0,                 # 18% on (brokerage + exchange + sebi)
    "default_brokerage_per_order": 0.0 # Delivery is free on Zerodha/Groww/AngelOne, or flat Rs 20
}


def calculate_indian_statutory_charges(
    buy_amount: float,
    sell_amount: float,
    brokerage_per_trade: float = 0.0
) -> Dict[str, float]:
    """
    Computes exact statutory charges for Indian equity delivery trading.
    """
    # 1. STT: 0.1% on buy and 0.1% on sell for delivery
    stt = (buy_amount * 0.001) + (sell_amount * 0.001)

    # 2. Stamp Duty: 0.015% on buy
    stamp_duty = buy_amount * 0.00015

    # 3. Exchange Turnover: 0.00345% of total turnover
    turnover = buy_amount + sell_amount
    exchange_charges = turnover * 0.0000345

    # 4. SEBI Charges: Rs 10 per crore (0.0001%)
    sebi_charges = turnover * 0.000001

    # 5. Brokerage: buy and sell
    total_brokerage = brokerage_per_trade * 2.0

    # 6. GST: 18% on (brokerage + exchange + sebi)
    gst_base = total_brokerage + exchange_charges + sebi_charges
    gst = gst_base * 0.18

    total_taxes = stt + stamp_duty + exchange_charges + sebi_charges + total_brokerage + gst

    return {
        "stt": round(stt, 2),
        "stamp_duty": round(stamp_duty, 2),
        "exchange_charges": round(exchange_charges, 2),
        "sebi_charges": round(sebi_charges, 2),
        "brokerage": round(total_brokerage, 2),
        "gst": round(gst, 2),
        "total_charges": round(total_taxes, 2)
    }


def run_historical_backtest(
    provider: MarketDataProvider,
    symbols: Optional[List[str]] = None,
    universe_name: str = "NIFTY 50",
    start_date: str = "2023-01-01",
    end_date: str = "2026-12-31",
    stop_loss_pct: float = 5.0,
    target_pct: float = 12.0,
    min_confirmation_score: float = 65.0,
    slippage_pct: float = 0.2,
    capital_per_trade: float = 50000.0,
    brokerage_per_order: float = 0.0,
    max_holding_days: int = 45
) -> Dict[str, Any]:
    """
    Runs historical simulation with next-session execution and Indian taxes.
    """
    if symbols is None or len(symbols) == 0:
        universe_list = get_universe_stocks(universe_name)
        symbols = [s["symbol"] for s in universe_list[:25]] # Top 25 stocks for fast execution

    all_trades: List[Dict[str, Any]] = []

    # Benchmark tracking (NIFTY 50)
    nifty_df = provider.get_historical_data("NIFTY 50", period="2y", interval="1d")
    nifty_cagr = 0.0
    nifty_total_return = 0.0
    if not nifty_df.empty and len(nifty_df) > 20:
        nifty_mask = (nifty_df.index >= pd.to_datetime(start_date)) & (nifty_df.index <= pd.to_datetime(end_date))
        nifty_filtered = nifty_df[nifty_mask]
        if len(nifty_filtered) >= 2:
            n_start = float(nifty_filtered["Close"].iloc[0])
            n_end = float(nifty_filtered["Close"].iloc[-1])
            nifty_total_return = round(((n_end - n_start) / n_start) * 100, 2)
            years = max(0.1, (nifty_filtered.index[-1] - nifty_filtered.index[0]).days / 365.25)
            if n_start > 0 and n_end > 0:
                nifty_cagr = round((((n_end / n_start) ** (1.0 / years)) - 1.0) * 100, 2)

    for sym in symbols:
        df = provider.get_historical_data(sym, period="2y", interval="1d")
        if df.empty or len(df) < 50:
            continue

        close = df["Close"]
        open_px = df["Open"] if "Open" in df.columns else close
        high_px = df["High"] if "High" in df.columns else close
        low_px = df["Low"] if "Low" in df.columns else close

        ema_50 = calculate_ema(close, 50)
        ema_200 = calculate_ema(close, 200)
        rsi_14 = calculate_rsi(close, 14)

        in_pos = False
        entry_price = 0.0
        entry_date = ""
        entry_idx = 0
        shares = 0
        buy_amount = 0.0

        for i in range(50, len(df) - 1):
            date_val = df.index[i]
            date_str = date_val.strftime("%Y-%m-%d") if hasattr(date_val, "strftime") else str(date_val)

            if date_str < start_date or date_str > end_date:
                continue

            px = float(close.iloc[i])
            e50 = float(ema_50.iloc[i])
            e200 = float(ema_200.iloc[i])
            rsi_val = float(rsi_14.iloc[i])
            rsi_prev = float(rsi_14.iloc[i - 1]) if i > 0 else 50.0

            # Signal rules evaluated at Day T Close:
            # 1. Price > EMA50 and Price > EMA200
            # 2. EMA50 > EMA200
            # 3. RSI crossing or bullish above 50
            trend_ok = (px > e50) and (px > e200) and (e50 > e200)
            fresh_rsi = (rsi_prev <= 50.0) and (rsi_val > 50.0)
            rsi_ok = (rsi_val >= 50.0) and (rsi_val <= 75.0)

            signal_triggered = trend_ok and (fresh_rsi or rsi_ok)

            if not in_pos:
                if signal_triggered:
                    in_pos = True
                    # Next-session Day T+1 Open execution with slippage
                    next_open = float(open_px.iloc[i + 1])
                    entry_price = round(next_open * (1.0 + (slippage_pct / 100.0)), 2)
                    shares = int(capital_per_trade // entry_price) if entry_price > 0 else 0
                    buy_amount = round(shares * entry_price, 2)
                    entry_date = df.index[i + 1].strftime("%Y-%m-%d") if hasattr(df.index[i + 1], "strftime") else str(df.index[i + 1])
                    entry_idx = i + 1
            else:
                holding_days = i - entry_idx
                cur_close = float(close.iloc[i])
                cur_low = float(low_px.iloc[i])
                cur_high = float(high_px.iloc[i])

                stop_price = entry_price * (1.0 - (stop_loss_pct / 100.0))
                target_price = entry_price * (1.0 + (target_pct / 100.0))

                exit_triggered = False
                exit_price = 0.0
                exit_reason = ""

                if cur_low <= stop_price:
                    exit_triggered = True
                    exit_price = round(stop_price * (1.0 - (slippage_pct / 100.0)), 2)
                    exit_reason = f"Stop Loss Triggered (-{stop_loss_pct}%)"
                elif cur_high >= target_price:
                    exit_triggered = True
                    exit_price = round(target_price * (1.0 - (slippage_pct / 100.0)), 2)
                    exit_reason = f"Target Level Reached (+{target_pct}%)"
                elif holding_days >= max_holding_days:
                    exit_triggered = True
                    exit_price = round(cur_close * (1.0 - (slippage_pct / 100.0)), 2)
                    exit_reason = f"Max Holding Exceeded ({max_holding_days} sessions)"
                elif px < e50:
                    exit_triggered = True
                    exit_price = round(cur_close * (1.0 - (slippage_pct / 100.0)), 2)
                    exit_reason = "Trailing Trend Exit (< 50 EMA)"

                if exit_triggered and shares > 0:
                    sell_amount = round(shares * exit_price, 2)
                    tax_info = calculate_indian_statutory_charges(
                        buy_amount, sell_amount, brokerage_per_trade=brokerage_per_order
                    )
                    gross_pnl = sell_amount - buy_amount
                    net_pnl = round(gross_pnl - tax_info["total_charges"], 2)
                    net_ret_pct = round((net_pnl / buy_amount) * 100, 2) if buy_amount > 0 else 0.0

                    all_trades.append({
                        "symbol": sym,
                        "entry_date": entry_date,
                        "entry_price": entry_price,
                        "exit_date": date_str,
                        "exit_price": exit_price,
                        "shares": shares,
                        "capital_deployed": buy_amount,
                        "gross_pnl": round(gross_pnl, 2),
                        "taxes_charges": tax_info["total_charges"],
                        "net_pnl": net_pnl,
                        "net_return_pct": net_ret_pct,
                        "holding_days": holding_days,
                        "exit_reason": exit_reason
                    })
                    in_pos = False

    # Metrics computation
    total_trades = len(all_trades)
    if total_trades == 0:
        return {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate_pct": 0.0,
            "net_pnl_total": 0.0,
            "avg_trade_return_pct": 0.0,
            "cagr_pct": 0.0,
            "max_drawdown_pct": 0.0,
            "profit_factor": 0.0,
            "benchmark_nifty_return_pct": nifty_total_return,
            "benchmark_nifty_cagr_pct": nifty_cagr,
            "trades": [],
            "equity_curve": [],
            "warnings": ["No trades triggered with current parameters. Try adjusting stop loss or date range."],
            "disclaimer": "BACKTEST RESULTS DO NOT GUARANTEE FUTURE LIVE RETURNS."
        }

    # Sort trades chronologically by exit date
    all_trades.sort(key=lambda x: x["exit_date"])

    winning = [t for t in all_trades if t["net_pnl"] > 0]
    losing = [t for t in all_trades if t["net_pnl"] <= 0]
    win_rate = round((len(winning) / total_trades) * 100, 1)

    total_net_pnl = round(sum(t["net_pnl"] for t in all_trades), 2)
    avg_trade_ret = round(sum(t["net_return_pct"] for t in all_trades) / total_trades, 2)

    total_gross_gain = sum(t["gross_pnl"] for t in winning)
    total_gross_loss = abs(sum(t["gross_pnl"] for t in losing))
    profit_factor = round(total_gross_gain / total_gross_loss, 2) if total_gross_loss > 0 else (round(total_gross_gain, 2) if total_gross_gain > 0 else 1.0)

    # Compute Equity Curve and Drawdown
    starting_capital = capital_per_trade * 2.0  # Assumed portfolio base
    running_pnl = 0.0
    equity_series = []
    equity_series.append({"date": start_date, "equity": starting_capital, "pnl": 0.0, "drawdown_pct": 0.0})

    peak_equity = starting_capital
    max_dd_pct = 0.0

    for t in all_trades:
        running_pnl += t["net_pnl"]
        cur_eq = starting_capital + running_pnl
        if cur_eq > peak_equity:
            peak_equity = cur_eq
        dd_pct = round(((peak_equity - cur_eq) / peak_equity) * 100, 2) if peak_equity > 0 else 0.0
        if dd_pct > max_dd_pct:
            max_dd_pct = dd_pct
        equity_series.append({
            "date": t["exit_date"],
            "equity": round(cur_eq, 2),
            "pnl": round(running_pnl, 2),
            "drawdown_pct": dd_pct
        })

    # CAGR calculation
    total_return_pct = round((running_pnl / starting_capital) * 100, 2)
    try:
        dt_start = pd.to_datetime(start_date)
        dt_end = pd.to_datetime(end_date)
        years = max(0.1, (dt_end - dt_start).days / 365.25)
        ending_val = starting_capital + running_pnl
        if ending_val > 0:
            cagr = round((((ending_val / starting_capital) ** (1.0 / years)) - 1.0) * 100, 2)
        else:
            cagr = -100.0
    except Exception:
        cagr = 0.0

    # Data limitations & sample size warning
    warnings = []
    if total_trades < 30:
        warnings.append(f"⚠️ Small Sample Size ({total_trades} trades). Statistical significance is low. Recommend testing on at least 50+ trades.")
    warnings.append("Note: Backtest does not account for corporate actions (splits, bonus, delisting) unless adjusted in raw CSV data.")
    warnings.append("Execution assumes liquidity at next-day Open price with configurable slippage.")

    return {
        "total_trades": total_trades,
        "winning_trades": len(winning),
        "losing_trades": len(losing),
        "win_rate_pct": win_rate,
        "net_pnl_total": total_net_pnl,
        "total_return_pct": total_return_pct,
        "avg_trade_return_pct": avg_trade_ret,
        "cagr_pct": cagr,
        "max_drawdown_pct": max_dd_pct,
        "profit_factor": profit_factor,
        "starting_capital": starting_capital,
        "benchmark_nifty_return_pct": nifty_total_return,
        "benchmark_nifty_cagr_pct": nifty_cagr,
        "trades": all_trades,
        "equity_curve": equity_series,
        "warnings": warnings,
        "disclaimer": (
            "HISTORICAL BACKTEST DISCLAIMER: Past performance is no guarantee of future returns. "
            "All simulated trades apply statutory Indian equity delivery charges and slippage."
        )
    }

# Backward-compatibility alias
run_backtest = run_historical_backtest

