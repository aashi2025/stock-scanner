from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import logging

from backend.app.database import engine, Base
from backend.app.api import (
    market_router,
    scan_router,
    stocks_router,
    watchlist_router,
    filters_router,
    backtest_router,
    alerts_router,
    alerts_router,
    settings_router,
    upstox_router
)

# Configure Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("StockConfirmationScanner")

# Initialize DB tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Stock Confirmation Scanner API",
    description="Rule-based multi-stage Indian Stock Market (NSE/BSE) Confirmation Scanner with Upstox API",
    version="2.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(upstox_router)
app.include_router(market_router)
app.include_router(scan_router)
app.include_router(stocks_router)
app.include_router(watchlist_router)
app.include_router(filters_router)
app.include_router(backtest_router)
app.include_router(alerts_router)
app.include_router(settings_router)


# Mount Static Files for Single Page Frontend Application
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)

app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def serve_index():
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {
        "status": "online",
        "app": "Stock Confirmation Scanner",
        "message": "Frontend index.html is being prepared. Access API documentation at /docs"
    }

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "Stock Confirmation Scanner Backend"}
