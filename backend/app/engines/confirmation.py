from typing import Dict, Any, List
import pandas as pd
from backend.app.indicators.calculations import compute_all_indicators

def calculate_confirmation_score(
    stock: Dict[str, Any],
    stock_df: pd.DataFrame,
    nifty_df: pd.DataFrame,
    sector_scores_map: Dict[str, float],
    market_score: float
) -> Dict[str, Any]:
    """
    Confirmation Engine.
    Computes a rule-based confirmation score (0-100) and produces a complete,
    transparent explanation of why the stock passed or failed each rule.
    Strictly native Python primitives for JSON serialization safety.
    """
    symbol = str(stock["symbol"])
    company_name = str(stock.get("name", symbol))
    sector = str(stock.get("sector", "General"))

    if stock_df.empty or len(stock_df) < 10:
        return {
            "symbol": symbol,
            "company_name": company_name,
            "sector": sector,
            "price": 0.0,
            "change_percent": 0.0,
            "confirmation_score": 0.0,
            "classification": "Not Confirmed",
            "passed_rules": [],
            "failed_rules": [],
            "why_passed": [],
            "why_failed_100": ["Insufficient price history for technical analysis"],
            "invalidation_triggers": ["Data unavailable"],
            "reference_levels": {},
            "rule_explanation": "Insufficient historical data available to verify setup rules."
        }

    ind = compute_all_indicators(stock_df, nifty_df)
    price = float(ind["price"])
    sma_50 = float(ind["sma_50"])
    sma_200 = float(ind["sma_200"])
    rsi = float(ind["rsi_14"])
    vol_ratio = float(ind["vol_ratio"])
    rs_20 = float(ind["rs_vs_nifty_20d"])
    atr = float(ind["atr_14"])
    price_above_50 = bool(ind["price_above_50"])
    price_above_200 = bool(ind["price_above_200"])
    dma_cross = bool(ind["sma_50_above_200"])

    sector_score = float(sector_scores_map.get(sector.upper(), sector_scores_map.get("GENERAL", 60.0)))

    # Calculate 20-day high for breakout check
    high_20d = float(stock_df['High'].tail(20).max()) if 'High' in stock_df.columns else price
    is_breakout = bool(price >= (high_20d * 0.98))

    passed_rules = []
    failed_rules = []
    why_passed = []
    why_failed_100 = []
    invalidation_triggers = []

    total_score = 0.0

    # 1. TREND CONFIRMATION (Max 20 pts)
    trend_pts = 0.0
    if price_above_50: trend_pts += 7.0
    if price_above_200: trend_pts += 7.0
    if dma_cross: trend_pts += 6.0

    total_score += trend_pts
    trend_passed = bool(trend_pts >= 14.0)
    rule_item = {
        "rule_name": "Trend Confirmation",
        "description": "Stock price above 50 DMA, 200 DMA, and 50 DMA > 200 DMA",
        "points_awarded": float(trend_pts),
        "max_points": 20.0,
        "passed": trend_passed,
        "detail": f"Close: ₹{price} | 50 DMA: ₹{sma_50} | 200 DMA: ₹{sma_200}"
    }
    if trend_passed:
        passed_rules.append(rule_item)
        why_passed.append(f"Strong uptrend structure (Close ₹{price} > 50 DMA ₹{sma_50} & 200 DMA ₹{sma_200})")
    else:
        failed_rules.append(rule_item)
        why_failed_100.append(f"Trend structure not fully aligned (50 DMA: ₹{sma_50}, 200 DMA: ₹{sma_200})")
        invalidation_triggers.append("Close drops below 200 DMA or 50 DMA falls below 200 DMA")

    # 2. SECTOR CONFIRMATION (Max 15 pts)
    sec_pts = 15.0 if sector_score >= 60.0 else round((sector_score / 60.0) * 15.0, 1)
    total_score += sec_pts
    sec_passed = bool(sector_score >= 60.0)
    sec_rule = {
        "rule_name": "Sector Confirmation",
        "description": f"Sector '{sector}' strength score >= 60.0",
        "points_awarded": float(sec_pts),
        "max_points": 15.0,
        "passed": sec_passed,
        "detail": f"{sector} Sector Score: {sector_score}/100"
    }
    if sec_passed:
        passed_rules.append(sec_rule)
        why_passed.append(f"Sector '{sector}' is in a bullish regime (Score: {sector_score}/100)")
    else:
        failed_rules.append(sec_rule)
        why_failed_100.append(f"Sector '{sector}' score ({sector_score}/100) is below the 60.0 threshold")
        invalidation_triggers.append(f"Sector score weakens below 45.0")

    # 3. MOMENTUM CONFIRMATION (Max 15 pts)
    rsi_passed = bool((rsi > 50.0) and (rsi <= 75.0))
    mom_pts = 15.0 if rsi_passed else (10.0 if rsi > 50.0 else 0.0)
    total_score += mom_pts
    mom_rule = {
        "rule_name": "Momentum Confirmation",
        "description": "RSI(14) > 50 and <= 75 (Bullish momentum without overbought exhaustion)",
        "points_awarded": float(mom_pts),
        "max_points": 15.0,
        "passed": rsi_passed,
        "detail": f"RSI(14) = {rsi}"
    }
    if rsi_passed:
        passed_rules.append(mom_rule)
        why_passed.append(f"Healthy bullish momentum with RSI at {rsi}")
    else:
        failed_rules.append(mom_rule)
        if rsi > 75.0:
            why_failed_100.append(f"RSI is overbought ({rsi} > 75 exhaustion level)")
        else:
            why_failed_100.append(f"RSI momentum is weak ({rsi} <= 50)")
        invalidation_triggers.append("RSI falls below 45 or spikes over 80 into extreme exhaustion")

    # 4. VOLUME CONFIRMATION (Max 15 pts)
    vol_passed = bool(vol_ratio >= 1.2)
    vol_pts = 15.0 if vol_ratio >= 1.2 else (10.0 if vol_ratio >= 1.0 else 5.0)
    total_score += vol_pts
    vol_rule = {
        "rule_name": "Volume Confirmation",
        "description": "Current volume vs 20-day average volume ratio (>= 1.2x)",
        "points_awarded": float(vol_pts),
        "max_points": 15.0,
        "passed": vol_passed,
        "detail": f"Volume Ratio = {vol_ratio}x (Current: {ind['volume']:,} vs 20D Avg: {ind['avg_volume_20d']:,})"
    }
    if vol_passed:
        passed_rules.append(vol_rule)
        why_passed.append(f"Volume expansion verified ({vol_ratio}x 20-day average volume)")
    else:
        failed_rules.append(vol_rule)
        why_failed_100.append(f"Volume expansion was modest ({vol_ratio}x vs required 1.2x 20D average)")

    # 5. RELATIVE STRENGTH (Max 15 pts)
    rs_passed = bool(rs_20 > 0.0)
    rs_pts = 15.0 if rs_20 > 0.0 else 0.0
    total_score += rs_pts
    rs_rule = {
        "rule_name": "Relative Strength vs NIFTY",
        "description": "Outperformance vs NIFTY 50 over 20 trading days",
        "points_awarded": float(rs_pts),
        "max_points": 15.0,
        "passed": rs_passed,
        "detail": f"RS Outperformance = {rs_20}%"
    }
    if rs_passed:
        passed_rules.append(rs_rule)
        why_passed.append(f"Outperforming NIFTY 50 by {rs_20}% over last 20 trading days")
    else:
        failed_rules.append(rs_rule)
        why_failed_100.append(f"Underperforming NIFTY 50 by {abs(rs_20)}% over 20 days")
        invalidation_triggers.append("Relative strength stays negative for 5 consecutive days")

    # 6. BREAKOUT CONFIRMATION (Max 10 pts)
    bk_pts = 10.0 if is_breakout else 5.0
    total_score += bk_pts
    bk_rule = {
        "rule_name": "Breakout Confirmation",
        "description": "Price near or breaking above 20-day swing high",
        "points_awarded": float(bk_pts),
        "max_points": 10.0,
        "passed": is_breakout,
        "detail": f"Price ₹{price} vs 20D High ₹{high_20d}"
    }
    if is_breakout:
        passed_rules.append(bk_rule)
        why_passed.append(f"Price is at or near 20-day breakout high (₹{high_20d})")
    else:
        failed_rules.append(bk_rule)
        why_failed_100.append(f"Price is below recent 20-day high (₹{high_20d})")

    # 7. MARKET CONFIRMATION (Max 10 pts)
    mkt_passed = bool(market_score >= 60.0)
    mkt_pts = 10.0 if market_score >= 60.0 else (5.0 if market_score >= 40.0 else 0.0)
    total_score += mkt_pts
    mkt_rule = {
        "rule_name": "Market Confirmation",
        "description": "Overall NIFTY Market Regime Score >= 60.0",
        "points_awarded": float(mkt_pts),
        "max_points": 10.0,
        "passed": mkt_passed,
        "detail": f"NIFTY Market Score = {market_score}/100"
    }
    if mkt_passed:
        passed_rules.append(mkt_rule)
        why_passed.append(f"Overall market tailwind supported (Market Score: {market_score}/100)")
    else:
        failed_rules.append(mkt_rule)
        why_failed_100.append(f"Market environment is neutral/weak (Market Score: {market_score}/100)")

    total_score = float(round(min(100.0, max(0.0, total_score)), 1))

    # Classification
    if total_score >= 80.0:
        classification = "Strong Setup"
    elif total_score >= 65.0:
        classification = "Confirmed Setup"
    elif total_score >= 50.0:
        classification = "Watchlist"
    else:
        classification = "Not Confirmed"

    # Reference Levels
    ref_entry = float(round(high_20d, 2))
    ref_stop = float(round(max(price - (2 * atr), sma_50 * 0.98), 2))
    risk = max(1.0, ref_entry - ref_stop)
    ref_target_1 = float(round(ref_entry + (2 * risk), 2))
    ref_target_2 = float(round(ref_entry + (3 * risk), 2))

    reference_levels = {
        "entry_reference": ref_entry,
        "stop_reference": ref_stop,
        "target_1_reference": ref_target_1,
        "target_2_reference": ref_target_2,
        "risk_amount": float(round(risk, 2)),
        "risk_reward_ratio": "1:2 / 1:3",
        "notice": "Reference levels for analysis ONLY. Not guaranteed future prices or buy/sell recommendations."
    }

    rule_explanation = (
        f"{symbol} has achieved a confirmation score of {total_score}/100 ({classification}). "
        f"The stock is trading at ₹{price} ({'above' if price_above_50 else 'below'} its 50 DMA of ₹{sma_50}). "
        f"Its sector ({sector}) score is {sector_score}/100 with RSI at {rsi}."
    )

    if not invalidation_triggers:
        invalidation_triggers.append("Price drops below 50 DMA or confirmation score falls below 50.0")

    chg_pct = float(round(((price - stock_df['Close'].iloc[-2]) / stock_df['Close'].iloc[-2] * 100), 2)) if len(stock_df) > 1 else 0.0

    return {
        "symbol": symbol,
        "company_name": company_name,
        "sector": sector,
        "price": price,
        "change_percent": chg_pct,
        "confirmation_score": total_score,
        "classification": classification,
        "passed_rules": passed_rules,
        "failed_rules": failed_rules,
        "why_passed": why_passed,
        "why_failed_100": why_failed_100,
        "invalidation_triggers": invalidation_triggers,
        "reference_levels": reference_levels,
        "rule_explanation": rule_explanation
    }
