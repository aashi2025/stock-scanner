"""
Unit Tests for Delivery & Institutional Accumulation Tracker.
"""

import unittest
import pandas as pd
import numpy as np

from backend.app.engines.delivery_tracker import compute_obv, analyze_accumulation_distribution


class TestDeliveryTracker(unittest.TestCase):

    def test_obv_calculation(self):
        df = pd.DataFrame({
            "Close": [100.0, 105.0, 102.0, 108.0],
            "Volume": [1000, 2000, 1500, 3000]
        })
        obv = compute_obv(df)
        self.assertEqual(len(obv), len(df))
        # Day 1 (+5): +2000, Day 2 (-3): -1500 => 500, Day 3 (+6): +3000 => 3500
        self.assertEqual(obv.iloc[-1], 3500)

    def test_accumulation_distribution_detection(self):
        # 30 days of data with strong closing at the highs and rising volume
        dates = pd.date_range("2026-01-01", periods=30, freq="B")
        df = pd.DataFrame({
            "Open": [100 + i for i in range(30)],
            "Low": [99 + i for i in range(30)],
            "High": [105 + i for i in range(30)],
            "Close": [104.5 + i for i in range(30)], # Closes right near High (CLV high)
            "Volume": [10000 + (i * 500) for i in range(30)] # Expanding volume
        }, index=dates)

        res = analyze_accumulation_distribution(df)
        self.assertGreaterEqual(res["accumulation_score"], 65.0)
        self.assertTrue(res["close_location_value"] >= 0.6)
        self.assertIn("Smart Money Accumulation", res["status"])


if __name__ == "__main__":
    unittest.main()
