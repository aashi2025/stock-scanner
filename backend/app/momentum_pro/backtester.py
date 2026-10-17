"""
Momentum Pro — Realistic Historical Strategy Backtesting Engine.
Zero look-ahead bias: Signal generated at Day T Close -> Execution at Day T+1 Open.
Includes slippage, Indian equity delivery statutory taxes & charges.
Produces: Trade count, Win rate, Expectancy, Profit Factor, Max Drawdown, Equity Curve.
"""

from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from datetime import datetime

from backend.app.data_providers.base import MarketDataProvider
from backend.app.engines.backtest import calculate_indian_statutory_charges
from backend.app.indicators.calculations import (
    calculate_ema,
    calculate_rsi,
    calculate_atr,
    calculate_resistance_and_swing_high
)

def run_momentum_pro_backtest(
    provider: MarketDataProvider,
    symbol: str = "RELIANCE",
    initial_capital: float = 100000.0,
    risk_per_trade_pct: float = 1.0,
    target_multiplier: float = 2.0,
    max_holding_bars: int = 15,
    slippage_pct: float = 0.10,
    strategy_mode: str = "Breakout & RSI Cross" # "Breakout & RSI Cross" | "Breakout Only" | "RSI Cross Only"
) -> Dict[str, Any]:
    """
    Executes a walk-forward, next-day execution backtest on historical OHLCV data.
    """
    df = provider.get_historical_data(symbol, period="2y", interval="1d")
    if df.empty or len(df) < 50:
        return {
            "status": "error",
            "message": f"Insufficient historical data for {symbol} (Requires >= 50 completed daily bars).",
            "total_trades": 0,
            "win_rate_pct": 0.0,
            "profit_factor": 0.0,
            "expectancy": 0.0,
            "max_drawdown_pct": 0.0,
            "equity_curve": [],
            "trades": []
        }

    close = df['Close']
    open_p = df['Open']
    high = df['High']
    low = df['Low']
    vol = df['Volume'] if 'Volume' in df.columns else pd.Series(1000, index=df.index)

    # Calculate indicators
    rsi_series = calculate_rsi(close, 14)
    atr_series = calculate_atr(df, 14)
    vol_sma20 = vol.rolling(window=20).mean()

    # Track equity and trades
    capital = initial_capital
    peak_capital = initial_capital
    max_drawdown = 0.0

    trades: List[Dict[str, Any]] = []
    equity_curve: List[Dict[str, Any]] = []

    in_position = False
    entry_price = 0.0
    stop_loss = 0.0
    target_price = 0.0
    position_shares = 0
    entry_bar_idx = 0
    entry_date = ""

    # Add initial equity point
    first_date = str(df.index[0])[:10]
    equity_curve.append({"date": first_date, "equity": capital})

    for i in range(25, len(df) - 1):
        curr_date = str(df.index[i])[:10]
        next_open = float(open_p.iloc[i + 1])
        next_high = float(high.iloc[i + 1])
        next_low = float(low.iloc[i + 1])
        next_date = str(df.index[i + 1])[:10]

        # -------------------------------------------------------------
        # 1. Manage Active Position
        # -------------------------------------------------------------
        if in_position:
            bars_held = i - entry_bar_idx
            exit_price = None
            exit_reason = None

            # Check Stop Loss hit on next candle
            if next_low <= stop_loss:
                # Execution at SL or Next Open (if gapped below SL)
                exit_price = min(next_open, stop_loss) * (1.0 - (slippage_pct / 100.0))
                exit_reason = "Stop Loss"
            # Check Target hit on next candle
            elif next_high >= target_price:
                exit_price = max(next_open, target_price) * (1.0 - (slippage_pct / 100.0))
                exit_reason = f"Target ({target_multiplier}R)"
            # Check Time-based Exit
            elif bars_held >= max_holding_bars:
                exit_price = next_open * (1.0 - (slippage_pct / 100.0))
                exit_reason = f"Time Exit ({max_holding_bars} Bars)"

            if exit_price is not None:
                buy_val = position_shares * entry_price
                sell_val = position_shares * exit_price
                charges = calculate_indian_statutory_charges(buy_val, sell_val)
                total_costs = charges["total_charges"]

                gross_pnl = sell_val - buy_val
                net_pnl = round(gross_pnl - total_costs, 2)
                ret_pct = round((net_pnl / buy_val * 100), 2) if buy_val > 0 else 0.0

                capital += net_pnl
                peak_capital = max(peak_capital, capital)
                dd = (peak_capital - capital) / peak_capital * 100.0
                max_drawdown = max(max_drawdown, dd)

                trades.append({
                    "symbol": symbol,
                    "entry_date": entry_date,
                    "exit_date": next_date,
                    "entry_price": round(entry_price, 2),
                    "exit_price": round(exit_price, 2),
                    "shares": position_shares,
                    "exit_reason": exit_reason,
                    "gross_pnl": round(gross_pnl, 2),
                    "statutory_costs": total_costs,
                    "net_pnl": net_pnl,
                    "return_pct": ret_pct,
                    "bars_held": bars_held
                })

                equity_curve.append({"date": next_date, "equity": round(capital, 2)})
                in_position = False
                continue

        # -------------------------------------------------------------
        # 2. Check Signals on Completed Candle [i]
        # -------------------------------------------------------------
        if not in_position and i < len(df) - 1:
            c_price = float(close.iloc[i])
            c_rsi = float(rsi_series.iloc[i])
            p_rsi = float(rsi_series.iloc[i - 1])
            c_atr = float(atr_series.iloc[i])
            c_vol = float(vol.iloc[i])
            c_avg_vol = float(vol_sma20.iloc[i]) if not pd.isna(vol_sma20.iloc[i]) else c_vol
            rvol = (c_vol / c_avg_vol) if c_avg_vol > 0 else 1.0

            # 20-day swing high resistance (prior 20 bars excluding current)
            prior_slice = high.iloc[max(0, i-20):i]
            res_20 = float(prior_slice.max()) if not prior_slice.empty else c_price
            prior_low_slice = low.iloc[max(0, i-20):i]
            sw_low = float(prior_low_slice.min()) if not prior_low_slice.empty else (c_price * 0.95)

            is_rsi_cross = bool(p_rsi <= 50.0 and c_rsi > 50.0)
            is_breakout = bool(c_price >= res_20 and rvol >= 1.15)

            trigger = False
            if strategy_mode == "Breakout & RSI Cross":
                trigger = is_breakout or (is_rsi_cross and rvol >= 1.0)
            elif strategy_mode == "Breakout Only":
                trigger = is_breakout
            elif strategy_mode == "RSI Cross Only":
                trigger = is_rsi_cross

            if trigger:
                # Enter on next bar Open with slippage applied
                entry_price = next_open * (1.0 + (slippage_pct / 100.0))
                atr_val = c_atr if c_atr > 0 else (entry_price * 0.02)
                
                # Stop loss based on structural swing low or ATR
                raw_sl = max(sw_low, entry_price - (1.5 * atr_val))
                if raw_sl >= (entry_price * 0.985):
                    stop_loss = round(entry_price * 0.975, 2)
                elif raw_sl < (entry_price * 0.90):
                    stop_loss = round(entry_price * 0.92, 2)
                else:
                    stop_loss = round(raw_sl, 2)

                risk_per_share = entry_price - stop_loss
                target_price = round(entry_price + (risk_per_share * target_multiplier), 2)

                # Position Sizing
                risk_amt = capital * (risk_per_trade_pct / 100.0)
                shares = int(risk_amt // risk_per_share) if risk_per_share > 0 else 0
                if (shares * entry_price) > capital:
                    shares = int(capital // entry_price)

                if shares > 0:
                    position_shares = shares
                    entry_bar_idx = i + 1
                    entry_date = next_date
                    in_position = True

    # Final summary statistics
    total_trades = len(trades)
    winning_trades = [t for t in trades if t["net_pnl"] > 0]
    losing_trades = [t for t in trades if t["net_pnl"] <= 0]
    win_rate = round((len(winning_trades) / total_trades * 100.0), 2) if total_trades > 0 else 0.0

    gross_wins = sum(t["net_pnl"] for t in winning_trades)
    gross_losses = abs(sum(t["net_pnl"] for t in losing_trades))
    profit_factor = round(gross_wins / gross_losses, 2) if gross_losses > 0 else (round(gross_wins, 2) if gross_wins > 0 else 0.0)

    avg_win = (gross_wins / len(winning_trades)) if winning_trades else 0.0
    avg_loss = (gross_losses / len(losing_trades)) if losing_trades else 0.0
    expectancy = round(((win_rate / 100.0) * avg_win) - (((100.0 - win_rate) / 100.0) * avg_loss), 2)

    total_net_pnl = round(capital - initial_capital, 2)
    total_return_pct = round((total_net_pnl / initial_capital) * 100.0, 2)

    return {
        "status": "success",
        "symbol": symbol,
        "strategy_mode": strategy_mode,
        "initial_capital": initial_capital,
        "ending_capital": round(capital, 2),
        "total_net_pnl": total_net_pnl,
        "total_return_pct": total_return_pct,
        "total_trades": total_trades,
        "winning_trades": len(winning_trades),
        "losing_trades": len(losing_trades),
        "win_rate_pct": win_rate,
        "profit_factor": profit_factor,
        "expectancy": expectancy,
        "max_drawdown_pct": round(max_drawdown, 2),
        "equity_curve": equity_curve,
        "trades": trades[:50] # Return last 50 trades
    }
