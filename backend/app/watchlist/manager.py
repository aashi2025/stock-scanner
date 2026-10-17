"""
Watchlist Manager & Invalidation Monitor.
Stores user's watched stocks in a simple local JSON file.
Monitors technical invalidation conditions (e.g. breakdown below 50 EMA or RSI < 45).
"""

import os
import json
from typing import Dict, Any, List
from datetime import datetime

from backend.app.data_providers.base import MarketDataProvider
from backend.app.indicators.calculations import calculate_ema, calculate_rsi

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
WATCHLIST_FILE = os.path.join(PROJECT_ROOT, "data", "watchlist.json")


def load_watchlist() -> List[Dict[str, Any]]:
    """Loads watchlist from local JSON file."""
    if not os.path.exists(WATCHLIST_FILE):
        return []
    try:
        with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_watchlist(items: List[Dict[str, Any]]) -> bool:
    """Saves watchlist items to local JSON file."""
    os.makedirs(os.path.dirname(WATCHLIST_FILE), exist_ok=True)
    try:
        with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
            json.dump(items, f, indent=2)
        return True
    except Exception:
        return False


def add_to_watchlist(symbol: str, company_name: str = "", notes: str = "") -> bool:
    """Adds a stock to watchlist if not already present."""
    sym = symbol.strip().upper()
    items = load_watchlist()
    for item in items:
        if item["symbol"] == sym:
            item["notes"] = notes or item.get("notes", "")
            return save_watchlist(items)

    items.append({
        "symbol": sym,
        "company_name": company_name or sym,
        "added_on": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "notes": notes
    })
    return save_watchlist(items)


def remove_from_watchlist(symbol: str) -> bool:
    """Removes a stock from watchlist."""
    sym = symbol.strip().upper()
    items = load_watchlist()
    new_items = [i for i in items if i["symbol"] != sym]
    return save_watchlist(new_items)


def monitor_watchlist_health(provider: MarketDataProvider) -> List[Dict[str, Any]]:
    """
    Evaluates current status of all watchlist stocks:
    Flags invalidation warnings (Close < 50 EMA, RSI < 45, etc.)
    """
    items = load_watchlist()
    results = []

    for item in items:
        sym = item["symbol"]
        df = provider.get_historical_data(sym)
        if df.empty or len(df) < 50:
            results.append({
                "symbol": sym,
                "price": 0.0,
                "status": "DATA_UNAVAILABLE",
                "warning": "No historical candle data found",
                "notes": item.get("notes", "")
            })
            continue

        close = df["Close"]
        price = float(close.iloc[-1])
        ema_50 = float(calculate_ema(close, 50).iloc[-1])
        rsi = float(calculate_rsi(close, 14).iloc[-1])

        warnings = []
        is_invalidated = False

        if price < ema_50:
            warnings.append(f"Price (₹{price}) slipped BELOW 50 EMA (₹{round(ema_50, 2)})")
            is_invalidated = True

        if rsi < 45.0:
            warnings.append(f"RSI is weak at {round(rsi, 1)} (< 45 momentum breakdown)")
            is_invalidated = True

        status = "⚠️ SETUP INVALIDATED" if is_invalidated else "✅ SETUP INTACT (BULLISH)"

        results.append({
            "symbol": sym,
            "company_name": item.get("company_name", sym),
            "price": price,
            "ema_50": round(ema_50, 2),
            "rsi_14": round(rsi, 1),
            "status": status,
            "is_invalidated": is_invalidated,
            "warnings": warnings,
            "added_on": item.get("added_on", "-"),
            "notes": item.get("notes", "")
        })

    return results
