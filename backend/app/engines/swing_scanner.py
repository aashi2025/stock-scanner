from typing import Dict, Any, List, Optional
import pandas as pd
from backend.app.indicators.calculations import compute_all_indicators
from backend.app.engines.ranking import compute_composite_ranking

def analyze_swing_setup(
    stock: Dict[str, Any],
    stock_df: pd.DataFrame,
    nifty_df: pd.DataFrame,
    sector_scores_map: Dict[str, float],
    market_score: float,
    data_source: str = "Verified Market Data",
    custom_weights: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Dedicated Swing Trading Scanner Engine.
    Executes on completed daily historical candles without look-ahead bias.
    Rules:
    1. RSI(14) Fresh Crossover above 50 (Strictly T-1 <= 50 and T > 50)
    2. EMA50 & EMA200 Trend Alignment (Price > EMA50, Price > EMA200, EMA50 > EMA200)
    3. Volume Breakout vs 20-session average volume (>= 1.2x)
    4. Distance from 52-Week High (<= 20% distance preferred)
    5. Sector Strength Score >= 60.0
    """
    symbol = str(stock["symbol"])
    company_name = str(stock.get("name", symbol))
    sector = str(stock.get("sector", "General"))

    if stock_df.empty or len(stock_df) < 20:
        return {
            "symbol": symbol,
            "company_name": company_name,
            "sector": sector,
            "price": 0.0,
            "change_percent": 0.0,
            "swing_score": 0.0,
            "classification": "INSUFFICIENT DATA",
            "rsi_fresh_crossover": False,
            "rsi_status": "Insufficient Data",
            "rsi_value": 50.0,
            "ema_trend_bullish": False,
            "volume_breakout": False,
            "vol_ratio": 1.0,
            "dist_from_52w_high_pct": 0.0,
            "high_52w": 0.0,
            "sector_score": 60.0,
            "candle_timestamp": "",
            "passed_rules": [],
            "failed_rules": [],
            "reasons": ["Insufficient historical candle data"],
            "reference_levels": {}
        }

    ind = compute_all_indicators(stock_df, nifty_df)
    price = float(ind["price"])
    ema_50 = float(ind["ema_50"])
    ema_200 = float(ind["ema_200"])
    rsi = float(ind["rsi_14"])
    rsi_fresh = bool(ind["rsi_fresh_crossover"])
    rsi_bars = int(ind["rsi_bars_above_50"])
    rsi_status = str(ind["rsi_status"])
    vol_ratio = float(ind["vol_ratio"])
    is_vol_bk = bool(ind["is_volume_breakout"])
    dist_52w = float(ind["dist_from_52w_high_pct"])
    high_52w = float(ind["high_52w"])
    atr = float(ind["atr_14"])

    sector_score = float(sector_scores_map.get(sector.upper(), sector_scores_map.get("GENERAL", 60.0)))
    last_candle_time = str(stock_df.index[-1].strftime("%Y-%m-%d %H:%M:%S")) if hasattr(stock_df.index[-1], "strftime") else str(stock_df.index[-1])

    passed_rules = []
    failed_rules = []
    reasons = []

    score = 0.0

    # 1. RSI(14) MOMENTUM & FRESH CROSSOVER (Max 25 pts)
    # Fresh crossover gets full 25 pts. Continued bullish gets 15 pts. Below 50 gets 0 pts.
    if rsi_fresh:
        score += 25.0
        passed_rules.append({
            "name": "RSI(14) Fresh Crossover > 50",
            "detail": f"Fresh bullish crossover! RSI crossed from {ind.get('prev_rsi', 48.0)} to {rsi}.",
            "points": 25.0
        })
        reasons.append("⚡ Fresh RSI(14) Bullish Crossover above 50 triggered on completed candle")
    elif rsi > 50.0 and rsi <= 75.0:
        score += 16.0
        passed_rules.append({
            "name": "RSI(14) Bullish Momentum",
            "detail": f"RSI is bullish at {rsi} ({rsi_bars} sessions above 50, not a fresh cross).",
            "points": 16.0
        })
        reasons.append(f"RSI(14) at {rsi} shows ongoing bullish momentum ({rsi_bars} days above 50)")
    elif rsi > 75.0:
        score += 8.0
        failed_rules.append({
            "name": "RSI(14) Overbought Warning",
            "detail": f"RSI at {rsi} is overbought (> 75 exhaustion level).",
            "points": 8.0
        })
        reasons.append(f"⚠️ RSI is extended at {rsi} (>75 overbought exhaustion)")
    else:
        failed_rules.append({
            "name": "RSI(14) Weak Momentum",
            "detail": f"RSI is {rsi} (below 50 neutral threshold).",
            "points": 0.0
        })

    # 2. EMA50 & EMA200 TREND (Max 25 pts)
    # Price > EMA50 (10 pts), Price > EMA200 (10 pts), EMA50 > EMA200 (5 pts)
    ema_pts = 0.0
    if price > ema_50: ema_pts += 10.0
    if price > ema_200: ema_pts += 10.0
    if ema_50 > ema_200: ema_pts += 5.0
    score += ema_pts

    ema_aligned = bool(ema_pts >= 20.0)
    if ema_aligned:
        passed_rules.append({
            "name": "EMA Trend Alignment",
            "detail": f"Price ₹{price} > EMA50 ₹{ema_50} & EMA200 ₹{ema_200}",
            "points": ema_pts
        })
        reasons.append(f"📈 Strong uptrend: Price ₹{price} trading above 50 EMA (₹{ema_50}) and 200 EMA (₹{ema_200})")
    else:
        failed_rules.append({
            "name": "EMA Trend Alignment",
            "detail": f"Price ₹{price} vs EMA50 ₹{ema_50} / EMA200 ₹{ema_200}",
            "points": ema_pts
        })

    # 3. VOLUME BREAKOUT VS 20-SESSION AVERAGE (Max 20 pts)
    vol_pts = 0.0
    if vol_ratio >= 1.5:
        vol_pts = 20.0
        passed_rules.append({
            "name": "Strong Volume Surge",
            "detail": f"Volume is {vol_ratio}x 20-day average volume.",
            "points": 20.0
        })
        reasons.append(f"🔥 Massive volume breakout ({vol_ratio}x 20-day average volume)")
    elif vol_ratio >= 1.2:
        vol_pts = 15.0
        passed_rules.append({
            "name": "Volume Expansion",
            "detail": f"Volume is {vol_ratio}x 20-day average volume.",
            "points": 15.0
        })
        reasons.append(f"Volume surge confirmed ({vol_ratio}x 20-day average volume)")
    elif vol_ratio >= 0.9:
        vol_pts = 8.0
        failed_rules.append({
            "name": "Normal Volume",
            "detail": f"Volume ratio {vol_ratio}x is below the 1.2x surge mark.",
            "points": 8.0
        })
    else:
        vol_pts = 0.0
        failed_rules.append({
            "name": "Drying Volume",
            "detail": f"Volume is low ({vol_ratio}x 20-day average).",
            "points": 0.0
        })
    score += vol_pts

    # 4. 52-WEEK HIGH DISTANCE (Max 15 pts)
    # Proximity to 52W High indicates high relative momentum & lack of overhead supply
    high_pts = 0.0
    if dist_52w <= 5.0:
        high_pts = 15.0
        passed_rules.append({
            "name": "At/Near 52-Week High",
            "detail": f"Trading within {dist_52w}% of 52-week high (₹{high_52w}).",
            "points": 15.0
        })
        reasons.append(f"🎯 Ultra-high relative strength: within {dist_52w}% of 52-week high (₹{high_52w})")
    elif dist_52w <= 15.0:
        high_pts = 12.0
        passed_rules.append({
            "name": "Within 15% of 52-Week High",
            "detail": f"Trading {dist_52w}% below 52-week high (₹{high_52w}).",
            "points": 12.0
        })
        reasons.append(f"Within consolidation distance ({dist_52w}%) of 52-week high")
    elif dist_52w <= 25.0:
        high_pts = 6.0
        failed_rules.append({
            "name": "Moderate Distance from 52W High",
            "detail": f"{dist_52w}% below 52-week high.",
            "points": 6.0
        })
    else:
        high_pts = 0.0
        failed_rules.append({
            "name": "Far from 52W High",
            "detail": f"{dist_52w}% below 52-week high. Overhead resistance present.",
            "points": 0.0
        })
    score += high_pts

    # 5. SECTOR & RELATIVE STRENGTH (Max 15 pts)
    sec_pts = 0.0
    if sector_score >= 65.0:
        sec_pts = 15.0
        passed_rules.append({
            "name": "Sector Tailwind",
            "detail": f"{sector} sector strength is strong ({sector_score}/100).",
            "points": 15.0
        })
        reasons.append(f"Sector '{sector}' is in a bullish expansion mode ({sector_score}/100)")
    elif sector_score >= 55.0:
        sec_pts = 10.0
        passed_rules.append({
            "name": "Sector Neutral",
            "detail": f"{sector} sector score is {sector_score}/100.",
            "points": 10.0
        })
    else:
        sec_pts = 3.0
        failed_rules.append({
            "name": "Sector Headwind",
            "detail": f"{sector} sector is lagging ({sector_score}/100).",
            "points": 3.0
        })
    score += sec_pts

    score = float(round(min(100.0, max(0.0, score)), 1))

    # Swing Classification
    if score >= 80.0:
        classification = "STRONG SWING CANDIDATE"
    elif score >= 65.0:
        classification = "CONFIRMED SWING SETUP"
    elif score >= 50.0:
        classification = "SWING WATCHLIST"
    else:
        classification = "AVOID / NOT CONFIRMED"

    # Swing Reference Levels (Analytical reference only)
    high_20d = float(stock_df["High"].tail(20).max()) if "High" in stock_df.columns else price
    ref_entry = round(max(price, high_20d), 2)
    ref_stop = round(max(price - (1.5 * atr), ema_50 * 0.985), 2)
    risk = max(1.0, ref_entry - ref_stop)
    ref_target_1 = round(ref_entry + (2.0 * risk), 2)
    ref_target_2 = round(ref_entry + (3.0 * risk), 2)

    chg_pct = float(round(((price - stock_df['Close'].iloc[-2]) / stock_df['Close'].iloc[-2] * 100), 2)) if len(stock_df) > 1 else 0.0

    return {
        "symbol": symbol,
        "company_name": company_name,
        "sector": sector,
        "price": price,
        "change_percent": chg_pct,
        "swing_score": score,
        "classification": classification,
        "rsi_fresh_crossover": rsi_fresh,
        "rsi_status": rsi_status,
        "rsi_value": rsi,
        "ema_trend_bullish": ema_aligned,
        "ema_50": ema_50,
        "ema_200": ema_200,
        "volume_breakout": is_vol_bk,
        "vol_ratio": vol_ratio,
        "volume": ind["volume"],
        "avg_volume_20d": ind["avg_volume_20d"],
        "dist_from_52w_high_pct": dist_52w,
        "high_52w": high_52w,
        "sector_score": sector_score,
        "candle_timestamp": last_candle_time,
        "candle_timeframe": "1D (Completed Daily Candle)",
        "data_source": data_source,
        "passed_rules": passed_rules,
        "failed_rules": failed_rules,
        "reasons": reasons,
        "ranking": compute_composite_ranking(ind, stock.get("fundamentals"), sector, custom_weights),
        "reference_levels": {
            "entry_reference": ref_entry,
            "stop_loss_reference": ref_stop,
            "target_1_reference": ref_target_1,
            "target_2_reference": ref_target_2,
            "risk_reward": "1:2 / 1:3",
            "risk_per_share": round(risk, 2)
        }
    }
