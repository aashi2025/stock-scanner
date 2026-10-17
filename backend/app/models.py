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
