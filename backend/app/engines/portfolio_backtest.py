"""
Multi-Stock Portfolio Backtesting Simulator.
Simulates a real-world multi-stock portfolio with cash management,
max concurrent position constraints, priority ranking, and Indian taxes.
Zero look-ahead bias: Day T Close signal -> Day T+1 Open entry.
"""

from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from datetime import datetime

from backend.app.data_providers.base import MarketDataProvider
from backend.app.engines.backtest import calculate_indian_statutory_charges
from backend.app.indicators.calculations import calculate_ema, calculate_rsi, calculate_atr


def run_portfolio_backtest(
    provider: MarketDataProvider,
    symbols: List[str],
    start_date: str = "2023-01-01",
    end_date: str = "2026-10-15",
    initial_capital: float = 500000.0,
    max_positions: int = 5,
    stop_loss_pct: float = 5.0,
    target_pct: float = 12.0,
    slippage_pct: float = 0.2,
    brokerage_per_order: float = 0.0,
    trailing_exit_type: str = "ema_50",  # "ema_50", "fixed_target", "atr_trailing"
    atr_multiplier: float = 2.0
) -> Dict[str, Any]:
    """
    Simulates portfolio execution across multiple stocks with capital constraints.
    """
    # 1. Load historical data for all stocks
    stock_data: Dict[str, pd.DataFrame] = {}
    for s in symbols:
        df = provider.get_historical_data(s, period="2y", interval="1d")
        if not df.empty and len(df) >= 60:
            clean_df = df.copy()
            clean_df["50_EMA"] = calculate_ema(clean_df["Close"], 50)
            clean_df["200_EMA"] = calculate_ema(clean_df["Close"], 200)
            clean_df["RSI_14"] = calculate_rsi(clean_df["Close"], 14)
            clean_df["ATR_14"] = calculate_atr(clean_df, 14)
            stock_data[s] = clean_df

    if not stock_data:
        return {
            "error": "No valid historical data found for backtest symbols.",
            "total_trades": 0,
            "cagr_pct": 0.0,
            "max_drawdown_pct": 0.0
        }

    # Extract all unique trading calendar dates across all datasets
    all_dates = set()
    for s, df in stock_data.items():
        all_dates.update([d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d) for d in df.index])

    sorted_dates = sorted([d for d in all_dates if start_date <= d <= end_date])
    if len(sorted_dates) < 20:
        return {
            "error": "Insufficient trading dates in selected date range.",
            "total_trades": 0,
            "cagr_pct": 0.0,
            "max_drawdown_pct": 0.0
        }

    # Simulation State
    cash = float(initial_capital)
    open_positions: Dict[str, Dict[str, Any]] = {}
    closed_trades: List[Dict[str, Any]] = []
    equity_curve: List[Dict[str, Any]] = []

    # Map dates to row indices for speed
    date_to_idx = {s: {df.index[i].strftime("%Y-%m-%d") if hasattr(df.index[i], "strftime") else str(df.index[i]): i for i in range(len(df))} for s, df in stock_data.items()}

    for day_i, cur_date in enumerate(sorted_dates):
        # 1. PROCESS EXITS FIRST (Check stop loss, target, or trailing EMA)
        symbols_to_close = []
        for sym, pos in list(open_positions.items()):
            df = stock_data[sym]
            if cur_date not in date_to_idx[sym]:
                continue
            idx = date_to_idx[sym][cur_date]
            bar = df.iloc[idx]

            cur_px = float(bar["Close"])
            cur_high = float(bar["High"]) if "High" in bar else cur_px
            cur_low = float(bar["Low"]) if "Low" in bar else cur_px
            entry_px = float(pos["entry_price"])
            shares = int(pos["shares"])

            pos["highest_high"] = max(pos.get("highest_high", cur_high), cur_high)
            holding_days = day_i - pos["entry_day_idx"]

            exit_triggered = False
            exit_px = 0.0
            exit_reason = ""

            stop_px = entry_px * (1.0 - (stop_loss_pct / 100.0))
            target_px = entry_px * (1.0 + (target_pct / 100.0))

            if cur_low <= stop_px:
                exit_triggered = True
                exit_px = round(stop_px * (1.0 - (slippage_pct / 100.0)), 2)
                exit_reason = f"Stop Loss Hit (-{stop_loss_pct}%)"
            elif cur_high >= target_px:
                exit_triggered = True
                exit_px = round(target_px * (1.0 - (slippage_pct / 100.0)), 2)
                exit_reason = f"Target Level Reached (+{target_pct}%)"
            elif trailing_exit_type == "ema_50" and cur_px < float(bar["50_EMA"]):
                exit_triggered = True
                exit_px = round(cur_px * (1.0 - (slippage_pct / 100.0)), 2)
                exit_reason = "Trailing Trend Exit (< 50 EMA)"
            elif trailing_exit_type == "atr_trailing":
                trailing_stop = pos["highest_high"] - (atr_multiplier * float(bar["ATR_14"]))
                if cur_low <= trailing_stop:
                    exit_triggered = True
                    exit_px = round(trailing_stop * (1.0 - (slippage_pct / 100.0)), 2)
                    exit_reason = f"ATR Trailing Stop Hit ({atr_multiplier}x ATR)"
            elif holding_days >= 60:
                exit_triggered = True
                exit_px = round(cur_px * (1.0 - (slippage_pct / 100.0)), 2)
                exit_reason = "Max Holding Period (60 days)"

            if exit_triggered:
                symbols_to_close.append((sym, exit_px, exit_reason))

        # Close positions and return cash
        for sym, exit_px, exit_reason in symbols_to_close:
            pos = open_positions.pop(sym)
            shares = pos["shares"]
            buy_amt = pos["capital_deployed"]
            sell_amt = round(shares * exit_px, 2)

            tax_info = calculate_indian_statutory_charges(
                buy_amt, sell_amt, brokerage_per_trade=brokerage_per_order
            )
            net_proceeds = sell_amt - tax_info["total_charges"]
            cash += net_proceeds

            gross_pnl = sell_amt - buy_amt
            net_pnl = round(gross_pnl - tax_info["total_charges"], 2)
            net_ret_pct = round((net_pnl / buy_amt) * 100, 2) if buy_amt > 0 else 0.0

            closed_trades.append({
                "symbol": sym,
                "entry_date": pos["entry_date"],
                "entry_price": pos["entry_price"],
                "exit_date": cur_date,
                "exit_price": exit_px,
                "shares": shares,
                "capital_deployed": buy_amt,
                "gross_pnl": round(gross_pnl, 2),
                "taxes_charges": tax_info["total_charges"],
                "net_pnl": net_pnl,
                "net_return_pct": net_ret_pct,
                "holding_days": day_i - pos["entry_day_idx"],
                "exit_reason": exit_reason
            })

        # 2. PROCESS NEW ENTRIES IF SLOTS ARE OPEN
        available_slots = max_positions - len(open_positions)
        if available_slots > 0 and day_i > 0:
            prev_date = sorted_dates[day_i - 1]
            candidates = []

            for sym, df in stock_data.items():
                if sym in open_positions or sym in ["NIFTY 50", "NIFTY_50", "^NSEI"]:
                    continue
                if prev_date not in date_to_idx[sym] or cur_date not in date_to_idx[sym]:
                    continue

                prev_idx = date_to_idx[sym][prev_date]
                if prev_idx < 50:
                    continue

                bar_prev = df.iloc[prev_idx]
                close_prev = float(bar_prev["Close"])
                e50_prev = float(bar_prev["50_EMA"])
                e200_prev = float(bar_prev["200_EMA"])
                rsi_prev = float(bar_prev["RSI_14"])

                # Prior bar for crossover check
                bar_prior = df.iloc[prev_idx - 1]
                rsi_prior = float(bar_prior["RSI_14"])

                trend_aligned = (close_prev > e50_prev) and (close_prev > e200_prev) and (e50_prev > e200_prev)
                fresh_cross = (rsi_prior <= 50.0) and (rsi_prev > 50.0)

                if trend_aligned and (fresh_cross or (50.0 <= rsi_prev <= 70.0)):
                    score = (25.0 if fresh_cross else 15.0) + (35.0 if close_prev > e50_prev else 0) + (20.0 if e50_prev > e200_prev else 0)
                    candidates.append((sym, score, df.iloc[date_to_idx[sym][cur_date]]))

            # Sort candidates by score descending and take top available slots
            candidates.sort(key=lambda x: x[1], reverse=True)
            top_candidates = candidates[:available_slots]

            # Calculate allocation per trade (equal weight of portfolio capital)
            current_portfolio_val = cash + sum(pos["shares"] * float(stock_data[s]["Close"].iloc[date_to_idx[s][cur_date]]) for s, pos in open_positions.items() if cur_date in date_to_idx[s])
            target_alloc_per_trade = current_portfolio_val / max_positions

            for sym, score, today_bar in top_candidates:
                open_px = float(today_bar["Open"]) if "Open" in today_bar else float(today_bar["Close"])
                entry_px = round(open_px * (1.0 + (slippage_pct / 100.0)), 2)

                alloc_amt = min(cash * 0.95, target_alloc_per_trade)
                shares = int(alloc_amt // entry_px) if entry_px > 0 else 0

                if shares > 0 and cash >= (shares * entry_px):
                    deployed = round(shares * entry_px, 2)
                    cash -= deployed
                    open_positions[sym] = {
                        "entry_date": cur_date,
                        "entry_price": entry_px,
                        "shares": shares,
                        "capital_deployed": deployed,
                        "highest_high": entry_px,
                        "entry_day_idx": day_i
                    }

        # 3. CALCULATE DAILY PORTFOLIO VALUE
        positions_val = 0.0
        for sym, pos in open_positions.items():
            if cur_date in date_to_idx[sym]:
                cur_close = float(stock_data[sym]["Close"].iloc[date_to_idx[sym][cur_date]])
                positions_val += pos["shares"] * cur_close
            else:
                positions_val += pos["capital_deployed"]

        total_portfolio_equity = round(cash + positions_val, 2)
        equity_curve.append({
            "date": cur_date,
            "equity": total_portfolio_equity,
            "cash": round(cash, 2),
            "invested": round(positions_val, 2),
            "open_positions": len(open_positions)
        })

    # Portfolio Performance Metrics
    total_trades = len(closed_trades)
    final_equity = equity_curve[-1]["equity"] if equity_curve else initial_capital
    net_profit = round(final_equity - initial_capital, 2)
    total_return_pct = round((net_profit / initial_capital) * 100, 2)

    # CAGR
    try:
        dt_start = pd.to_datetime(sorted_dates[0])
        dt_end = pd.to_datetime(sorted_dates[-1])
        years = max(0.1, (dt_end - dt_start).days / 365.25)
        cagr = round((((final_equity / initial_capital) ** (1.0 / years)) - 1.0) * 100, 2) if final_equity > 0 else -100.0
    except Exception:
        cagr = 0.0

    # Max Drawdown
    eq_series = [e["equity"] for e in equity_curve]
    peak = np.maximum.accumulate(eq_series)
    drawdowns = (peak - eq_series) / peak * 100
    max_dd = round(float(np.max(drawdowns)), 2) if len(drawdowns) > 0 else 0.0

    # Calmar Ratio
    calmar = round(cagr / max_dd, 2) if max_dd > 0 else cagr

    # Sharpe & Sortino (Daily returns)
    eq_df = pd.DataFrame(equity_curve)
    eq_df["daily_return"] = eq_df["equity"].pct_change().fillna(0.0)
    std_dev = float(eq_df["daily_return"].std()) * np.sqrt(252)
    risk_free_rate = 0.065  # 6.5% Indian 10Y G-Sec
    cagr_decimal = cagr / 100.0
    sharpe = round((cagr_decimal - risk_free_rate) / std_dev, 2) if std_dev > 0 else 0.0

    downside_returns = eq_df[eq_df["daily_return"] < 0]["daily_return"]
    downside_std = float(downside_returns.std()) * np.sqrt(252) if len(downside_returns) > 0 else std_dev
    sortino = round((cagr_decimal - risk_free_rate) / downside_std, 2) if downside_std > 0 else 0.0

    # Win Rate & Profit Factor
    winning = [t for t in closed_trades if t["net_pnl"] > 0]
    losing = [t for t in closed_trades if t["net_pnl"] <= 0]
    win_rate = round((len(winning) / total_trades * 100), 1) if total_trades > 0 else 0.0
    gross_win = sum(t["gross_pnl"] for t in winning)
    gross_loss = abs(sum(t["gross_pnl"] for t in losing))
    profit_factor = round(gross_win / gross_loss, 2) if gross_loss > 0 else (round(gross_win, 2) if gross_win > 0 else 1.0)

    # NIFTY 50 Benchmark comparison
    nifty_df = stock_data.get("NIFTY 50", stock_data.get("NIFTY_50", pd.DataFrame()))
    nifty_cagr = 0.0
    if not nifty_df.empty and len(nifty_df) >= 2:
        try:
            n_start = float(nifty_df["Close"].iloc[0])
            n_end = float(nifty_df["Close"].iloc[-1])
            nifty_cagr = round((((n_end / n_start) ** (1.0 / years)) - 1.0) * 100, 2)
        except Exception:
            pass

    return {
        "initial_capital": initial_capital,
        "final_equity": final_equity,
        "net_profit": net_profit,
        "total_return_pct": total_return_pct,
        "cagr_pct": cagr,
        "benchmark_nifty_cagr": nifty_cagr,
        "max_drawdown_pct": max_dd,
        "sharpe_ratio": sharpe,
        "sortino_ratio": sortino,
        "calmar_ratio": calmar,
        "total_trades": total_trades,
        "winning_trades": len(winning),
        "losing_trades": len(losing),
        "win_rate_pct": win_rate,
        "profit_factor": profit_factor,
        "closed_trades": closed_trades,
        "equity_curve": equity_curve,
        "open_positions": open_positions
    }
