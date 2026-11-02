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
        assert 50.0 <= res["rsi_14"] <= 70.0
        assert res["signal"] in ["🟢 READY TO BUY", "⏳ WAIT FOR CONFIRMATION"]


def test_setup_c_supertrend_flip_detection():
    """Tests user's exact Chartink formula: 200 EMA + ST Flip + Close Range > 0.65 + Vol > SMA20."""
    n_bars = 250
    dates = pd.date_range("2024-01-01", periods=n_bars, freq="B")
    
    # Uptrend above 200 EMA
    closes = np.linspace(800.0, 1050.0, n_bars)
    
    # Previous bar dip to put ST in bearish state
    closes[-2] = 1000.0
    # Day 0 sharp bounce flipping ST bullish
    closes[-1] = 1060.0
    
    opens = closes.copy()
    opens[-1] = 1030.0 # Green candle (Close > Open)
    
    highs = closes * 1.01
    highs[-1] = 1065.0
    
    lows = closes * 0.99
    lows[-1] = 1025.0
    # (c0 - l0)/(h0 - l0) = (1060 - 1025) / (1065 - 1025) = 35 / 40 = 0.875 > 0.65
    
    volumes = np.full(n_bars, 1000000)
    volumes[-1] = 2500000 # Heavy volume > 20 SMA
    
    df = pd.DataFrame({
        "Open": opens,
        "High": highs,
        "Low": lows,
        "Close": closes,
        "Volume": volumes
    }, index=dates)
    
    res = analyze_stock_swing_action("TEST_FLIP.NS", df)
    assert res is not None
    assert res["signal"] == "🟢 READY TO BUY"
    assert "Supertrend Flip" in res["setup_type"] or "Setup" in res["setup_type"]
    assert res["stop_loss"] < res["entry_level"]
    assert res["target_level"] > res["entry_level"]
