"""
Unit Tests for Data Validator and Integrity Checks.
"""

import unittest
import os
import pandas as pd
from backend.app.data_providers.data_validator import validate_ohlcv_dataframe

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYNTHETIC_DIR = os.path.join(BASE_DIR, "data", "synthetic")

class TestDataValidation(unittest.TestCase):

    def test_valid_dataframe(self):
        df = pd.DataFrame({
            "Date": pd.date_range("2026-01-01", periods=30, freq="D"),
            "Open": [100 + i for i in range(30)],
            "High": [105 + i for i in range(30)],
            "Low": [95 + i for i in range(30)],
            "Close": [102 + i for i in range(30)],
            "Volume": [10000 + i * 100 for i in range(30)]
        })
        is_valid, clean_df, report = validate_ohlcv_dataframe(df, symbol="TEST")
        self.assertTrue(is_valid)
        self.assertEqual(report["total_records"], 30)
        self.assertEqual(len(clean_df), 30)

    def test_missing_required_columns(self):
        # Missing 'Volume'
        bad_df = pd.DataFrame({
            "Date": ["2026-01-01", "2026-01-02"],
            "Open": [100, 102],
            "High": [105, 106],
            "Low": [98, 99],
            "Close": [102, 104]
        })
        is_valid, clean_df, report = validate_ohlcv_dataframe(bad_df, symbol="TEST_BAD")
        self.assertFalse(is_valid)
        self.assertEqual(report["status"], "INVALID_SCHEMA")
        self.assertTrue(any("Missing required columns" in err for err in report["errors"]))

    def test_duplicate_date_removal(self):
        df = pd.DataFrame({
            "Date": ["2026-01-01", "2026-01-01", "2026-01-02"],
            "Open": [100, 101, 102],
            "High": [105, 106, 107],
            "Low": [95, 96, 97],
            "Close": [102, 103, 104],
            "Volume": [1000, 1100, 1200]
        })
        is_valid, clean_df, report = validate_ohlcv_dataframe(df, symbol="DUP_TEST")
        self.assertTrue(is_valid)
        self.assertEqual(len(clean_df), 2)
        self.assertTrue(any("duplicate date" in w.lower() for w in report["warnings"]))

    def test_corrupted_synthetic_data_rejection(self):
        invalid_csv_path = os.path.join(SYNTHETIC_DIR, "SYNTHETIC_INVALID_DATA.csv")
        if os.path.exists(invalid_csv_path):
            raw_df = pd.read_csv(invalid_csv_path)
            is_valid, clean_df, report = validate_ohlcv_dataframe(raw_df, symbol="INVALID_TEST")
            # Should either be marked invalid or reject corrupted integrity rows
            self.assertTrue(len(report["errors"]) > 0 or not is_valid)


if __name__ == "__main__":
    unittest.main()
