"""
Unit Tests for Watchlist Manager & Invalidation Monitor.
"""

import unittest
from backend.app.watchlist.manager import add_to_watchlist, remove_from_watchlist, load_watchlist


class TestWatchlist(unittest.TestCase):

    def test_add_and_remove_watchlist(self):
        test_sym = "UNIT_TEST_SYM"
        add_to_watchlist(test_sym, notes="Test breakout setup")
        items = load_watchlist()
        self.assertTrue(any(i["symbol"] == test_sym for i in items))

        remove_from_watchlist(test_sym)
        items_after = load_watchlist()
        self.assertFalse(any(i["symbol"] == test_sym for i in items_after))


if __name__ == "__main__":
    unittest.main()
