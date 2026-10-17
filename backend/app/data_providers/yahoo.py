import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging
from backend.app.data_providers.base import MarketDataProvider

logger = logging.getLogger(__name__)

# Sector Index Map for Yahoo Finance NSE indices
INDEX_MAP = {
    "NIFTY 50": "^NSEI",
    "NIFTY 100": "^CNX100",
    "NIFTY 500": "^CRSLDX",
    "NIFTY IT": "^CNXIT",
    "NIFTY AUTO": "^CNXAUTO",
    "NIFTY BANK": "^NSEBANK",
    "NIFTY PHARMA": "^CNXPHARMA",
    "NIFTY FMCG": "^CNXFMCG",
    "NIFTY METAL": "^CNXMETAL",
    "NIFTY ENERGY": "^CNXENERGY",
    "NIFTY REALTY": "^CNXREALTY",
    "NIFTY INFRA": "^CNXINFRA"
}

class YahooFinanceProvider(MarketDataProvider):
    """
    Production-ready real market data provider using Yahoo Finance API for NSE/BSE.
    Formats symbols with '.NS' suffix for National Stock Exchange of India.
    """

    def __init__(self):
        self._cache = {}

    def get_provider_name(self) -> str:
        return "Yahoo Finance API (NSE/BSE Real Market Data)"

    def is_sample_mode(self) -> bool:
        return False

    def _format_symbol(self, symbol: str) -> str:
        sym = symbol.strip().upper()
        if sym in INDEX_MAP:
            return INDEX_MAP[sym]
        if sym.startswith("^"):
            return sym
        if not (sym.endswith(".NS") or sym.endswith(".BO")):
            return f"{sym}.NS"
        return sym

    def get_quote(self, symbol: str) -> Dict[str, Any]:
        yf_symbol = self._format_symbol(symbol)
        try:
            ticker = yf.Ticker(yf_symbol)
            info = ticker.fast_info
            
            price = float(info.last_price) if hasattr(info, 'last_price') and info.last_price else 0.0
            prev_close = float(info.previous_close) if hasattr(info, 'previous_close') and info.previous_close else price
            change = price - prev_close
            change_percent = (change / prev_close * 100) if prev_close else 0.0
            
            # Fetch recent volume
            df = self.get_historical_data(symbol, period="1mo", interval="1d")
            volume = int(df['Volume'].iloc[-1]) if not df.empty and 'Volume' in df.columns else 0
            avg_vol = int(df['Volume'].tail(20).mean()) if not df.empty and 'Volume' in df.columns else volume
            
            market_cap = getattr(info, 'market_cap', None)

            return {
                "symbol": symbol.upper(),
                "company_name": symbol.upper(),
                "exchange": "NSE",
                "sector": "General",
                "price": round(price, 2),
                "change": round(change, 2),
                "change_percent": round(change_percent, 2),
                "volume": volume,
                "avg_volume_20d": avg_vol,
                "market_cap": market_cap,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "data_source": "NSE (Yahoo Finance API)",
                "is_sample_data": False
            }
        except Exception as e:
            logger.error(f"Error fetching quote for {symbol}: {e}")
            # Fallback to historical last row
            df = self.get_historical_data(symbol, period="5d", interval="1d")
            if not df.empty:
                last_price = float(df['Close'].iloc[-1])
                prev_price = float(df['Close'].iloc[-2]) if len(df) > 1 else last_price
                chg = last_price - prev_price
                return {
                    "symbol": symbol.upper(),
                    "company_name": symbol.upper(),
                    "exchange": "NSE",
                    "sector": "General",
                    "price": round(last_price, 2),
                    "change": round(chg, 2),
                    "change_percent": round((chg / prev_price * 100) if prev_price else 0, 2),
                    "volume": int(df['Volume'].iloc[-1]),
                    "avg_volume_20d": int(df['Volume'].mean()),
                    "market_cap": None,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "data_source": "NSE (Yahoo Finance Historical)",
                    "is_sample_data": False
                }
            raise ValueError(f"Could not fetch market quote for {symbol} from Yahoo Finance: {str(e)}")

    def get_historical_data(self, symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
        yf_symbol = self._format_symbol(symbol)
        cache_key = f"{yf_symbol}_{period}_{interval}"
        
        if cache_key in self._cache:
            cached_time, cached_df = self._cache[cache_key]
            # 5 minute cache freshness
            if (datetime.now() - cached_time).total_seconds() < 300:
                return cached_df.copy()

        try:
            ticker = yf.Ticker(yf_symbol)
            df = ticker.history(period=period, interval=interval)
            if df.empty:
                logger.warning(f"No historical data returned for {yf_symbol}")
                return pd.DataFrame()
            
            # Clean dataframe
            df = df.dropna(subset=['Close'])
            self._cache[cache_key] = (datetime.now(), df)
            return df
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {e}")
            return pd.DataFrame()

    def get_volume_data(self, symbol: str) -> Dict[str, Any]:
        df = self.get_historical_data(symbol, period="3mo", interval="1d")
        if df.empty or 'Volume' not in df.columns:
            return {"current_volume": 0, "avg_volume_20d": 0, "volume_ratio": 1.0}
        
        cur_vol = int(df['Volume'].iloc[-1])
        avg_20 = int(df['Volume'].tail(20).mean())
        ratio = (cur_vol / avg_20) if avg_20 > 0 else 1.0
        return {
            "current_volume": cur_vol,
            "avg_volume_20d": avg_20,
            "volume_ratio": round(ratio, 2)
        }

    def get_index_data(self, index_symbol: str) -> Dict[str, Any]:
        return self.get_quote(index_symbol)

    def get_sector_data(self, sector_symbol: str) -> Dict[str, Any]:
        return self.get_quote(sector_symbol)

    def get_fundamental_data(self, symbol: str) -> Dict[str, Any]:
        yf_symbol = self._format_symbol(symbol)
        try:
            ticker = yf.Ticker(yf_symbol)
            info = ticker.info
            return {
                "market_cap": info.get("marketCap"),
                "sector": info.get("sector", "General"),
                "industry": info.get("industry"),
                "pe_ratio": info.get("trailingPE"),
                "pb_ratio": info.get("priceToBook"),
                "52w_high": info.get("fiftyTwoWeekHigh"),
                "52w_low": info.get("fiftyTwoWeekLow")
            }
        except Exception:
            return {"sector": "General"}
