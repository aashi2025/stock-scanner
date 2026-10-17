"""
CSV Market Data Provider.
Enables importing and scanning local daily OHLCV CSV files (NSE Bhavcopy, Yahoo exports, etc.)
with zero paid subscriptions or third-party API dependencies.
"""

import os
import io
from typing import Dict, Any, List, Optional
import pandas as pd
from datetime import datetime

from backend.app.data_providers.base import MarketDataProvider
from backend.app.data_providers.data_validator import validate_ohlcv_dataframe


class CSVDataProvider(MarketDataProvider):
    """
    Zero-Cost CSV File Provider.
    Loads and stores historical OHLCV data from local CSV files.
    Every dataset undergoes strict validation before being stored or scanned.
    """

    def __init__(self, data_directory: Optional[str] = None):
        if data_directory is None:
            # Default to data/stocks directory inside project
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            self.data_dir = os.path.join(base_dir, "data", "stocks")
        else:
            self.data_dir = data_directory

        os.makedirs(self.data_dir, exist_ok=True)
        self._memory_cache: Dict[str, pd.DataFrame] = {}
        self._validation_reports: Dict[str, Dict[str, Any]] = {}
        self._load_existing_files()

    def get_provider_name(self) -> str:
        return "Local CSV Storage (Zero-Budget Verified Files)"

    def is_sample_mode(self) -> bool:
        return False

    def _load_existing_files(self):
        """Scans data directory and validates all found CSV files."""
        if not os.path.exists(self.data_dir):
            return
            
        for file in os.listdir(self.data_dir):
            if file.endswith(".csv"):
                symbol = file[:-4].upper()
                file_path = os.path.join(self.data_dir, file)
                try:
                    df = pd.read_csv(file_path)
                    is_valid, clean_df, report = validate_ohlcv_dataframe(
                        df, symbol=symbol, data_source=f"File: {file}"
                    )
                    if is_valid:
                        self._memory_cache[symbol] = clean_df
                        self._validation_reports[symbol] = report
                except Exception as e:
                    self._validation_reports[symbol] = {
                        "symbol": symbol,
                        "is_valid": False,
                        "status": "LOAD_ERROR",
                        "errors": [str(e)],
                        "warnings": [],
                        "data_source": f"File: {file}",
                        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }

    def import_csv_data(self, symbol: str, csv_content_or_path: Any, data_source_label: str = "Uploaded CSV") -> Dict[str, Any]:
        """
        Imports, validates, and persists a stock's OHLCV CSV data.
        """
        sym = symbol.strip().upper()
        if isinstance(csv_content_or_path, str):
            if os.path.isfile(csv_content_or_path):
                raw_df = pd.read_csv(csv_content_or_path)
            else:
                raw_df = pd.read_csv(io.StringIO(csv_content_or_path))
        elif hasattr(csv_content_or_path, "read"):
            # BytesIO or file-like object from Streamlit file_uploader
            raw_df = pd.read_csv(csv_content_or_path)
        elif isinstance(csv_content_or_path, pd.DataFrame):
            raw_df = csv_content_or_path
        else:
            raise ValueError("Unsupported CSV input type")

        is_valid, clean_df, report = validate_ohlcv_dataframe(
            raw_df, symbol=sym, data_source=data_source_label
        )

        self._validation_reports[sym] = report

        if is_valid:
            self._memory_cache[sym] = clean_df
            # Persist to disk
            out_path = os.path.join(self.data_dir, f"{sym}.csv")
            clean_df.to_csv(out_path)

        return report

    def get_quote(self, symbol: str) -> Dict[str, Any]:
        sym = symbol.strip().upper()
        df = self.get_historical_data(sym)
        if df.empty:
            return {
                "symbol": sym,
                "price": 0.0,
                "change": 0.0,
                "change_percent": 0.0,
                "volume": 0,
                "avg_volume_20d": 0,
                "data_source": "None",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "status": "DATA_UNAVAILABLE"
            }

        last_price = float(df["Close"].iloc[-1])
        prev_price = float(df["Close"].iloc[-2]) if len(df) > 1 else last_price
        change = round(last_price - prev_price, 2)
        pct = round((change / prev_price * 100), 2) if prev_price > 0 else 0.0
        vol = int(df["Volume"].iloc[-1]) if "Volume" in df.columns else 0
        avg_vol = int(df["Volume"].tail(20).mean()) if "Volume" in df.columns and len(df) >= 20 else vol

        report = self._validation_reports.get(sym, {})

        return {
            "symbol": sym,
            "company_name": sym,
            "price": round(last_price, 2),
            "change": change,
            "change_percent": pct,
            "volume": vol,
            "avg_volume_20d": avg_vol,
            "timestamp": str(df.index[-1].strftime("%Y-%m-%d")) if hasattr(df.index[-1], "strftime") else str(df.index[-1]),
            "data_source": report.get("data_source", "CSV Storage"),
            "data_status": report.get("status", "VERIFIED")
        }

    def get_historical_data(self, symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
        sym = symbol.strip().upper()
        if sym in self._memory_cache:
            df = self._memory_cache[sym]
            if period == "1mo":
                return df.tail(22)
            elif period == "3mo":
                return df.tail(66)
            elif period == "6mo":
                return df.tail(130)
            elif period == "1y":
                return df.tail(252)
            return df

        # Try reading from disk
        file_path = os.path.join(self.data_dir, f"{sym}.csv")
        if os.path.exists(file_path):
            try:
                raw_df = pd.read_csv(file_path)
                is_valid, clean_df, report = validate_ohlcv_dataframe(raw_df, symbol=sym)
                if is_valid:
                    self._memory_cache[sym] = clean_df
                    self._validation_reports[sym] = report
                    return clean_df
            except Exception:
                pass

        return pd.DataFrame()

    def get_volume_data(self, symbol: str) -> Dict[str, Any]:
        df = self.get_historical_data(symbol)
        if df.empty or "Volume" not in df.columns:
            return {"current_volume": 0, "avg_volume_20d": 0, "volume_ratio": 1.0}
        cur_vol = int(df["Volume"].iloc[-1])
        avg_vol = int(df["Volume"].tail(20).mean()) if len(df) >= 20 else cur_vol
        ratio = round(cur_vol / avg_vol, 2) if avg_vol > 0 else 1.0
        return {
            "current_volume": cur_vol,
            "avg_volume_20d": avg_vol,
            "volume_ratio": ratio
        }

    def get_index_data(self, index_symbol: str) -> Dict[str, Any]:
        return self.get_quote(index_symbol)

    def get_sector_data(self, sector_symbol: str) -> Dict[str, Any]:
        return self.get_quote(sector_symbol)

    def get_fundamental_data(self, symbol: str) -> Dict[str, Any]:
        """
        Loads fundamental metrics if an accompanying JSON or CSV file exists.
        NEVER invents fundamental numbers. If missing, reports is_verified=False.
        """
        sym = symbol.strip().upper()
        fund_file = os.path.join(self.data_dir, f"{sym}_fundamentals.json")
        if os.path.exists(fund_file):
            import json
            try:
                with open(fund_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    data["is_verified"] = True
                    data["data_source"] = f"File: {sym}_fundamentals.json"
                    return data
            except Exception:
                pass

        # Return explicit unknown without fabricating numbers
        return {
            "symbol": sym,
            "market_cap": None,
            "roce": None,
            "roe": None,
            "debt_to_equity": None,
            "sales_growth_3y": None,
            "profit_growth_3y": None,
            "pe_ratio": None,
            "pb_ratio": None,
            "cash_flow_operating": None,
            "is_verified": False,
            "data_source": "No fundamental record on disk (Verify via Screener.in)"
        }

    def get_all_validation_reports(self) -> List[Dict[str, Any]]:
        """Returns health reports for all imported symbols."""
        return list(self._validation_reports.values())

    def list_available_symbols(self) -> List[str]:
        """Returns list of symbols available in local storage."""
        return sorted(list(set(list(self._memory_cache.keys()) + [
            f[:-4].upper() for f in os.listdir(self.data_dir) if f.endswith(".csv")
        ])))
