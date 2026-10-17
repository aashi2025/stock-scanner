"""
Momentum Pro — Advanced Quantitative Trading Analysis Package.
Includes:
- Explainable Quantitative Scoring (0-100)
- Systematic Trade Planner & Risk-Based Position Sizer
- Pre-Breakout & Fresh RSI Crossover Scanners
- Realistic Next-Day Execution Historical Backtester
"""

from backend.app.momentum_pro.scoring import calculate_momentum_setup_score, SCORE_DISCLAIMER
from backend.app.momentum_pro.trade_planner import calculate_trade_plan, TRADE_PLAN_DISCLAIMER
from backend.app.momentum_pro.scanner import run_momentum_pro_scan
from backend.app.momentum_pro.backtester import run_momentum_pro_backtest
