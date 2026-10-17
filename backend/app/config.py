import os
import dotenv

dotenv.load_dotenv()

class Settings:
    MARKET_DATA_PROVIDER: str = os.getenv("MARKET_DATA_PROVIDER", "upstox")
    UPSTOX_ACCESS_TOKEN: str = os.getenv("UPSTOX_ACCESS_TOKEN", "").strip("'\"")
    UPSTOX_API_KEY: str = os.getenv("UPSTOX_API_KEY", "").strip("'\"")
    UPSTOX_API_SECRET: str = os.getenv("UPSTOX_API_SECRET", "").strip("'\"")
    UPSTOX_REDIRECT_URI: str = os.getenv("UPSTOX_REDIRECT_URI", "http://localhost:8000/api/upstox/callback").strip("'\"")

    MARKET_API_KEY: str = os.getenv("MARKET_API_KEY", "")
    MARKET_API_SECRET: str = os.getenv("MARKET_API_SECRET", "")
    MARKET_API_BASE_URL: str = os.getenv("MARKET_API_BASE_URL", "https://api.upstox.com/v2")
    ALLOW_SAMPLE_MODE: bool = os.getenv("ALLOW_SAMPLE_MODE", "false").lower() == "true"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./stock_scanner.db")
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    ENV: str = os.getenv("ENV", "development")
    
    DEFAULT_SECTOR_SCORE_MIN: float = float(os.getenv("DEFAULT_SECTOR_SCORE_MIN", "60.0"))
    DEFAULT_CONFIRMATION_SCORE_MIN: float = float(os.getenv("DEFAULT_CONFIRMATION_SCORE_MIN", "65.0"))
    DEFAULT_UNIVERSE: str = os.getenv("DEFAULT_UNIVERSE", "NIFTY 50")

settings = Settings()

