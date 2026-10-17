import os
import json
import gzip
import logging
import requests
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Fallback mapping for core Nifty 50 and major market indices in case network download is delayed
BUILTIN_EQUITY_MAP = {
    "RELIANCE": {"instrument_key": "NSE_EQ|INE002A01018", "isin": "INE002A01018", "name": "Reliance Industries Ltd."},
    "TCS": {"instrument_key": "NSE_EQ|INE467B01029", "isin": "INE467B01029", "name": "Tata Consultancy Services Ltd."},
    "HDFCBANK": {"instrument_key": "NSE_EQ|INE040A01034", "isin": "INE040A01034", "name": "HDFC Bank Ltd."},
    "BHARTIARTL": {"instrument_key": "NSE_EQ|INE397D01024", "isin": "INE397D01024", "name": "Bharti Airtel Ltd."},
    "ICICIBANK": {"instrument_key": "NSE_EQ|INE090A01021", "isin": "INE090A01021", "name": "ICICI Bank Ltd."},
    "INFY": {"instrument_key": "NSE_EQ|INE009A01021", "isin": "INE009A01021", "name": "Infosys Ltd."},
    "ITC": {"instrument_key": "NSE_EQ|INE154A01025", "isin": "INE154A01025", "name": "ITC Ltd."},
    "SBIN": {"instrument_key": "NSE_EQ|INE062A01020", "isin": "INE062A01020", "name": "State Bank of India"},
    "LTIM": {"instrument_key": "NSE_EQ|INE214T01019", "isin": "INE214T01019", "name": "LTIMindtree Ltd."},
    "LT": {"instrument_key": "NSE_EQ|INE018A01030", "isin": "INE018A01030", "name": "Larsen & Toubro Ltd."},
    "HINDUNILVR": {"instrument_key": "NSE_EQ|INE030A01027", "isin": "INE030A01027", "name": "Hindustan Unilever Ltd."},
    "TATAMOTORS": {"instrument_key": "NSE_EQ|INE155A01022", "isin": "INE155A01022", "name": "Tata Motors Ltd."},
    "M&M": {"instrument_key": "NSE_EQ|INE101A01026", "isin": "INE101A01026", "name": "Mahindra & Mahindra Ltd."},
    "SUNPHARMA": {"instrument_key": "NSE_EQ|INE044A01036", "isin": "INE044A01036", "name": "Sun Pharmaceutical Industries"},
    "NTPC": {"instrument_key": "NSE_EQ|INE733E01010", "isin": "INE733E01010", "name": "NTPC Ltd."},
    "ONGC": {"instrument_key": "NSE_EQ|INE213A01029", "isin": "INE213A01029", "name": "Oil & Natural Gas Corp."},
    "TITAN": {"instrument_key": "NSE_EQ|INE280A01028", "isin": "INE280A01028", "name": "Titan Company Ltd."},
    "MARUTI": {"instrument_key": "NSE_EQ|INE585B01010", "isin": "INE585B01010", "name": "Maruti Suzuki India Ltd."},
    "POWERGRID": {"instrument_key": "NSE_EQ|INE752E01010", "isin": "INE752E01010", "name": "Power Grid Corp of India"},
    "AXISBANK": {"instrument_key": "NSE_EQ|INE238A01034", "isin": "INE238A01034", "name": "Axis Bank Ltd."},
    "KOTAKBANK": {"instrument_key": "NSE_EQ|INE237A01028", "isin": "INE237A01028", "name": "Kotak Mahindra Bank Ltd."},
    "ADANIENT": {"instrument_key": "NSE_EQ|INE423A01024", "isin": "INE423A01024", "name": "Adani Enterprises Ltd."},
    "ADANIPORTS": {"instrument_key": "NSE_EQ|INE742F01042", "isin": "INE742F01042", "name": "Adani Ports & SEZ Ltd."},
    "TATASTEEL": {"instrument_key": "NSE_EQ|INE081A01020", "isin": "INE081A01020", "name": "Tata Steel Ltd."},
    "JSWSTEEL": {"instrument_key": "NSE_EQ|INE019A01038", "isin": "INE019A01038", "name": "JSW Steel Ltd."},
    "HCLTECH": {"instrument_key": "NSE_EQ|INE860A01027", "isin": "INE860A01027", "name": "HCL Technologies Ltd."},
    "WIPRO": {"instrument_key": "NSE_EQ|INE075A01022", "isin": "INE075A01022", "name": "Wipro Ltd."},
    "TECHM": {"instrument_key": "NSE_EQ|INE669C01036", "isin": "INE669C01036", "name": "Tech Mahindra Ltd."},
    "BAJFINANCE": {"instrument_key": "NSE_EQ|INE296A01024", "isin": "INE296A01024", "name": "Bajaj Finance Ltd."},
    "BAJAJFINSV": {"instrument_key": "NSE_EQ|INE918I01026", "isin": "INE918I01026", "name": "Bajaj Finserv Ltd."},
    "ASIANPAINT": {"instrument_key": "NSE_EQ|INE021A01026", "isin": "INE021A01026", "name": "Asian Paints Ltd."},
    "ULTRACEMCO": {"instrument_key": "NSE_EQ|INE481G01011", "isin": "INE481G01011", "name": "UltraTech Cement Ltd."},
    "NESTLEIND": {"instrument_key": "NSE_EQ|INE239A01024", "isin": "INE239A01024", "name": "Nestle India Ltd."},
    "COALINDIA": {"instrument_key": "NSE_EQ|INE522F01014", "isin": "INE522F01014", "name": "Coal India Ltd."},
    "GRASIM": {"instrument_key": "NSE_EQ|INE047A01021", "isin": "INE047A01021", "name": "Grasim Industries Ltd."},
    "CIPLA": {"instrument_key": "NSE_EQ|INE059A01026", "isin": "INE059A01026", "name": "Cipla Ltd."},
    "DRREDDY": {"instrument_key": "NSE_EQ|INE089A01023", "isin": "INE089A01023", "name": "Dr. Reddy's Laboratories"},
    "EICHERMOT": {"instrument_key": "NSE_EQ|INE066A01021", "isin": "INE066A01021", "name": "Eicher Motors Ltd."},
    "HEROMOTOCO": {"instrument_key": "NSE_EQ|INE158A01026", "isin": "INE158A01026", "name": "Hero MotoCorp Ltd."},
    "APOLLOHOSP": {"instrument_key": "NSE_EQ|INE437A01024", "isin": "INE437A01024", "name": "Apollo Hospitals Enterprise"},
    "DIVISLAB": {"instrument_key": "NSE_EQ|INE361B01024", "isin": "INE361B01024", "name": "Divi's Laboratories Ltd."},
    "TATACONSUM": {"instrument_key": "NSE_EQ|INE192A01025", "isin": "INE192A01025", "name": "Tata Consumer Products Ltd."},
    "BPCL": {"instrument_key": "NSE_EQ|INE029A01011", "isin": "INE029A01011", "name": "Bharat Petroleum Corp. Ltd."},
    "HDFCLIFE": {"instrument_key": "NSE_EQ|INE795G01014", "isin": "INE795G01014", "name": "HDFC Life Insurance Co."},
    "SBILIFE": {"instrument_key": "NSE_EQ|INE123W01016", "isin": "INE123W01016", "name": "SBI Life Insurance Co. Ltd."},
    "BEL": {"instrument_key": "NSE_EQ|INE263A01024", "isin": "INE263A01024", "name": "Bharat Electronics Ltd."},
    "TRENT": {"instrument_key": "NSE_EQ|INE849A01020", "isin": "INE849A01020", "name": "Trent Ltd."},
    "HINDALCO": {"instrument_key": "NSE_EQ|INE038A01020", "isin": "INE038A01020", "name": "Hindalco Industries Ltd."},
    "SHRIRAMFIN": {"instrument_key": "NSE_EQ|INE721A01013", "isin": "INE721A01013", "name": "Shriram Finance Ltd."}
}

BUILTIN_INDEX_MAP = {
    "NIFTY 50": "NSE_INDEX|Nifty 50",
    "NIFTY": "NSE_INDEX|Nifty 50",
    "^NSEI": "NSE_INDEX|Nifty 50",
    "NIFTY BANK": "NSE_INDEX|Nifty Bank",
    "BANKNIFTY": "NSE_INDEX|Nifty Bank",
    "NIFTY IT": "NSE_INDEX|Nifty IT",
    "NIFTY AUTO": "NSE_INDEX|Nifty Auto",
    "NIFTY PHARMA": "NSE_INDEX|Nifty Pharma",
    "NIFTY FMCG": "NSE_INDEX|Nifty FMCG",
    "NIFTY METAL": "NSE_INDEX|Nifty Metal",
    "NIFTY ENERGY": "NSE_INDEX|Nifty Energy",
    "NIFTY REALTY": "NSE_INDEX|Nifty Realty",
    "NIFTY INFRA": "NSE_INDEX|Nifty Infra",
    "NIFTY FINANCIAL SERVICES": "NSE_INDEX|Nifty Fin Service",
    "NIFTY 100": "NSE_INDEX|Nifty 100",
    "NIFTY 500": "NSE_INDEX|Nifty 500"
}

class UpstoxInstrumentManager:
    """
    Manages Upstox official instrument keys for NSE equities and indices.
    Caches master list locally in JSON format to guarantee 0-cost, fast local operation.
    """
    def __init__(self, cache_dir: Optional[str] = None):
        if not cache_dir:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            cache_dir = os.path.join(base_dir, "cache")
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        self.cache_file = os.path.join(self.cache_dir, "upstox_nse_instruments.json")
        self.equity_map: Dict[str, Dict[str, Any]] = dict(BUILTIN_EQUITY_MAP)
        self.index_map: Dict[str, str] = dict(BUILTIN_INDEX_MAP)
        self._load_cache()

    def _load_cache(self):
        """Loads cached instrument file if present, or downloads it automatically."""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    cached_data = json.load(f)
                    if isinstance(cached_data, dict):
                        self.equity_map.update(cached_data.get("equities", {}))
                        self.index_map.update(cached_data.get("indices", {}))
                        logger.info(f"Loaded {len(self.equity_map)} NSE instruments from cache.")
            except Exception as e:
                logger.warning(f"Failed to load cached Upstox instruments: {e}")
        else:
            self.download_and_update_instruments()


    def download_and_update_instruments(self) -> bool:
        """
        Downloads latest official master instrument list from Upstox CDN:
        https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz
        Zero cost, no authentication required.
        """
        url = "https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz"
        try:
            logger.info("Downloading official Upstox NSE instrument list...")
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200:
                raw_json = gzip.decompress(resp.content).decode("utf-8")
                instruments = json.loads(raw_json)
                
                new_equities = {}
                new_indices = {}
                
                for item in instruments:
                    segment = item.get("segment")
                    symbol = item.get("trading_symbol")
                    inst_key = item.get("instrument_key")
                    isin = item.get("isin", "")
                    name = item.get("name", symbol)

                    if not symbol or not inst_key:
                        continue

                    if segment == "NSE_EQ" and item.get("instrument_type") == "EQ":
                        new_equities[symbol.upper()] = {
                            "instrument_key": inst_key,
                            "isin": isin,
                            "name": name
                        }
                    elif segment == "NSE_INDEX":
                        new_indices[symbol.upper()] = inst_key
                        # Also handle normal casing
                        new_indices[name.upper()] = inst_key

                # Update in-memory
                self.equity_map.update(new_equities)
                self.index_map.update(new_indices)

                # Persist to disk
                with open(self.cache_file, "w", encoding="utf-8") as f:
                    json.dump({"equities": self.equity_map, "indices": self.index_map}, f)

                logger.info(f"Successfully cached {len(self.equity_map)} NSE Equities and {len(self.index_map)} Indices.")
                return True
        except Exception as e:
            logger.error(f"Error downloading Upstox instrument list: {e}")
        return False

    def get_instrument_key(self, symbol: str) -> Optional[str]:
        """Returns the official Upstox instrument_key for an equity symbol or index."""
        cleaned = symbol.strip().upper().replace(".NS", "").replace("^", "")
        
        # 1. Check index map
        if cleaned in self.index_map:
            return self.index_map[cleaned]
        for idx_k, idx_v in self.index_map.items():
            if cleaned == idx_k.replace(" ", "") or cleaned in idx_k:
                return idx_v

        # 2. Check equity map
        if cleaned in self.equity_map:
            return self.equity_map[cleaned]["instrument_key"]

        # Default fallback convention for NSE Equity if known ISIN pattern
        return None

    def get_isin(self, symbol: str) -> Optional[str]:
        """Returns ISIN for fundamental API lookup."""
        cleaned = symbol.strip().upper().replace(".NS", "").replace("^", "")
        if cleaned in self.equity_map:
            return self.equity_map[cleaned].get("isin")
        return None

# Global Singleton
instrument_manager = UpstoxInstrumentManager()
