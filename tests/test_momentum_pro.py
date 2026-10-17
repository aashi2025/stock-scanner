"""
Unit Tests for Momentum Pro Engine.
Tests indicators, setup scoring, trade planner, multi-stage scanner, and backtesting.
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from backend.app.momentum_pro.indicators import (
    calculate_resistance_and_swing_high,
    compute_momentum_pro_indicators
)
from backend.app.momentum_pro.scoring import calculate_momentum_setup_score
from backend.app.momentum_pro.trade_planner import calculate_trade_plan
from backend.app.momentum_pro.scanner import run_momentum_pro_scan
from backend.app.momentum_pro.backtester import run_momentum_pro_backtest
from backend.app.data_providers.sample import SampleDataProvider


class TestMomentumPro(unittest.TestCase):

    def setUp(self):
        # Create deterministic price series with clear breakout
        np.random.seed(42)
        n = 60
        dates = pd.date_range(end=datetime.now(), periods=n, freq="B")
        
        # Consolidation between 100 and 105 for first 50 bars, then breakout to 110
        prices = [100.0 + (i % 5) for i in range(50)] + [106.0, 107.5, 109.0, 110.5, 112.0, 111.0, 113.0, 115.0, 114.0, 116.0]
        highs = [p + 1.0 for p in prices]
        lows = [p - 1.0 for p in prices]
        vols = [100000] * 50 + [250000] * 10 # Volume surge on breakout
        
        self.df = pd.DataFrame({
            "Open": prices,
            "High": highs,
            "Low": lows,
            "Close": prices,
            "Volume": vols
        }, index=dates)

        self.nifty_df = pd.DataFrame({
            "Open": [20000 + i * 10 for i in range(n)],
            "High": [20050 + i * 10 for i in range(n)],
            "Low": [19950 + i * 10 for i in range(n)],
            "Close": [20000 + i * 10 for i in range(n)],
            "Volume": [500000] * n
        }, index=dates)

    def test_resistance_and_swing_high(self):
        res, sw_low, dist_pct = calculate_resistance_and_swing_high(self.df, lookback=20)
        self.assertTrue(res > 0)
        self.assertTrue(sw_low > 0)
        self.assertTrue(sw_low < res)

    def test_momentum_pro_indicators(self):
        ind = compute_momentum_pro_indicators(self.df, self.nifty_df)
        self.assertIn("ema_9", ind)
        self.assertIn("ema_20", ind)
        self.assertIn("resistance_20d", ind)
        self.assertIn("swing_low_20d", ind)
        self.assertIn("rvol", ind)
        self.assertIn("rs_vs_nifty_20d", ind)
        self.assertIn("momentum_setup_type", ind)
        self.assertTrue(ind["ema_9"] > 0)
        self.assertTrue(ind["ema_20"] > 0)
        self.assertTrue(ind["rvol"] > 0)

    def test_setup_score(self):
        ind = compute_momentum_pro_indicators(self.df, self.nifty_df)
        score_data = calculate_momentum_setup_score(ind)
        self.assertIn("setup_score", score_data)
        self.assertIn("breakdown", score_data)
        self.assertTrue(0.0 <= score_data["setup_score"] <= 100.0)
        self.assertEqual(len(score_data["breakdown"]), 5) # 5 categories

    def test_trade_planner(self):
        plan = calculate_trade_plan(
            symbol="TESTSTOCK",
            price=100.0,
            atr_14=2.0,
            swing_low=95.0,
            resistance=100.0,
            account_capital=100000.0,
            risk_per_trade_pct=1.0
        )
        self.assertEqual(plan["symbol"], "TESTSTOCK")
        self.assertEqual(plan["entry_reference"], 100.0)
        self.assertTrue(plan["stop_loss"] < plan["entry_reference"])
        self.assertTrue(plan["target_1"] > plan["entry_reference"])
        self.assertTrue(plan["target_2"] > plan["target_1"])
        self.assertTrue(plan["target_3"] > plan["target_2"])
        self.assertTrue(plan["position_shares"] > 0)
        self.assertTrue(plan["total_investment"] <= 100000.0)
        self.assertIn("disclaimer", plan)

    def test_scanner_with_sample_provider(self):
        provider = SampleDataProvider()
        scan = run_momentum_pro_scan(provider)
        self.assertIn("confirmed_breakouts", scan)
        self.assertIn("fresh_rsi_crossovers", scan)
        self.assertIn("pre_breakout_watchlist", scan)
        self.assertIn("all_candidates", scan)
        self.assertGreater(scan["total_scanned"], 0)

    def test_backtester_with_sample_provider(self):
        provider = SampleDataProvider()
        bt = run_momentum_pro_backtest(provider, symbol="RELIANCE", initial_capital=100000.0)
        self.assertEqual(bt["status"], "success")
        self.assertIn("win_rate_pct", bt)
        self.assertIn("profit_factor", bt)
        self.assertIn("expectancy", bt)
        self.assertIn("equity_curve", bt)
        self.assertTrue(0.0 <= bt["win_rate_pct"] <= 100.0)


if __name__ == "__main__":
    unittest.main()
