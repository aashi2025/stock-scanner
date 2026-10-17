"""
Unit Tests for Quantitative Ranking and Risk Engine.
"""

import unittest
from backend.app.engines.ranking import (
    calculate_trend_score,
    calculate_momentum_score,
    calculate_fundamental_score,
    calculate_valuation_score,
    calculate_risk_score,
    compute_composite_ranking
)


class TestRanking(unittest.TestCase):

    def setUp(self):
        self.bullish_ind = {
            "price": 2500.0,
            "ema_50": 2400.0,
            "ema_200": 2200.0,
            "rsi_14": 56.5,
            "rsi_fresh_crossover": True,
            "vol_ratio": 1.6,
            "rs_vs_nifty_20d": 4.2,
            "dist_from_52w_high_pct": 3.5,
            "atr_14": 35.0
        }

        self.verified_fund = {
            "roce": 24.5,
            "roe": 21.0,
            "debt_to_equity": 0.15,
            "sales_growth_3y": 14.2,
            "profit_growth_3y": 16.5,
            "pe_ratio": 24.0,
            "pb_ratio": 3.2,
            "cash_flow_operating": 50000000.0,
            "is_verified": True
        }

    def test_trend_score_bullish(self):
        score, details = calculate_trend_score(self.bullish_ind)
        self.assertGreaterEqual(score, 80.0)
        self.assertLessEqual(score, 100.0)

    def test_momentum_score_fresh(self):
        score, details = calculate_momentum_score(self.bullish_ind)
        # Should receive sweet spot + fresh crossover bonus + volume ratio
        self.assertGreaterEqual(score, 70.0)
        self.assertIn("Fresh RSI(14) crossover", " ".join(details))

    def test_missing_fundamentals_never_fabricated(self):
        # When fundamentals are missing / unverified
        unverified_fund = {"is_verified": False}
        score, details, has_fund = calculate_fundamental_score(unverified_fund)
        self.assertIsNone(score)
        self.assertFalse(has_fund)
        self.assertTrue(any("unavailable" in d.lower() for d in details))

    def test_composite_ranking_bounds_and_disclaimer(self):
        res = compute_composite_ranking(self.bullish_ind, self.verified_fund)
        self.assertGreaterEqual(res["composite_score"], 0.0)
        self.assertLessEqual(res["composite_score"], 100.0)
        self.assertIn("DISCLAIMER", res["disclaimer"])
        self.assertIn("trend_score", res)
        self.assertIn("momentum_score", res)
        self.assertIn("safety_score", res)

    def test_composite_ranking_without_fundamentals(self):
        # Dynamic rebalancing without fundamentals
        res = compute_composite_ranking(self.bullish_ind, None)
        self.assertGreaterEqual(res["composite_score"], 0.0)
        self.assertLessEqual(res["composite_score"], 100.0)
        self.assertFalse(res["has_fundamental_data"])


if __name__ == "__main__":
    unittest.main()
