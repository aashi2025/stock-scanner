"""
Ranking and Risk Scoring Engine.
Transparent, rule-based quantitative scoring across 5 separate dimensions:
1. Trend Score
2. Momentum Score
3. Fundamental Quality Score
4. Valuation Score
5. Risk Score

Weights are completely configurable.
Scores are quantitative research heuristics, NEVER guaranteed predictions.
"""

from typing import Dict, Any, Optional, Tuple, List
import pandas as pd
import numpy as np

Tuple_Score = Tuple[float, List[str]]

HEURISTIC_DISCLAIMER = (
    "RESEARCH HEURISTICS DISCLAIMER: The Trend, Momentum, Quality, Valuation, "
    "and Risk scores are rule-based quantitative models intended solely for educational "
    "and research purposes. They do not constitute investment advice, financial planning, "
    "or guaranteed price predictions."
)

DEFAULT_WEIGHTS = {
    "trend": 0.30,
    "momentum": 0.30,
    "fundamental": 0.20,
    "valuation": 0.10,
    "safety": 0.10
}


def calculate_trend_score(ind: Dict[str, Any]) -> Tuple_Score:
    """
    Evaluates Trend Strength (0 - 100).
    Price > EMA50 (25), Price > EMA200 (25), EMA50 > EMA200 (30), Near 52W High (20).
    """
    score = 0.0
    details = []

    price = float(ind.get("price", 0.0))
    ema_50 = float(ind.get("ema_50", 0.0))
    ema_200 = float(ind.get("ema_200", 0.0))
    dist_52w = float(ind.get("dist_from_52w_high_pct", 100.0))

    if price > ema_50 and ema_50 > 0:
        score += 25.0
        details.append("Price > 50 EMA (+25)")
    else:
        details.append("Price <= 50 EMA (0)")

    if price > ema_200 and ema_200 > 0:
        score += 25.0
        details.append("Price > 200 EMA (+25)")
    else:
        details.append("Price <= 200 EMA (0)")

    if ema_50 > ema_200 and ema_200 > 0:
        score += 30.0
        details.append("50 EMA > 200 EMA Golden Alignment (+30)")
    else:
        details.append("50 EMA <= 200 EMA (0)")

    if dist_52w <= 10.0:
        score += 20.0
        details.append(f"Within 10% of 52W High ({dist_52w}%) (+20)")
    elif dist_52w <= 20.0:
        score += 10.0
        details.append(f"Within 20% of 52W High ({dist_52w}%) (+10)")
    else:
        details.append(f"Lags >20% below 52W High ({dist_52w}%) (0)")

    return round(score, 1), details


def calculate_momentum_score(ind: Dict[str, Any]) -> Tuple_Score:
    """
    Evaluates Momentum & Breakout Quality (0 - 100).
    RSI Sweet Spot (35), Fresh Crossover (25), Volume Ratio (20), RS vs Nifty (20).
    """
    score = 0.0
    details = []

    rsi = float(ind.get("rsi_14", 50.0))
    is_fresh = bool(ind.get("rsi_fresh_crossover", False))
    vol_ratio = float(ind.get("vol_ratio", 1.0))
    rs_20d = float(ind.get("rs_vs_nifty_20d", 0.0))

    # RSI regime
    if 50.0 <= rsi <= 70.0:
        score += 35.0
        details.append(f"RSI {rsi} in prime bullish acceleration zone (+35)")
    elif 70.0 < rsi <= 75.0:
        score += 20.0
        details.append(f"RSI {rsi} bullish but approaching overbought (+20)")
    elif rsi > 75.0:
        score += 5.0
        details.append(f"RSI {rsi} extended / overbought exhaustion (+5)")
    else:
        details.append(f"RSI {rsi} below 50 bearish momentum (0)")

    # Fresh crossover
    if is_fresh:
        score += 25.0
        details.append("⚡ Fresh RSI(14) crossover above 50 triggered on completed candle (+25)")
    elif rsi > 50:
        score += 10.0
        details.append("RSI above 50 (continuation, not fresh) (+10)")

    # Volume Surge
    if vol_ratio >= 2.0:
        score += 20.0
        details.append(f"Volume Surge {vol_ratio}x >= 2.0x 20-DMA (+20)")
    elif vol_ratio >= 1.2:
        score += 15.0
        details.append(f"Volume Breakout {vol_ratio}x >= 1.2x 20-DMA (+15)")
    else:
        details.append(f"Volume {vol_ratio}x < 1.2x 20-DMA (0)")

    # Relative Strength
    if rs_20d > 5.0:
        score += 20.0
        details.append(f"Strong outperformance vs NIFTY (+{rs_20d}%) (+20)")
    elif rs_20d > 0.0:
        score += 10.0
        details.append(f"Outperforming NIFTY (+{rs_20d}%) (+10)")
    else:
        details.append(f"Underperforming NIFTY ({rs_20d}%) (0)")

    return round(score, 1), details


def calculate_fundamental_score(fund: Dict[str, Any], sector: str = "General") -> Tuple[Optional[float], List[str], bool]:
    """
    Evaluates Fundamental Quality (0 - 100).
    Never fabricates figures. If unavailable, returns None and data_available=False.
    """
    if not fund or not fund.get("is_verified", False):
        return None, ["Fundamental data unavailable on disk. (Verify via Screener.in)"], False

    score = 0.0
    details = []
    is_fin = any(k in sector.upper() for k in ["BANK", "FINANCIAL", "NBFC"])

    roce = fund.get("roce")
    roe = fund.get("roe")
    de = fund.get("debt_to_equity")
    sales_g = fund.get("sales_growth_3y")
    profit_g = fund.get("profit_growth_3y")

    # ROCE
    if roce is not None:
        if roce >= 20.0:
            score += 25.0
            details.append(f"Exceptional ROCE {roce}% >= 20% (+25)")
        elif roce >= 15.0:
            score += 18.0
            details.append(f"Solid ROCE {roce}% >= 15% (+18)")
        elif roce >= 10.0:
            score += 10.0
            details.append(f"Moderate ROCE {roce}% (+10)")
        else:
            details.append(f"Low ROCE {roce}% (<10%) (0)")

    # ROE
    if roe is not None:
        if roe >= 18.0:
            score += 25.0
            details.append(f"Strong ROE {roe}% >= 18% (+25)")
        elif roe >= 12.0:
            score += 18.0
            details.append(f"Good ROE {roe}% >= 12% (+18)")
        else:
            details.append(f"Subdued ROE {roe}% (0)")

    # Debt / Equity
    if is_fin:
        score += 25.0
        details.append("Financial/Bank: Evaluated via regulatory capital ratios (+25)")
    elif de is not None:
        if de <= 0.3:
            score += 25.0
            details.append(f"Virtually Debt Free: D/E {de} <= 0.3 (+25)")
        elif de <= 0.8:
            score += 18.0
            details.append(f"Manageable Debt: D/E {de} <= 0.8 (+18)")
        elif de <= 1.2:
            score += 10.0
            details.append(f"Moderate Leverage: D/E {de} (+10)")
        else:
            details.append(f"High Debt: D/E {de} > 1.2 (0)")

    # Growth
    if sales_g is not None and profit_g is not None:
        if sales_g >= 12.0 and profit_g >= 12.0:
            score += 25.0
            details.append(f"High Growth: Sales +{sales_g}%, Profit +{profit_g}% (+25)")
        elif sales_g > 5.0 and profit_g > 5.0:
            score += 15.0
            details.append(f"Steady Growth: Sales +{sales_g}%, Profit +{profit_g}% (+15)")
        else:
            details.append(f"Weak/Negative Growth (0)")

    return round(score, 1), details, True


def calculate_valuation_score(fund: Dict[str, Any]) -> Tuple[Optional[float], List[str], bool]:
    """
    Evaluates Valuation attractiveness (0 - 100).
    Never fabricates missing valuation ratios.
    """
    if not fund or not fund.get("is_verified", False):
        return None, ["Valuation ratios unavailable. Not fabricated."], False

    pe = fund.get("pe_ratio")
    pb = fund.get("pb_ratio")
    cf = fund.get("cash_flow_operating")

    if pe is None and pb is None:
        return None, ["PE and PB not available for symbol."], False

    score = 0.0
    details = []

    if pe is not None and pe > 0:
        if 12.0 <= pe <= 28.0:
            score += 40.0
            details.append(f"Attractive P/E: {pe} (12-28 range) (+40)")
        elif pe < 12.0:
            score += 30.0
            details.append(f"Low P/E: {pe} (potential value or cyclical) (+30)")
        elif pe <= 45.0:
            score += 20.0
            details.append(f"Growth Premium P/E: {pe} (+20)")
        else:
            details.append(f"Elevated P/E: {pe} > 45 (0)")

    if pb is not None and pb > 0:
        if pb <= 3.5:
            score += 30.0
            details.append(f"Reasonable P/B: {pb} <= 3.5 (+30)")
        elif pb <= 6.0:
            score += 15.0
            details.append(f"Moderate P/B: {pb} (+15)")
        else:
            details.append(f"High P/B: {pb} (0)")

    if cf is not None:
        if cf > 0:
            score += 30.0
            details.append("Positive Operating Cash Flow (+30)")
        else:
            details.append("Negative Operating Cash Flow (0)")
    else:
        # Default neutral for missing cash flow
        score += 15.0

    return round(min(100.0, score), 1), details, True


def calculate_risk_score(ind: Dict[str, Any], fund: Optional[Dict[str, Any]] = None) -> Tuple_Score:
    """
    Evaluates Risk Level (0 - 100).
    Higher Risk Score = HIGHER DANGER.
    Safety Score = 100 - Risk Score.
    """
    risk_pts = 0.0
    details = []

    price = float(ind.get("price", 0.0))
    rsi = float(ind.get("rsi_14", 50.0))
    dist_52w = float(ind.get("dist_from_52w_high_pct", 0.0))
    atr = float(ind.get("atr_14", 0.0))

    # Overbought Risk
    if rsi >= 80.0:
        risk_pts += 30.0
        details.append(f"Extreme Overbought RSI ({rsi} >= 80): High pullback risk (+30 risk)")
    elif rsi >= 75.0:
        risk_pts += 15.0
        details.append(f"Elevated RSI ({rsi}): Caution on breakout (+15 risk)")

    # Deep Drawdown Risk
    if dist_52w >= 35.0:
        risk_pts += 30.0
        details.append(f"Deep Downtrend ({dist_52w}% below 52W high): Structural weakness (+30 risk)")
    elif dist_52w >= 25.0:
        risk_pts += 15.0
        details.append(f"Significant lag ({dist_52w}% below 52W high) (+15 risk)")

    # Volatility / ATR risk
    if price > 0:
        atr_pct = (atr / price) * 100
        if atr_pct >= 4.0:
            risk_pts += 25.0
            details.append(f"High Volatility (Daily ATR {round(atr_pct, 1)}% of price) (+25 risk)")
        elif atr_pct >= 2.5:
            risk_pts += 10.0
            details.append(f"Moderate Volatility (Daily ATR {round(atr_pct, 1)}%) (+10 risk)")

    # Fundamental leverage risk
    if fund and fund.get("is_verified", False):
        de = fund.get("debt_to_equity")
        if de is not None and de > 1.5:
            risk_pts += 25.0
            details.append(f"High Financial Leverage (D/E {de} > 1.5) (+25 risk)")

    risk_pts = min(100.0, risk_pts)
    return round(risk_pts, 1), details


Tuple_Score = Tuple[float, List[str]]


def compute_composite_ranking(
    ind: Dict[str, Any],
    fund: Optional[Dict[str, Any]] = None,
    sector: str = "General",
    custom_weights: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Computes all 5 scores and blends them into a final research score.
    Dynamically adjusts if fundamental/valuation data is unavailable.
    """
    weights = dict(DEFAULT_WEIGHTS)
    if custom_weights:
        weights.update(custom_weights)

    trend_score, trend_details = calculate_trend_score(ind)
    mom_score, mom_details = calculate_momentum_score(ind)
    fund_score, fund_details, has_fund = calculate_fundamental_score(fund or {}, sector)
    val_score, val_details, has_val = calculate_valuation_score(fund or {})
    risk_score, risk_details = calculate_risk_score(ind, fund)

    safety_score = round(max(0.0, 100.0 - risk_score), 1)

    # Dynamic Weight Rebalancing if Fundamentals/Valuation missing
    active_weights = {}
    active_weights["trend"] = weights["trend"]
    active_weights["momentum"] = weights["momentum"]
    active_weights["safety"] = weights["safety"]

    if has_fund and fund_score is not None:
        active_weights["fundamental"] = weights["fundamental"]
    if has_val and val_score is not None:
        active_weights["valuation"] = weights["valuation"]

    total_w = sum(active_weights.values())
    norm_w = {k: v / total_w for k, v in active_weights.items()}

    composite = (
        trend_score * norm_w["trend"] +
        mom_score * norm_w["momentum"] +
        safety_score * norm_w["safety"]
    )
    if has_fund and fund_score is not None:
        composite += fund_score * norm_w["fundamental"]
    if has_val and val_score is not None:
        composite += val_score * norm_w["valuation"]

    composite = round(composite, 1)

    return {
        "composite_score": composite,
        "trend_score": trend_score,
        "momentum_score": mom_score,
        "fundamental_score": fund_score,
        "valuation_score": val_score,
        "risk_score": risk_score,
        "safety_score": safety_score,
        "has_fundamental_data": has_fund,
        "has_valuation_data": has_val,
        "weights_used": norm_w,
        "breakdown": {
            "trend": trend_details,
            "momentum": mom_details,
            "fundamental": fund_details,
            "valuation": val_details,
            "risk": risk_details
        },
        "disclaimer": HEURISTIC_DISCLAIMER
    }
