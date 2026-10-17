"""
Unit Tests for Historical Backtesting Engine and Indian Tax Calculations.
"""

import unittest
from backend.app.engines.backtest import (
    calculate_indian_statutory_charges,
    run_historical_backtest
)
from backend.app.data_providers.sample import SampleDataProvider


class TestBacktest(unittest.TestCase):

    def test_indian_statutory_charges(self):
        buy_amt = 50000.0
        sell_amt = 55000.0
        # Delivery trade
        charges = calculate_indian_statutory_charges(buy_amt, sell_amt, brokerage_per_trade=0.0)
        
        # STT = (50000 * 0.001) + (55000 * 0.001) = 50 + 55 = 105.0
        self.assertEqual(charges["stt"], 105.0)
        # Stamp Duty = 50000 * 0.00015 = 7.50
        self.assertEqual(charges["stamp_duty"], 7.50)
        # Brokerage should be 0.0
        self.assertEqual(charges["brokerage"], 0.0)
        # Total charges should be positive and include GST
        self.assertGreater(charges["total_charges"], 112.5)

    def test_backtest_simulation_structure(self):
        provider = SampleDataProvider()
        res = run_historical_backtest(
            provider=provider,
            symbols=["RELIANCE", "TCS", "INFY"],
            start_date="2024-01-01",
            end_date="2026-10-15",
            stop_loss_pct=5.0,
            target_pct=10.0,
            slippage_pct=0.2,
            capital_per_trade=50000.0
        )

        self.assertIn("total_trades", res)
        self.assertIn("win_rate_pct", res)
        self.assertIn("cagr_pct", res)
        self.assertIn("max_drawdown_pct", res)
        self.assertIn("equity_curve", res)
        self.assertIn("disclaimer", res)

        # Check equity curve starts at starting_capital
        if len(res["equity_curve"]) > 0:
            self.assertEqual(res["equity_curve"][0]["equity"], res["starting_capital"])


if __name__ == "__main__":
    unittest.main()
