"""
Unit Tests for Multi-Stock Portfolio Backtest Engine.
"""

import unittest
from backend.app.data_providers.sample import SampleDataProvider
from backend.app.engines.portfolio_backtest import run_portfolio_backtest


class TestPortfolioBacktest(unittest.TestCase):

    def test_portfolio_backtest_execution(self):
        provider = SampleDataProvider()
        symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ITC"]

        res = run_portfolio_backtest(
            provider=provider,
            symbols=symbols,
            start_date="2024-01-01",
            end_date="2026-10-15",
            initial_capital=500000.0,
            max_positions=3,
            stop_loss_pct=5.0,
            target_pct=10.0,
            trailing_exit_type="ema_50"
        )

        self.assertIn("initial_capital", res)
        self.assertEqual(res["initial_capital"], 500000.0)
        self.assertIn("cagr_pct", res)
        self.assertIn("max_drawdown_pct", res)
        self.assertIn("sharpe_ratio", res)
        self.assertIn("equity_curve", res)

        # Check maximum concurrent positions constraint was never violated
        for point in res["equity_curve"]:
            self.assertLessEqual(point["open_positions"], 3)


if __name__ == "__main__":
    unittest.main()
