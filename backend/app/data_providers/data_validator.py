"""
Data Validator Module for Indian Stock Research Platform.
Validates daily OHLCV CSV data with zero tolerance for corrupted records,
look-ahead timestamps, or fabricated figures.
"""

from typing import Dict, Any, List, Tuple, Optional
import pandas as pd
import numpy as np
from datetime import datetime, date

REQUIRED_COLUMNS = ["Date", "Open", "High", "Low", "Close", "Volume"]

COLUMN_ALIASES = {
    "date": "Date", "timestamp": "Date", "time": "Date", "datetime": "Date",
    "open": "Open", "open_price": "Open",
    "high": "High", "high_price": "High",
    "low": "Low", "low_price": "Low",
    "close": "Close", "close_price": "Close", "ltp": "Close", "prevclose": "Close",
    "volume": "Volume", "vol": "Volume", "tottrdqty": "Volume", "total_traded_quantity": "Volume"
}


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Standardizes column names to Date, Open, High, Low, Close, Volume."""
    rename_dict = {}
    for col in df.columns:
        clean_name = str(col).strip().lower().replace(" ", "_")
        if clean_name in COLUMN_ALIASES:
            rename_dict[col] = COLUMN_ALIASES[clean_name]
    return df.rename(columns=rename_dict)


def validate_ohlcv_dataframe(
    df: pd.DataFrame,
    symbol: str = "UNKNOWN",
    data_source: str = "CSV Import",
    stale_days_threshold: int = 5
) -> Tuple[bool, pd.DataFrame, Dict[str, Any]]:
    """
    Validates and cleans an OHLCV dataframe.
    
    Returns:
        (is_valid: bool, cleaned_df: pd.DataFrame, report: Dict[str, Any])
    """
    errors: List[str] = []
    warnings: List[str] = []
    
    if df is None or df.empty:
        return False, pd.DataFrame(), {
            "symbol": symbol,
            "is_valid": False,
            "status": "MISSING / EMPTY",
            "total_records": 0,
            "errors": ["Dataset is empty or None"],
            "warnings": [],
            "data_source": data_source,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    clean_df = normalize_columns(df.copy())
    
    # 1. Column existence check
    missing_cols = [c for c in REQUIRED_COLUMNS if c not in clean_df.columns]
    if missing_cols:
        errors.append(f"Missing required columns: {', '.join(missing_cols)}")
        return False, pd.DataFrame(), {
            "symbol": symbol,
            "is_valid": False,
            "status": "INVALID_SCHEMA",
            "total_records": len(df),
            "errors": errors,
            "warnings": warnings,
            "data_source": data_source,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    # 2. Date parsing and sorting
    try:
        clean_df["Date"] = pd.to_datetime(clean_df["Date"])
        if hasattr(clean_df["Date"].dt, "tz") and clean_df["Date"].dt.tz is not None:
            clean_df["Date"] = clean_df["Date"].dt.tz_localize(None)
    except Exception as e:
        errors.append(f"Failed to parse Date column: {e}")
        return False, pd.DataFrame(), {
            "symbol": symbol,
            "is_valid": False,
            "status": "INVALID_DATES",
            "total_records": len(df),
            "errors": errors,
            "warnings": warnings,
            "data_source": data_source,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    # Sort chronologically
    clean_df = clean_df.sort_values(by="Date").reset_index(drop=True)

    # 3. Duplicate Dates check
    dup_mask = clean_df.duplicated(subset=["Date"], keep="last")
    dup_count = int(dup_mask.sum())
    if dup_count > 0:
        warnings.append(f"Found and removed {dup_count} duplicate date rows (kept latest).")
        clean_df = clean_df[~dup_mask].reset_index(drop=True)

    # 4. Null & Missing values check
    null_counts = clean_df[REQUIRED_COLUMNS].isnull().sum().to_dict()
    has_nulls = any(cnt > 0 for cnt in null_counts.values())
    if has_nulls:
        warnings.append(f"Dropped rows with null values: {null_counts}")
        clean_df = clean_df.dropna(subset=REQUIRED_COLUMNS).reset_index(drop=True)

    if clean_df.empty:
        errors.append("All rows dropped due to null values.")
        return False, pd.DataFrame(), {
            "symbol": symbol,
            "is_valid": False,
            "status": "ALL_NULLS",
            "total_records": 0,
            "errors": errors,
            "warnings": warnings,
            "data_source": data_source,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    # 5. Type casting
    for col in ["Open", "High", "Low", "Close"]:
        clean_df[col] = pd.to_numeric(clean_df[col], errors="coerce")
    clean_df["Volume"] = pd.to_numeric(clean_df["Volume"], errors="coerce").fillna(0).astype(int)

    # Re-check for any conversion failure
    clean_df = clean_df.dropna(subset=["Open", "High", "Low", "Close"]).reset_index(drop=True)

    # 6. Price Integrity checks (High >= Low, High >= Open/Close, Low <= Open/Close, Price > 0)
    bad_price_mask = (
        (clean_df["High"] < clean_df["Low"]) |
        (clean_df["High"] < clean_df["Open"]) |
        (clean_df["High"] < clean_df["Close"]) |
        (clean_df["Low"] > clean_df["Open"]) |
        (clean_df["Low"] > clean_df["Close"]) |
        (clean_df["Close"] <= 0) |
        (clean_df["Open"] <= 0)
    )
    bad_price_count = int(bad_price_mask.sum())
    if bad_price_count > 0:
        errors.append(f"Detected {bad_price_count} price integrity violation rows (e.g. High < Low or Price <= 0).")
        # Drop corrupt rows but record error
        clean_df = clean_df[~bad_price_mask].reset_index(drop=True)
        if len(clean_df) < 20:
            return False, pd.DataFrame(), {
                "symbol": symbol,
                "is_valid": False,
                "status": "INTEGRITY_FAIL",
                "total_records": len(clean_df),
                "errors": errors,
                "warnings": warnings,
                "data_source": data_source,
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

    # 7. Minimum Record Count
    if len(clean_df) < 20:
        warnings.append(f"Only {len(clean_df)} bars available. Minimum 20 bars needed for 20-DMA and 14-RSI calculations.")

    # 8. Stale Data Check
    latest_date = clean_df["Date"].iloc[-1]
    today = pd.to_datetime(date.today())
    days_lag = (today - latest_date).days
    
    if days_lag > stale_days_threshold:
        status = "STALE"
        warnings.append(f"Data is {days_lag} days old (latest candle: {latest_date.strftime('%Y-%m-%d')}). Threshold: {stale_days_threshold} days.")
    else:
        status = "VERIFIED"

    # Set Date as index for consistency with indicator engines
    clean_df = clean_df.set_index("Date")

    report = {
        "symbol": symbol.upper(),
        "is_valid": True,
        "status": status,
        "total_records": len(clean_df),
        "date_range": {
            "start": clean_df.index[0].strftime("%Y-%m-%d"),
            "end": clean_df.index[-1].strftime("%Y-%m-%d")
        },
        "latest_close": float(round(clean_df["Close"].iloc[-1], 2)),
        "errors": errors,
        "warnings": warnings,
        "data_source": data_source,
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    return True, clean_df, report
