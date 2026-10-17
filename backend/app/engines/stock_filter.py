from typing import Dict, Any, List, Tuple
import pandas as pd
from backend.app.schemas import ScanFilterParams
from backend.app.indicators.calculations import compute_all_indicators

def apply_stock_filters(
    stock_df: pd.DataFrame,
    nifty_df: pd.DataFrame,
    sector_score: float,
    stock_mcap: float,
    params: ScanFilterParams
) -> Tuple[bool, List[str]]:
    """
    Stock Filter Engine.
    Filters individual stocks based on user-configured technical, volume, sector, and market cap criteria.
    All filters are toggleable ON/OFF via ScanFilterParams.
    """
    if stock_df.empty or len(stock_df) < 10:
        return False, ["Insufficient data"]

    ind = compute_all_indicators(stock_df, nifty_df)
    price = ind["price"]
    sma_50 = ind["sma_50"]
    sma_200 = ind["sma_200"]
    rsi = ind["rsi_14"]
    vol_ratio = ind["vol_ratio"]
    rs_20 = ind["rs_vs_nifty_20d"]

    reasons_failed = []

    # A. Trend Filter
    if params.filter_trend:
        if not (price > sma_50 and price > sma_200 and sma_50 > sma_200):
            reasons_failed.append("Trend filter failed (Close must be > 50 DMA, > 200 DMA, and 50 DMA > 200 DMA)")

    # B. Momentum Filter
    if params.filter_momentum:
        if rsi <= 50.0:
            reasons_failed.append(f"RSI momentum filter failed ({rsi} <= 50.0)")
        elif rsi > params.rsi_max_exhaustion:
            reasons_failed.append(f"RSI overbought exhaustion filter failed ({rsi} > {params.rsi_max_exhaustion})")

    # C. Volume Filter
    if params.filter_volume:
        if vol_ratio < params.min_volume_ratio:
            reasons_failed.append(f"Volume surge filter failed ({vol_ratio}x < {params.min_volume_ratio}x 20D average)")

    # D. Relative Strength Filter
    if params.filter_relative_strength:
        if rs_20 <= 0.0:
            reasons_failed.append(f"Relative Strength filter failed ({rs_20}% vs NIFTY <= 0%)")

    # E. Sector Filter
    if params.filter_sector:
        if sector_score < params.min_sector_score:
            reasons_failed.append(f"Sector score filter failed ({sector_score} < {params.min_sector_score})")

    passed = (len(reasons_failed) == 0)
    return passed, reasons_failed
