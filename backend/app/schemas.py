from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class StockQuote(BaseModel):
    symbol: str
    company_name: str
    exchange: str = "NSE"
    sector: str
    price: float
    change: float
    change_percent: float
    volume: int
    avg_volume_20d: int
    market_cap: Optional[float] = None
    timestamp: str
    data_source: str
    is_sample_data: bool = False

class TechnicalIndicators(BaseModel):
    symbol: str
    price: float
    sma_50: float
    sma_200: float
    rsi_14: float
    volume: int
    avg_volume_20d: int
    vol_ratio: float
    rs_vs_nifty_20d: float
    atr_14: float
    sma_50_above_200: bool
    price_above_50: bool
    price_above_200: bool

class RuleResult(BaseModel):
    rule_name: str
    description: str
    points_awarded: float
    max_points: float
    passed: bool
    detail: str

class ConfirmationBreakdown(BaseModel):
    symbol: str
    company_name: str
    sector: str
    price: float
    change_percent: float
    confirmation_score: float
    classification: str # Strong Setup, Confirmed Setup, Watchlist, Not Confirmed
    passed_rules: List[RuleResult]
    failed_rules: List[RuleResult]
    why_passed: List[str]
    why_failed_100: List[str]
    invalidation_triggers: List[str]
    reference_levels: Dict[str, Any] # entry, stop, target, risk_reward
    rule_explanation: str

class MarketTrendResult(BaseModel):
    nifty_price: float
    nifty_sma_50: float
    nifty_sma_200: float
    nifty_rsi: float
    market_breadth_pct: float
    market_score: float
    classification: str # Strong Bullish, Bullish, Neutral, Bearish, Strong Bearish
    breakdown: List[RuleResult]
    timestamp: str
    data_source: str
    is_sample_data: bool = False

class SectorTrendItem(BaseModel):
    sector_name: str
    index_symbol: str
    price: float
    sma_50: float
    sma_200: float
    rsi: float
    rs_vs_nifty: float
    sector_score: float
    trend: str # Bullish, Neutral, Bearish
    qualifying_stocks_count: int = 0

class ScanFilterParams(BaseModel):
    universe: str = "NIFTY 50"
    min_sector_score: float = 60.0
    min_confirmation_score: float = 65.0
    filter_trend: bool = True
    filter_momentum: bool = True
    filter_volume: bool = True
    filter_relative_strength: bool = True
    filter_sector: bool = True
    min_volume_ratio: float = 1.0
    rsi_max_exhaustion: float = 75.0
    custom_filter_id: Optional[int] = None
    use_sample_mode: bool = False

class ScanResult(BaseModel):
    scan_time: str
    data_source: str
    is_sample_data: bool
    total_stocks_scanned: int
    market_trend: MarketTrendResult
    sector_trends: List[SectorTrendItem]
    confirmed_setups: List[ConfirmationBreakdown]
    watchlist_setups: List[ConfirmationBreakdown]
    not_confirmed_count: int

class BacktestRequest(BaseModel):
    universe: str = "NIFTY 50"
    start_date: str = "2023-01-01"
    end_date: str = "2024-09-30"
    timeframe: str = "1d"
    min_confirmation_score: float = 75.0
    min_sector_score: float = 60.0
    stop_loss_pct: float = 5.0
    target_pct: float = 10.0
    position_size_pct: float = 10.0
    slippage_pct: float = 0.2

class TradeLogItem(BaseModel):
    symbol: str
    entry_date: str
    entry_price: float
    exit_date: str
    exit_price: float
    return_pct: float
    pnl_amount: float
    holding_days: int
    exit_reason: str # Target, Stop Loss, Signal Invalidated, End of Period
    confirmation_score_at_entry: float

class BacktestResult(BaseModel):
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    avg_return_pct: float
    total_return_pct: float
    cagr_pct: float
    max_drawdown_pct: float
    profit_factor: float
    avg_holding_days: float
    trades: List[TradeLogItem]
    disclaimer: str = "BACKTEST RESULT (Historical rule performance, not a guarantee of live market results)"

class WatchlistItemSchema(BaseModel):
    id: Optional[int] = None
    symbol: str
    company_name: str
    sector: str
    added_at: Optional[datetime] = None
    initial_score: float = 0.0
    current_score: float = 0.0
    previous_score: float = 0.0
    score_change: float = 0.0
    status: str = "HOLDING SETUP STATUS"
    notes: Optional[str] = None

class CustomFilterSchema(BaseModel):
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    rules_json: str
    created_at: Optional[datetime] = None

class AppSettingsSchema(BaseModel):
    provider: str
    api_key: Optional[str] = ""
    api_secret: Optional[str] = ""
    base_url: Optional[str] = ""
    sample_mode: bool
    min_sector_score: float
    min_confirmation_score: float
    is_configured: bool
    active_data_source: str
