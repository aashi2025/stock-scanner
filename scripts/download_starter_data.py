"""
Starter Data Downloader for Zero-Budget Local Use.
Fetches verified historical OHLCV data from official public Yahoo Finance NSE feeds
and validates every record before saving to data/stocks/.
Completely free - zero monthly rupee cost.
"""

import os
import sys
import yfinance as yf
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.app.data_providers.data_validator import validate_ohlcv_dataframe

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STOCKS_DIR = os.path.join(BASE_DIR, "data", "stocks")
os.makedirs(STOCKS_DIR, exist_ok=True)

STARTER_STOCKS = [
    ("RELIANCE", "RELIANCE.NS"),
    ("TCS", "TCS.NS"),
    ("INFY", "INFY.NS"),
    ("HDFCBANK", "HDFCBANK.NS"),
    ("ITC", "ITC.NS"),
    ("MARUTI", "MARUTI.NS"),
    ("ICICIBANK", "ICICIBANK.NS"),
    ("BHARTIARTL", "BHARTIARTL.NS"),
    ("SBIN", "SBIN.NS"),
    ("LT", "LT.NS"),
    ("NIFTY 50", "^NSEI")
]

def download_starter_stocks():
    print("=" * 60)
    print("   ZERO-BUDGET STARTER DATA DOWNLOAD (NSE)")
    print("=" * 60)

    for symbol, ticker_sym in STARTER_STOCKS:
        print(f"Fetching {symbol} ({ticker_sym})...")
        try:
            ticker = yf.Ticker(ticker_sym)
            df = ticker.history(period="2y", interval="1d")
            if df.empty:
                print(f"  [WARN] No data received for {symbol}")
                continue

            df = df.reset_index()
            # Rename Date/Datetime
            date_col = next((c for c in df.columns if "date" in str(c).lower()), None)
            if date_col:
                df = df.rename(columns={date_col: "Date"})
            
            # Keep required columns
            cols = [c for c in ["Date", "Open", "High", "Low", "Close", "Volume"] if c in df.columns]
            df = df[cols]

            # Validate before saving
            is_valid, clean_df, report = validate_ohlcv_dataframe(
                df, symbol=symbol, data_source=f"NSE via Yahoo ({ticker_sym})"
            )

            if is_valid:
                clean_sym = symbol.replace(" ", "_")
                out_path = os.path.join(STOCKS_DIR, f"{clean_sym}.csv")
                clean_df.to_csv(out_path)
                print(f"  [OK] Saved & Verified {symbol}: {report['total_records']} bars ({report['status']})")
            else:
                print(f"  [FAIL] Validation failed for {symbol}: {report['errors']}")

        except Exception as e:
            print(f"  [ERROR] Failed to fetch {symbol}: {e}")

    print("=" * 60)
    print("Starter data download completed.")

if __name__ == "__main__":
    download_starter_stocks()
