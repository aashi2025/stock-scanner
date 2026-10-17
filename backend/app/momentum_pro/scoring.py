"""
Momentum Pro — Explainable Quantitative Setup Scoring Engine (0 - 100).
Rules-based heuristics across 5 key dimensions:
1. Trend Structure (Max 25 pts)
2. Relative Strength vs Benchmark (Max 20 pts)
3. Momentum & RSI State (Max 20 pts)
4. Volume Surge & Institutional Interest (Max 20 pts)
5. Price Structure & Breakout Proximity (Max 15 pts)

Disclaimer: Scores are research heuristics and NOT win probabilities or guarantees.
"""

from typing import Dict, Any, List

SCORE_DISCLAIMER = (
    "Setup Score is an objective, rules-based research heuristic (0-100) reflecting multi-factor "
    "alignment across Trend, Relative Strength, RSI, Volume, and Structure. "
    "It does NOT represent a win probability, profit guarantee, or buy recommendation."
)

def calculate_momentum_setup_score(ind: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes an explainable 0-100 score with explicit point breakdown.
    """
    breakdown: List[Dict[str, Any]] = []
    total_score = 0.0

    # -------------------------------------------------------------
    # 1. Trend Structure (Max 25 pts)
    # -------------------------------------------------------------
    pts_trend = 0.0
    price = ind.get("price", 0.0)
    sma_50 = ind.get("sma_50", 0.0)
    sma_200 = ind.get("sma_200", 0.0)
    ema_9 = ind.get("ema_9", 0.0)
    ema_20 = ind.get("ema_20", 0.0)

    # Sub-rule 1a: Price > SMA 50 (10 pts)
    p_gt_50 = bool(price > sma_50)
    if p_gt_50:
        pts_trend += 10.0

    # Sub-rule 1b: Short-term Momentum Alignment EMA 9 > EMA 20 (8 pts)
    ema_cross = bool(ema_9 > ema_20)
    if ema_cross:
        pts_trend += 8.0

    # Sub-rule 1c: Golden Macro Alignment SMA 50 > SMA 200 (7 pts)
    macro_bull = bool(sma_50 > sma_200)
    if macro_bull:
        pts_trend += 7.0

    total_score += pts_trend
    breakdown.append({
        "category": "Trend Structure",
        "points": round(pts_trend, 1),
        "max_points": 25.0,
        "detail": f"Price > 50 SMA ({'✅' if p_gt_50 else '❌'}), EMA 9 > EMA 20 ({'✅' if ema_cross else '❌'}), 50 > 200 SMA ({'✅' if macro_bull else '❌'})"
    })

    # -------------------------------------------------------------
    # 2. Relative Strength vs NIFTY Benchmark (Max 20 pts)
    # -------------------------------------------------------------
    pts_rs = 0.0
    rs_20 = ind.get("rs_vs_nifty_20d", 0.0)
    rs_50 = ind.get("rs_vs_nifty_50d", 0.0)

    if rs_20 >= 3.0:
        pts_rs += 12.0
    elif rs_20 > 0.0:
        pts_rs += 8.0
    elif rs_20 > -2.0:
        pts_rs += 4.0

    if rs_50 > 0.0:
        pts_rs += 8.0
    elif rs_50 > -3.0:
        pts_rs += 4.0

    total_score += pts_rs
    breakdown.append({
        "category": "Relative Strength",
        "points": round(pts_rs, 1),
        "max_points": 20.0,
        "detail": f"20D RS vs NIFTY: {rs_20:+0.2f}% | 50D RS: {rs_50:+0.2f}%"
    })

    # -------------------------------------------------------------
    # 3. Momentum & RSI State (Max 20 pts)
    # -------------------------------------------------------------
    pts_mom = 0.0
    rsi = ind.get("rsi_14", 50.0)
    fresh_cross = ind.get("rsi_fresh_crossover", False)

    if fresh_cross:
        pts_mom = 20.0
        mom_detail = f"Fresh RSI 14 Crossover above 50 on completed bar (RSI: {rsi:.1f})"
    elif 53.0 <= rsi <= 68.0:
        pts_mom = 16.0
        mom_detail = f"Optimal Bullish Momentum Zone (RSI: {rsi:.1f})"
    elif 50.0 <= rsi < 53.0:
        pts_mom = 12.0
        mom_detail = f"Early Positive Momentum (RSI: {rsi:.1f})"
    elif rsi > 68.0 and rsi <= 78.0:
        pts_mom = 10.0
        mom_detail = f"Strong but Approaching Overbought (RSI: {rsi:.1f})"
    elif rsi > 78.0:
        pts_mom = 4.0
        mom_detail = f"Exhaustion Zone (RSI: {rsi:.1f} > 78)"
    else:
        pts_mom = 0.0
        mom_detail = f"Sub-50 Bearish Momentum (RSI: {rsi:.1f})"

    total_score += pts_mom
    breakdown.append({
        "category": "Momentum & RSI",
        "points": round(pts_mom, 1),
        "max_points": 20.0,
        "detail": mom_detail
    })

    # -------------------------------------------------------------
    # 4. Volume Surge & RVOL (Max 20 pts)
    # -------------------------------------------------------------
    pts_vol = 0.0
    rvol = ind.get("rvol", ind.get("vol_ratio", 1.0))

    if rvol >= 2.0:
        pts_vol = 20.0
        vol_detail = f"Massive Volume Surge ({rvol:.2f}x 20-DMA)"
    elif rvol >= 1.5:
        pts_vol = 16.0
        vol_detail = f"High Institutional Participation ({rvol:.2f}x 20-DMA)"
    elif rvol >= 1.2:
        pts_vol = 12.0
        vol_detail = f"Above Average Volume ({rvol:.2f}x 20-DMA)"
    elif rvol >= 1.0:
        pts_vol = 6.0
        vol_detail = f"Normal Volume ({rvol:.2f}x 20-DMA)"
    else:
        pts_vol = 2.0
        vol_detail = f"Dry / Below Average Volume ({rvol:.2f}x 20-DMA)"

    total_score += pts_vol
    breakdown.append({
        "category": "Volume & Accumulation",
        "points": round(pts_vol, 1),
        "max_points": 20.0,
        "detail": vol_detail
    })

    # -------------------------------------------------------------
    # 5. Price Structure & Breakout Proximity (Max 15 pts)
    # -------------------------------------------------------------
    pts_struct = 0.0
    is_breakout = ind.get("is_price_breakout", False)
    dist_res = ind.get("dist_to_resistance_pct", 0.0)

    if is_breakout:
        pts_struct = 15.0
        struct_detail = "Confirmed Price Breakout above 20D resistance level"
    elif 0.0 <= dist_res <= 1.5:
        pts_struct = 13.0
        struct_detail = f"Consolidating tightly within {dist_res:.2f}% of 20D resistance"
    elif dist_res <= 3.0:
        pts_struct = 10.0
        struct_detail = f"Pre-breakout watch: {dist_res:.2f}% from resistance"
    elif dist_res <= 6.0:
        pts_struct = 5.0
        struct_detail = f"Approaching resistance ({dist_res:.2f}% away)"
    else:
        pts_struct = 2.0
        struct_detail = f"Far from breakout level ({dist_res:.2f}% away)"

    total_score += pts_struct
    breakdown.append({
        "category": "Price Structure",
        "points": round(pts_struct, 1),
        "max_points": 15.0,
        "detail": struct_detail
    })

    final_score = min(100.0, max(0.0, round(total_score, 1)))

    # Classification
    if final_score >= 80.0:
        grade = "Strong High-Conviction Setup"
        badge_color = "#16a34a" # Green
    elif final_score >= 65.0:
        grade = "Solid Momentum Setup"
        badge_color = "#2563eb" # Blue
    elif final_score >= 50.0:
        grade = "Developing Setup"
        badge_color = "#d97706" # Amber
    else:
        grade = "Weak / Low Momentum"
        badge_color = "#dc2626" # Red

    return {
        "setup_score": final_score,
        "grade": grade,
        "badge_color": badge_color,
        "breakdown": breakdown,
        "disclaimer": SCORE_DISCLAIMER
    }
