from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models import AppSettingModel
from backend.app.config import settings
from backend.app.schemas import AppSettingsSchema
from datetime import datetime

router = APIRouter(prefix="/api/settings", tags=["Admin & Settings"])

@router.get("/", response_model=AppSettingsSchema)
def get_app_settings(db: Session = Depends(get_db)):
    db_setting = db.query(AppSettingModel).first()
    
    if not db_setting:
        db_setting = AppSettingModel(
            provider=settings.MARKET_DATA_PROVIDER,
            api_key=settings.MARKET_API_KEY,
            api_secret=settings.MARKET_API_SECRET,
            base_url=settings.MARKET_API_BASE_URL,
            sample_mode=False, # Default sample mode false to follow real-data directive unless explicitly toggled
            min_sector_score=settings.DEFAULT_SECTOR_SCORE_MIN,
            min_confirmation_score=settings.DEFAULT_CONFIRMATION_SCORE_MIN
        )
        db.add(db_setting)
        db.commit()
        db.refresh(db_setting)

    # API key masking for frontend security (Requirement #2 & #18)
    masked_key = (db_setting.api_key[:3] + "********" + db_setting.api_key[-3:]) if len(db_setting.api_key) > 6 else ("********" if db_setting.api_key else "")
    
    is_conf = bool(db_setting.provider in ["yahoo", "yfinance", "nse"] or (db_setting.api_key and db_setting.api_secret))

    active_source = "EXPLICIT SAMPLE DATA MODE" if db_setting.sample_mode else (
        "NSE (Yahoo Finance Real Market Data API)" if db_setting.provider == "yahoo" else f"{db_setting.provider.title()} Broker API"
    )

    return AppSettingsSchema(
        provider=db_setting.provider,
        api_key=masked_key,
        api_secret="********" if db_setting.api_secret else "",
        base_url=db_setting.base_url,
        sample_mode=db_setting.sample_mode,
        min_sector_score=db_setting.min_sector_score,
        min_confirmation_score=db_setting.min_confirmation_score,
        is_configured=is_conf,
        active_data_source=active_source
    )

@router.post("/update", response_model=AppSettingsSchema)
def update_app_settings(
    provider: str = Body("yahoo"),
    api_key: str = Body(None),
    api_secret: str = Body(None),
    base_url: str = Body(None),
    sample_mode: bool = Body(False),
    min_sector_score: float = Body(60.0),
    min_confirmation_score: float = Body(65.0),
    db: Session = Depends(get_db)
):
    db_setting = db.query(AppSettingModel).first()
    if not db_setting:
        db_setting = AppSettingModel()
        db.add(db_setting)

    db_setting.provider = provider
    if api_key and not api_key.startswith("****"):
        db_setting.api_key = api_key
    if api_secret and not api_secret.startswith("****"):
        db_setting.api_secret = api_secret
    if base_url:
        db_setting.base_url = base_url

    db_setting.sample_mode = sample_mode
    db_setting.min_sector_score = min_sector_score
    db_setting.min_confirmation_score = min_confirmation_score
    db_setting.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(db_setting)

    return get_app_settings(db)
