"""
Interactive Plotly Financial Charting Module.
Renders professional Candlestick charts, 50/200 EMAs, Volume, RSI subplots,
and trade reference levels for Streamlit.
"""

from typing import Dict, Any, Optional
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from backend.app.indicators.calculations import calculate_ema, calculate_rsi


def create_candlestick_chart(
    df: pd.DataFrame,
    symbol: str = "STOCK",
    lookback_bars: int = 120,
    reference_levels: Optional[Dict[str, Any]] = None
) -> go.Figure:
    """
    Creates an interactive 2-panel Plotly Candlestick + RSI chart.
    """
    plot_df = df.tail(lookback_bars).copy()
    
    # Calculate indicators
    plot_df["EMA_50"] = calculate_ema(plot_df["Close"], 50)
    plot_df["EMA_200"] = calculate_ema(plot_df["Close"], 200)
    plot_df["RSI_14"] = calculate_rsi(plot_df["Close"], 14)

    dates = [d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d) for d in plot_df.index]

    # Subplots: Row 1 = Price + EMAs, Row 2 = RSI
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.06,
        row_heights=[0.72, 0.28],
        subplot_titles=(f"{symbol.upper()} Daily Price Action & EMAs", "RSI(14) Momentum")
    )

    # 1. Candlestick
    fig.add_trace(
        go.Candlestick(
            x=dates,
            open=plot_df["Open"],
            high=plot_df["High"],
            low=plot_df["Low"],
            close=plot_df["Close"],
            name="OHLC",
            increasing_line_color="#10B981", # Emerald Green
            decreasing_line_color="#EF4444"  # Rose Red
        ),
        row=1, col=1
    )

    # 2. EMAs
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=plot_df["EMA_50"],
            name="50 EMA",
            line=dict(color="#3B82F6", width=1.8) # Blue
        ),
        row=1, col=1
    )

    fig.add_trace(
        go.Scatter(
            x=dates,
            y=plot_df["EMA_200"],
            name="200 EMA",
            line=dict(color="#F59E0B", width=2.0, dash="dot") # Amber
        ),
        row=1, col=1
    )

    # Reference Levels (Entry, SL, Target)
    if reference_levels:
        entry_px = reference_levels.get("entry_reference")
        stop_px = reference_levels.get("stop_loss_reference")
        t1_px = reference_levels.get("target_1_reference")

        if entry_px:
            fig.add_hline(y=entry_px, line_dash="dash", line_color="#3B82F6", annotation_text=f"Ref Entry: ₹{entry_px}", row=1, col=1)
        if stop_px:
            fig.add_hline(y=stop_px, line_dash="dash", line_color="#EF4444", annotation_text=f"Stop Loss: ₹{stop_px}", row=1, col=1)
        if t1_px:
            fig.add_hline(y=t1_px, line_dash="dash", line_color="#10B981", annotation_text=f"Target 1: ₹{t1_px}", row=1, col=1)

    # 3. RSI Subplot
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=plot_df["RSI_14"],
            name="RSI(14)",
            line=dict(color="#8B5CF6", width=1.5) # Purple
        ),
        row=2, col=1
    )

    # RSI Threshold Lines
    fig.add_hline(y=50, line_dash="dash", line_color="#64748B", line_width=1, row=2, col=1)
    fig.add_hline(y=70, line_dash="dot", line_color="#EF4444", line_width=1, row=2, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color="#10B981", line_width=1, row=2, col=1)

    fig.update_layout(
        height=520,
        margin=dict(l=10, r=10, t=35, b=10),
        xaxis_rangeslider_visible=False,
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    fig.update_yaxes(title_text="Price (₹)", row=1, col=1)
    fig.update_yaxes(title_text="RSI", range=[10, 90], row=2, col=1)

    return fig


def create_portfolio_equity_chart(equity_curve: list, initial_capital: float) -> go.Figure:
    """Creates portfolio equity and cash curve chart."""
    dates = [e["date"] for e in equity_curve]
    equities = [e["equity"] for e in equity_curve]
    cashes = [e["cash"] for e in equity_curve]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates, y=equities,
        mode="lines", name="Total Portfolio Equity",
        line=dict(color="#10B981", width=2.5),
        fill="tozeroy", fillcolor="rgba(16, 185, 129, 0.08)"
    ))

    fig.add_trace(go.Scatter(
        x=dates, y=cashes,
        mode="lines", name="Idle Cash Reserves",
        line=dict(color="#94A3B8", width=1.2, dash="dash")
    ))

    fig.add_hline(y=initial_capital, line_dash="dot", line_color="#64748B", annotation_text="Starting Capital")

    fig.update_layout(
        title="Portfolio Capital Growth & Cash Reserves",
        height=380,
        margin=dict(l=10, r=10, t=35, b=10),
        template="plotly_white",
        xaxis_title="Date",
        yaxis_title="Portfolio Value (₹)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    return fig
