from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import pandas as pd

class MarketDataProvider(ABC):
    """
    Abstract Base Class / Interface for Market Data Architecture.
    Allows switching between live market data APIs (Yahoo Finance, Zerodha Kite, Upstox, Fyers, AngelOne)
    and Sample Data Mode for testing without altering core scanner logic.
    """

    @abstractmethod
    def get_provider_name(self) -> str:
        """Returns the human-readable name of the market data provider."""
        pass

    @abstractmethod
    def is_sample_mode(self) -> bool:
        """Returns True if this provider is strictly using sample/test data."""
        pass

    @abstractmethod
    def get_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Fetches the latest quote for a stock or index.
        Returns dictionary with symbol, price, change, volume, avg_volume_20d, etc.
        """
        pass

    @abstractmethod
    def get_historical_data(self, symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
        """
        Fetches historical daily OHLCV data.
        Returns DataFrame with Date index and columns: Open, High, Low, Close, Volume.
        """
        pass

    @abstractmethod
    def get_volume_data(self, symbol: str) -> Dict[str, Any]:
        """
        Fetches volume metrics: current volume, 20-day average volume, volume surge ratio.
        """
        pass

    @abstractmethod
    def get_index_data(self, index_symbol: str) -> Dict[str, Any]:
        """
        Fetches index quote and key technical levels (e.g. NIFTY 50: ^NSEI).
        """
        pass

    @abstractmethod
    def get_sector_data(self, sector_symbol: str) -> Dict[str, Any]:
        """
        Fetches sector index data (e.g., NIFTY IT, NIFTY Auto).
        """
        pass

    @abstractmethod
    def get_fundamental_data(self, symbol: str) -> Dict[str, Any]:
        """
        Fetches basic fundamental data if available (Market Cap, Sector, Exchange).
        """
        pass
