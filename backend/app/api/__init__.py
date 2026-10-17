from backend.app.api.market import router as market_router
from backend.app.api.scan import router as scan_router
from backend.app.api.stocks import router as stocks_router
from backend.app.api.watchlist import router as watchlist_router
from backend.app.api.filters import router as filters_router
from backend.app.api.backtest import router as backtest_router
from backend.app.api.alerts import router as alerts_router
from backend.app.api.settings import router as settings_router
from backend.app.api.upstox_auth import router as upstox_router

__all__ = [
    "market_router",
    "scan_router",
    "stocks_router",
    "watchlist_router",
    "filters_router",
    "backtest_router",
    "alerts_router",
    "settings_router",
    "upstox_router"
]

