"""
Unit Tests for Multi-Timeframe (MTF) Weekly Resampling & Confirmation.
"""

import unittest
import pandas as pd
import numpy as np

from backend.app.engines.multi_timeframe import resample_daily_to_weekly, analyze_multi_timeframe_context


class TestMultiTimeframe(unittest.TestCase):

    def setUp(self):
        # 120 days of daily data
        dates = pd.date_range("2026-01-01", periods=120, freq="B")
        prices = [500.0 + (i * 0.5) for i in range(120)]
        self.daily_df = pd.DataFrame({
            "Open": [p - 1.0 for p in prices],
            "High": [p + 3.0 for p in prices],
            "Low": [p - 3.0 for p in prices],
            "Close": prices,
            "Volume": [100000] * 120
        }, index=dates)

    def test_weekly_resampling_aggregation(self):
        weekly = resample_daily_to_weekly(self.daily_df)
        self.assertFalse(weekly.empty)
        # Should have approx 24 weeks
        self.assertGreaterEqual(len(weekly), 20)
        # Check weekly high is >= weekly close
        self.assertTrue((weekly["High"] >= weekly["Close"]).all())
        self.assertTrue((weekly["Low"] <= weekly["Close"]).all())

    def test_multi_timeframe_bullish_context(self):
        res = analyze_multi_timeframe_context(self.daily_df)
        self.assertTrue(res["is_available"])
        self.assertTrue(res["weekly_trend_bullish"])
        self.assertIn("High-Conviction", res["mtf_status"])
        self.assertGreaterEqual(res["weekly_score"], 80.0)


if __name__ == "__main__":
    unittest.main()
