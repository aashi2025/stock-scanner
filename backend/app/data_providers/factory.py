import logging
from backend.app.config import settings
from backend.app.data_providers.base import MarketDataProvider
from backend.app.data_providers.yahoo import YahooFinanceProvider
from backend.app.data_providers.sample import SampleDataProvider
from backend.app.data_providers.upstox import UpstoxDataProvider
from backend.app.data_providers.broker_stubs import BrokerAPIProviderStub

from backend.app.data_providers.csv_provider import CSVDataProvider

logger = logging.getLogger(__name__)

def get_market_data_provider(provider_name: str = None, force_sample: bool = False) -> MarketDataProvider:
    """
    Factory function returning the configured MarketDataProvider.
    Dynamically switches provider based on settings or explicitly requested sample mode.
    """
    if force_sample:
        return SampleDataProvider()

    target_provider = (provider_name or settings.MARKET_DATA_PROVIDER).lower()

    if target_provider == "sample":
        return SampleDataProvider()
    elif target_provider in ["csv", "local_csv", "file"]:
        return CSVDataProvider()
    elif target_provider in ["upstox", "upstox_api"]:
        return UpstoxDataProvider()
    elif target_provider in ["yahoo", "yfinance", "nse"]:
        return YahooFinanceProvider()
    elif target_provider in ["zerodha", "kite", "fyers", "angelone"]:
        if not settings.MARKET_API_KEY:
            logger.warning(f"Broker API provider '{target_provider}' requested but MARKET_API_KEY is not configured.")
        return BrokerAPIProviderStub(broker_name=target_provider.title())
    else:
        # Default fallback to Yahoo Finance for zero-budget live NSE data
        return YahooFinanceProvider()

