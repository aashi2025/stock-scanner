from fastapi import APIRouter, Body, Query
from backend.app.schemas import BacktestRequest, BacktestResult
from backend.app.data_providers.factory import get_market_data_provider
from backend.app.engines.backtest import run_backtest

router = APIRouter(prefix="/api/backtest", tags=["Backtesting Module"])

@router.post("/run", response_model=BacktestResult)
def execute_backtest(
    req: BacktestRequest = Body(...),
    use_sample_mode: bool = Query(False)
):
    provider = get_market_data_provider(force_sample=use_sample_mode)
    res = run_backtest(provider, req)
    return res
