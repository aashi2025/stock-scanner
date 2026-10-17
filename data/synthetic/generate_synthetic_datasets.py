"""
Generates clearly labeled synthetic test datasets for unit tests and offline verification.
DISCLAIMER: ALL FILES IN THIS DIRECTORY ARE SYNTHETIC MATHEMATICAL ARTIFACTS
AND MUST NEVER BE CONFUSED WITH REAL LIVE MARKET DATA.
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

SYNTHETIC_DIR = os.path.dirname(os.path.abspath(__file__))

def create_synthetic_fresh_crossover():
    """Generates a dataset where the latest completed candle has a fresh RSI crossover above 50."""
    base_date = datetime(2026, 10, 15)

    base = 400.0
    prices = [base]
    for i in range(1, 200):
        prices.append(prices[-1] + 0.6)  # strong uptrend ensures EMA50 > EMA200
    for i in range(14):
        if i % 2 == 0:
            prices.append(prices[-1] - 1.2)
        else:
            prices.append(prices[-1] + 0.8)
    prices.append(prices[-1] + 4.5)  # latest completed bar crossing above 50

    n = len(prices)
    dates = [base_date - timedelta(days=n - i) for i in range(n)]

    close_arr = np.array(prices)
    high_arr = close_arr * 1.015
    low_arr = close_arr * 0.985
    open_arr = low_arr + (high_arr - low_arr) * 0.4

    # High volume surge on latest day
    np.random.seed(42)
    volumes = [int(np.random.uniform(800000, 1200000)) for _ in range(n - 1)]
    volumes.append(int(volumes[-1] * 2.2))  # 2.2x volume surge

    df = pd.DataFrame({
        "Date": [d.strftime("%Y-%m-%d") for d in dates],
        "Open": np.round(open_arr, 2),
        "High": np.round(high_arr, 2),
        "Low": np.round(low_arr, 2),
        "Close": np.round(close_arr, 2),
        "Volume": volumes
    })

    out_file = os.path.join(SYNTHETIC_DIR, "SYNTHETIC_FRESH_CROSSOVER.csv")
    df.to_csv(out_file, index=False)
    print(f"Created: {out_file}")


def create_synthetic_stale_trend():
    """Generates a dataset where RSI has stayed > 50 for many sessions (continuation, not fresh)."""
    np.random.seed(101)
    n = 220
    base_date = datetime(2026, 10, 15)
    dates = [base_date - timedelta(days=n - i) for i in range(n)]

    prices = [1000.0]
    for i in range(1, n):
        # Persistent steady upward drift keeps RSI continuously between 58 and 68
        prices.append(prices[-1] * (1.0 + np.random.normal(0.003, 0.005)))

    close_arr = np.array(prices)
    high_arr = close_arr * 1.01
    low_arr = close_arr * 0.99
    open_arr = low_arr + (high_arr - low_arr) * 0.5
    volumes = [int(np.random.uniform(500000, 1500000)) for _ in range(n)]

    df = pd.DataFrame({
        "Date": [d.strftime("%Y-%m-%d") for d in dates],
        "Open": np.round(open_arr, 2),
        "High": np.round(high_arr, 2),
        "Low": np.round(low_arr, 2),
        "Close": np.round(close_arr, 2),
        "Volume": volumes
    })

    out_file = os.path.join(SYNTHETIC_DIR, "SYNTHETIC_STALE_TREND.csv")
    df.to_csv(out_file, index=False)
    print(f"Created: {out_file}")


def create_synthetic_downtrend():
    """Generates a bearish stock where Price < 50 EMA < 200 EMA and RSI < 40."""
    np.random.seed(202)
    n = 220
    base_date = datetime(2026, 10, 15)
    dates = [base_date - timedelta(days=n - i) for i in range(n)]

    prices = [1500.0]
    for i in range(1, n):
        prices.append(prices[-1] * (1.0 + np.random.normal(-0.002, 0.008)))

    close_arr = np.array(prices)
    high_arr = close_arr * 1.012
    low_arr = close_arr * 0.988
    open_arr = low_arr + (high_arr - low_arr) * 0.5
    volumes = [int(np.random.uniform(200000, 800000)) for _ in range(n)]

    df = pd.DataFrame({
        "Date": [d.strftime("%Y-%m-%d") for d in dates],
        "Open": np.round(open_arr, 2),
        "High": np.round(high_arr, 2),
        "Low": np.round(low_arr, 2),
        "Close": np.round(close_arr, 2),
        "Volume": volumes
    })

    out_file = os.path.join(SYNTHETIC_DIR, "SYNTHETIC_BEARISH_DOWNTREND.csv")
    df.to_csv(out_file, index=False)
    print(f"Created: {out_file}")


def create_synthetic_invalid_data():
    """Generates corrupted data with invalid schema, High < Low, negative prices, and nulls."""
    df = pd.DataFrame({
        "Date": ["2026-10-01", "2026-10-02", "2026-10-03", "invalid-date", "2026-10-05"],
        "Open": [100.0, 105.0, None, 110.0, -50.0],  # Negative price & Null
        "High": [90.0, 115.0, 112.0, 115.0, 120.0],  # Row 0: High (90) < Open (100)
        "Low": [95.0, 102.0, 98.0, 105.0, 100.0],   # Row 0: Low (95) > High (90)
        "Close": [92.0, 110.0, 108.0, 112.0, 115.0],
        "Volume": [1000, 2000, None, 1500, -500]     # Negative volume & Null
    })
    out_file = os.path.join(SYNTHETIC_DIR, "SYNTHETIC_INVALID_DATA.csv")
    df.to_csv(out_file, index=False)
    print(f"Created: {out_file}")


if __name__ == "__main__":
    create_synthetic_fresh_crossover()
    create_synthetic_stale_trend()
    create_synthetic_downtrend()
    create_synthetic_invalid_data()
    print("All synthetic test datasets successfully generated.")
