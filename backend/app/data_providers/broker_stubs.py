from typing import Dict, Any, List
import pandas as pd
from backend.app.data_providers.base import MarketDataProvider

class BrokerAPIProviderStub(MarketDataProvider):
    """
    Adapter Stub for Direct Broker APIs (Zerodha Kite Connect, Upstox API, Fyers API, AngelOne SmartAPI).
    Contains configuration stubs and API key setup instructions for Indian traders.
    """

    def __init__(self, broker_name: str = "Zerodha Kite Connect"):
        self.broker_name = broker_name

    def get_provider_name(self) -> str:
        return f"{self.broker_name} (Direct Broker API - Configuration Required)"

    def is_sample_mode(self) -> bool:
        return False

    def get_quote(self, symbol: str) -> Dict[str, Any]:
        raise NotImplementedError(
            f"Broker API '{self.broker_name}' requires valid MARKET_API_KEY and MARKET_API_SECRET in backend environment settings."
        )

    def get_historical_data(self, symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
        raise NotImplementedError(
            f"Broker API '{self.broker_name}' requires valid MARKET_API_KEY and MARKET_API_SECRET in backend environment settings."
        )

    def get_volume_data(self, symbol: str) -> Dict[str, Any]:
        raise NotImplementedError("Broker API credentials missing.")

    def get_index_data(self, index_symbol: str) -> Dict[str, Any]:
        raise NotImplementedError("Broker API credentials missing.")

    def get_sector_data(self, sector_symbol: str) -> Dict[str, Any]:
        raise NotImplementedError("Broker API credentials missing.")

    def get_fundamental_data(self, symbol: str) -> Dict[str, Any]:
        return {}
