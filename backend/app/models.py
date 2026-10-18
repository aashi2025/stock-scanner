from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text
from datetime import datetime
from backend.app.database import Base

class WatchlistItem(Base):
    __tablename__ = "watchlist"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True, nullable=False)
    company_name = Column(String, nullable=False)
    sector = Column(String, nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow)
    initial_score = Column(Float, default=0.0)
    current_score = Column(Float, default=0.0)
    previous_score = Column(Float, default=0.0)
    status = Column(String, default="HOLDING SETUP STATUS") # HOLDING SETUP STATUS, SETUP WEAKENING, SETUP INVALIDATED
    notes = Column(Text, nullable=True)

class CustomFilter(Base):
    __tablename__ = "custom_filters"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=True)
    rules_json = Column(Text, nullable=False) # JSON array of rule definitions
    created_at = Column(DateTime, default=datetime.utcnow)

class ScanSnapshot(Base):
    __tablename__ = "scan_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    scan_date = Column(String, nullable=False)
    universe = Column(String, nullable=False)
    market_score = Column(Float, nullable=False)
    sector_scores_json = Column(Text, nullable=False)
    stock_results_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class AlertRule(Base):
    __tablename__ = "alert_rules"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    trigger_type = Column(String, nullable=False) # score_above, setup_confirmed, sector_bullish, setup_invalidated
    threshold = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_triggered = Column(DateTime, nullable=True)

class AppSettingModel(Base):
    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String, default="yahoo")
    api_key = Column(String, default="")
    api_secret = Column(String, default="")
    base_url = Column(String, default="")
    sample_mode = Column(Boolean, default=False)
    min_sector_score = Column(Float, default=60.0)
    min_confirmation_score = Column(Float, default=65.0)
    updated_at = Column(DateTime, default=datetime.utcnow)


class TradeJournalModel(Base):
    """
    Trade Journal persistence model.
    Stores both planned research setups and user-confirmed real executions.
    Strictly distinguishes theoretical signals from actual trades.
    """
    __tablename__ = "trade_journal"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    strategy_name = Column(String, index=True, nullable=False)
    timeframe = Column(String, default="1d") # 5m, 15m, 1d, 1w
    bias = Column(String, default="BULLISH") # BULLISH, BEARISH
    planned_entry = Column(Float, nullable=False)
    planned_stop_loss = Column(Float, nullable=False)
    planned_target = Column(Float, nullable=False)
    planned_quantity = Column(Integer, default=1)
    planned_risk = Column(Float, default=0.0)
    estimated_charges = Column(Float, default=0.0)
    
    # Real execution tracking (Supplied by user only)
    is_user_executed = Column(Boolean, default=False)
    actual_entry = Column(Float, nullable=True)
    actual_exit = Column(Float, nullable=True)
    actual_pnl = Column(Float, nullable=True)
    status = Column(String, default="PLANNED") # PLANNED, EXECUTED_OPEN, CLOSED_PROFIT, CLOSED_LOSS, CANCELLED
    
    tags = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AlertHistoryModel(Base):
    """
    Alert History persistence model.
    Records every alert generated, deduplication state, and Telegram dispatch logs.
    """
    __tablename__ = "alert_history"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    strategy_name = Column(String, index=True, nullable=False)
    bias = Column(String, default="BULLISH")
    timeframe = Column(String, default="1d")
    trigger_level = Column(Float, nullable=True)
    invalidation_level = Column(Float, nullable=True)
    risk_reward = Column(String, default="1:2.0")
    status = Column(String, default="NEW") # NEW, CONFIRMED, INVALIDATED, EXPIRED
    message_text = Column(Text, nullable=False)
    is_telegram_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
