"""
Unit Tests verifying Scanner Behavior on Clearly Labeled Synthetic Datasets.
"""

import unittest
import os
import pandas as pd
from backend.app.engines.swing_scanner import analyze_swing_setup

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYNTHETIC_DIR = os.path.join(BASE_DIR, "data", "synthetic")


class TestSyntheticScan(unittest.TestCase):

    def test_synthetic_fresh_crossover_detection(self):
        csv_path = os.path.join(SYNTHETIC_DIR, "SYNTHETIC_FRESH_CROSSOVER.csv")
        self.assertTrue(os.path.exists(csv_path), "Synthetic fresh crossover file must exist")

        df = pd.read_csv(csv_path)
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.set_index("Date")

        stock_info = {"symbol": "SYNTH_FRESH", "name": "Synthetic Fresh Crossover", "sector": "IT"}
        sec_map = {"IT": 75.0, "GENERAL": 60.0}

        res = analyze_swing_setup(stock_info, df, df, sec_map, market_score=70.0, data_source="Synthetic Test Data")

        self.assertTrue(res["rsi_fresh_crossover"], "Expected fresh RSI crossover to be True")
        self.assertGreaterEqual(res["swing_score"], 65.0)
        self.assertTrue(any("Fresh RSI" in r for r in res["reasons"]))

    def test_synthetic_stale_trend_detection(self):
        csv_path = os.path.join(SYNTHETIC_DIR, "SYNTHETIC_STALE_TREND.csv")
        self.assertTrue(os.path.exists(csv_path), "Synthetic stale trend file must exist")

        df = pd.read_csv(csv_path)
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.set_index("Date")

        stock_info = {"symbol": "SYNTH_STALE", "name": "Synthetic Stale Trend", "sector": "Auto"}
        sec_map = {"AUTO": 65.0, "GENERAL": 60.0}

        res = analyze_swing_setup(stock_info, df, df, sec_map, market_score=65.0, data_source="Synthetic Test Data")

        # Stale crossover must NOT be reported as fresh
        self.assertFalse(res["rsi_fresh_crossover"], "Stale trend must not trigger fresh crossover")
        self.assertTrue(res["rsi_value"] > 50.0)

    def test_synthetic_bearish_downtrend(self):
        csv_path = os.path.join(SYNTHETIC_DIR, "SYNTHETIC_BEARISH_DOWNTREND.csv")
        self.assertTrue(os.path.exists(csv_path), "Synthetic bearish downtrend file must exist")

        df = pd.read_csv(csv_path)
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.set_index("Date")

        stock_info = {"symbol": "SYNTH_BEAR", "name": "Synthetic Downtrend", "sector": "Metal"}
        sec_map = {"METAL": 40.0, "GENERAL": 60.0}

        res = analyze_swing_setup(stock_info, df, df, sec_map, market_score=40.0, data_source="Synthetic Test Data")

        self.assertFalse(res["rsi_fresh_crossover"])
        self.assertEqual(res["classification"], "AVOID / NOT CONFIRMED")
        self.assertLess(res["swing_score"], 50.0)


if __name__ == "__main__":
    unittest.main()
