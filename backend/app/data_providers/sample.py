import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List
from backend.app.data_providers.base import MarketDataProvider

class SampleDataProvider(MarketDataProvider):
    """
    Explicitly labeled Sample Data Provider.
    Used ONLY when Sample Data Mode is manually toggled by user or explicitly allowed for offline testing.
    All returned objects have `is_sample_data = True` and clear data_source disclaimers.
    """

    def get_provider_name(self) -> str:
        return "Explicit Sample Data Mode (Offline / UI Testing Only)"

    def is_sample_mode(self) -> bool:
        return True

    def get_quote(self, symbol: str) -> Dict[str, Any]:
        np.random.seed(hash(symbol) % 100000)
        base_price = 500.0 + (hash(symbol) % 2500)
        change = round(np.random.uniform(-15.0, 25.0), 2)
        pct = round((change / base_price) * 100, 2)
        
        return {
            "symbol": symbol.upper(),
            "company_name": f"{symbol.upper()} (Sample Data)",
            "exchange": "NSE-SAMPLE",
            "sector": "Sample Sector",
            "price": round(base_price + change, 2),
            "change": change,
            "change_percent": pct,
            "volume": int(np.random.uniform(500000, 5000000)),
            "avg_volume_20d": int(np.random.uniform(400000, 4000000)),
            "market_cap": float(base_price * 10000000),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data_source": "EXPLICIT SAMPLE DATA MODE (FOR UI/ENGINE TESTING ONLY)",
            "is_sample_data": True
        }

    def get_historical_data(self, symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
        days = 250 if period == "1y" else 90
        dates = [datetime.now() - timedelta(days=i) for i in range(days)]
        dates.reverse()

        np.random.seed(hash(symbol) % 100000)
        
        # Determine deterministic trend based on symbol name to test scanner pass/fail rules
        sym_upper = symbol.upper()
        if "RELIANCE" in sym_upper or "TCS" in sym_upper or "INFY" in sym_upper or "ICICIBANK" in sym_upper or "BHARTIARTL" in sym_upper or "LT" in sym_upper:
            drift = 0.0015  # Strong Bullish trend
        elif "TATAMOTORS" in sym_upper or "HDFCBANK" in sym_upper or "SBIN" in sym_upper:
            drift = 0.0008  # Moderate Bullish
        elif "WIPRO" in sym_upper or "SUNPHARMA" in sym_upper:
            drift = 0.0001  # Neutral
        else:
            drift = -0.0005 # Bearish

        returns = np.random.normal(drift, 0.015, days)
        start_price = 1000.0 + (hash(symbol) % 1500)
        prices = start_price * np.exp(np.cumsum(returns))

        highs = prices * (1 + np.abs(np.random.normal(0, 0.008, days)))
        lows = prices * (1 - np.abs(np.random.normal(0, 0.008, days)))
        opens = lows + (highs - lows) * np.random.uniform(0.1, 0.9, days)
        volumes = np.random.uniform(500000, 5000000, days)

        df = pd.DataFrame({
            "Open": opens,
            "High": highs,
            "Low": lows,
            "Close": prices,
            "Volume": volumes
        }, index=pd.to_datetime(dates))
        
        return df

    def get_volume_data(self, symbol: str) -> Dict[str, Any]:
        df = self.get_historical_data(symbol)
        cur_vol = int(df['Volume'].iloc[-1])
        avg_20 = int(df['Volume'].tail(20).mean())
        return {
            "current_volume": cur_vol,
            "avg_volume_20d": avg_20,
            "volume_ratio": round(cur_vol / avg_20, 2)
        }

    def get_index_data(self, index_symbol: str) -> Dict[str, Any]:
        return self.get_quote(index_symbol)

    def get_sector_data(self, sector_symbol: str) -> Dict[str, Any]:
        return self.get_quote(sector_symbol)

    def get_fundamental_data(self, symbol: str) -> Dict[str, Any]:
        return {
            "market_cap": 150000000000.0,
            "sector": "Sample Sector",
            "industry": "Sample Industry",
            "pe_ratio": 22.5,
            "pb_ratio": 3.8,
            "52w_high": 2800.0,
            "52w_low": 1900.0
        }
