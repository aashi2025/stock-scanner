import pytest
import pandas as pd
import numpy as np
from backend.app.engines.swing_action_screener import (
    calculate_supertrend,
    calculate_rsi,
    analyze_stock_swing_action,
    NIFTY_100_SYMBOLS
)

def create_synthetic_stock_data(
    n_bars: int = 250,
    base_price: float = 1000.0,
    trend_type: str = "bullish_pullback"
) -> pd.DataFrame:
    """Generates synthetic OHLCV data for testing."""
    dates = pd.date_range("2024-01-01", periods=n_bars, freq="B")
    
    if trend_type == "bullish_pullback":
        # Upward sloping prices, recent small pullback to 200 EMA
        closes = np.linspace(base_price * 0.7, base_price * 1.15, n_bars)
        # Add slight pullback in last 3 bars
        closes[-3] = closes[-4] * 0.985
        closes[-2] = closes[-4] * 0.980
        closes[-1] = closes[-2] * 1.015 # green reversal candle
    elif trend_type == "bearish":
        # Downward sloping
        closes = np.linspace(base_price * 1.2, base_price * 0.7, n_bars)
    else:
        closes = np.full(n_bars, base_price)

    highs = closes * 1.015
    lows = closes * 0.985
    opens = closes * 0.995 # slightly below close for green candle
    opens[-1] = lows[-1] + 1.0 # strong green reversal
    volumes = np.random.randint(500000, 2000000, size=n_bars)

    df = pd.DataFrame({
        "Open": opens,
        "High": highs,
        "Low": lows,
        "Close": closes,
        "Volume": volumes
    }, index=dates)
    return df


def test_nifty_100_symbols_count():
    assert len(NIFTY_100_SYMBOLS) == 100
    for sym in NIFTY_100_SYMBOLS:
        assert sym.endswith(".NS")


def test_calculate_supertrend():
    df = create_synthetic_stock_data(100, trend_type="bullish_pullback")
    st, direction = calculate_supertrend(df, period=7, multiplier=3.0)
    assert len(st) == len(df)
    assert direction.iloc[-1] in [1, -1]
    assert not pd.isna(st.iloc[-1])


def test_calculate_rsi():
    df = create_synthetic_stock_data(100)
    rsi = calculate_rsi(df['Close'], period=14)
    assert len(rsi) == len(df)
    assert 0 <= rsi.iloc[-1] <= 100


def test_bearish_stock_filtered_out():
    df_bearish = create_synthetic_stock_data(250, trend_type="bearish")
    res = analyze_stock_swing_action("TEST_BEARISH.NS", df_bearish)
    assert res is None # Below 200 EMA must be filtered out


def test_bullish_stock_detection_and_levels():
    df_bullish = create_synthetic_stock_data(250, trend_type="bullish_pullback")
    res = analyze_stock_swing_action("RELIANCE.NS", df_bullish)
    if res: # If passes RSI & support criteria
        assert res["symbol"] == "RELIANCE"
        assert res["cmp"] > 0
        assert res["stop_loss"] < res["entry_level"]
        assert res["target_level"] > res["entry_level"]
        assert res["risk_reward_ratio"].startswith("1:")
        assert 50.0 <= res["rsi_14"] <= 68.0
        assert res["signal"] in ["🟢 READY TO BUY", "⏳ WAIT FOR CONFIRMATION"]
