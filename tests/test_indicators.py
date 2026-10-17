"""
Unit Tests for Technical Indicators and Crossover Detection.
"""

import unittest
import pandas as pd
import numpy as np

from backend.app.indicators.calculations import (
    calculate_sma,
    calculate_ema,
    calculate_rsi,
    calculate_atr,
    calculate_52w_metrics,
    detect_rsi_fresh_crossover
)


class TestIndicators(unittest.TestCase):

    def setUp(self):
        # Create deterministic price series
        np.random.seed(42)
        self.prices = pd.Series([
            100.0, 102.0, 101.0, 103.0, 105.0, 104.0, 106.0, 108.0, 107.0, 109.0,
            111.0, 110.0, 112.0, 114.0, 113.0, 115.0, 117.0, 116.0, 118.0, 120.0
        ])

    def test_sma_calculation(self):
        sma5 = calculate_sma(self.prices, 5)
        self.assertEqual(len(sma5), len(self.prices))
        # Expected last 5 avg: (115 + 117 + 116 + 118 + 120) / 5 = 117.2
        self.assertAlmostEqual(sma5.iloc[-1], 117.2, places=1)

    def test_ema_calculation(self):
        ema5 = calculate_ema(self.prices, 5)
        self.assertEqual(len(ema5), len(self.prices))
        self.assertTrue(ema5.iloc[-1] > ema5.iloc[0])

    def test_rsi_bounds(self):
        rsi = calculate_rsi(self.prices, 14)
        self.assertTrue((rsi >= 0.0).all())
        self.assertTrue((rsi <= 100.0).all())

    def test_detect_rsi_fresh_crossover(self):
        # Case 1: Fresh crossover (T-1 <= 50, T > 50)
        rsi_series_fresh = pd.Series([45.0, 48.0, 49.5, 52.3])
        res_fresh = detect_rsi_fresh_crossover(rsi_series_fresh, 50.0)
        self.assertTrue(res_fresh["fresh_crossover"])
        self.assertEqual(res_fresh["curr_rsi"], 52.3)
        self.assertEqual(res_fresh["prev_rsi"], 49.5)

        # Case 2: Stale continuation (T-1 > 50, T > 50)
        rsi_series_stale = pd.Series([45.0, 52.0, 55.0, 58.0])
        res_stale = detect_rsi_fresh_crossover(rsi_series_stale, 50.0)
        self.assertFalse(res_stale["fresh_crossover"])
        self.assertTrue(res_stale["is_above_50"])
        self.assertIn("Bullish Continuation", res_stale["status"])

        # Case 3: Bearish continuation (T-1 < 50, T < 50)
        rsi_series_bearish = pd.Series([48.0, 47.0, 45.0, 42.0])
        res_bear = detect_rsi_fresh_crossover(rsi_series_bearish, 50.0)
        self.assertFalse(res_bear["fresh_crossover"])
        self.assertFalse(res_bear["is_above_50"])

    def test_calculate_52w_metrics(self):
        df = pd.DataFrame({
            "Close": [100.0, 110.0, 120.0, 115.0, 108.0],
            "High": [105.0, 115.0, 125.0, 118.0, 112.0],
            "Low": [98.0, 104.0, 114.0, 110.0, 106.0]
        })
        high_52w, low_52w, dist_pct = calculate_52w_metrics(df)
        self.assertEqual(high_52w, 125.0)
        self.assertEqual(low_52w, 98.0)
        # Distance from 125 with close at 108 = (125 - 108) / 125 * 100 = 13.6%
        self.assertAlmostEqual(dist_pct, 13.6, places=1)


if __name__ == "__main__":
    unittest.main()
