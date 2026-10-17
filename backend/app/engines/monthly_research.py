from typing import Dict, Any, List
import pandas as pd
from backend.app.data_providers.base import MarketDataProvider
from backend.app.indicators.calculations import calculate_ema, calculate_52w_metrics

def analyze_monthly_candidate(
    stock: Dict[str, Any],
    provider: MarketDataProvider
) -> Dict[str, Any]:
    """
    Monthly Stock Research Engine.
    Combines:
    1. Multi-month technical trend on Upstox historical candles
    2. Verified Financial Fundamentals (Upstox Fundamentals API or Verified Public Layer)
    Transparently reports data source without ever faking missing fundamental data.
    """
    symbol = str(stock["symbol"])
    company_name = str(stock.get("name", symbol))
    sector = str(stock.get("sector", "General"))

    # 1. Fetch Price Trend from Upstox (1 year of daily candles)
    df = provider.get_historical_data(symbol, period="1y", interval="day")
    
    if df.empty or len(df) < 50:
        return {
            "symbol": symbol,
            "company_name": company_name,
            "sector": sector,
            "classification": "DATA UNAVAILABLE",
            "price": 0.0,
            "reasons": ["Insufficient historical price data from market data provider"],
            "fundamentals": {},
            "fundamental_source": "None"
        }

    close = df["Close"]
    price = float(round(close.iloc[-1], 2))
    
    ema_50_series = calculate_ema(close, 50)
    ema_200_series = calculate_ema(close, 200)
    
    ema_50 = float(round(ema_50_series.iloc[-1], 2)) if not pd.isna(ema_50_series.iloc[-1]) else price
    ema_200 = float(round(ema_200_series.iloc[-1], 2)) if not pd.isna(ema_200_series.iloc[-1]) else price
    
    high_52w, low_52w, dist_52w_pct = calculate_52w_metrics(df)

    # Calculate 3-month and 6-month price performance
    ret_3m = round(float((price - close.iloc[-60]) / close.iloc[-60] * 100), 1) if len(close) >= 60 else 0.0
    ret_6m = round(float((price - close.iloc[-120]) / close.iloc[-120] * 100), 1) if len(close) >= 120 else 0.0

    # 2. Fetch Fundamentals from verified source
    fundamentals = provider.get_fundamental_data(symbol)
    fund_source = fundamentals.get("data_source", "Verified Public Data")
    is_fund_verified = fundamentals.get("is_verified", False)

    roce = float(fundamentals.get("roce", 0.0) or 0.0)
    roe = float(fundamentals.get("roe", 0.0) or 0.0)
    debt_equity = float(fundamentals.get("debt_to_equity", 0.0) or 0.0)
    sales_growth = float(fundamentals.get("sales_growth_3y", 0.0) or 0.0)
    profit_growth = float(fundamentals.get("profit_growth_3y", 0.0) or 0.0)
    pe_ratio = float(fundamentals.get("pe_ratio", 0.0) or 0.0)

    # 3. Rule Evaluation
    passed_criteria = []
    caution_criteria = []
    failed_criteria = []

    # Trend Checks
    above_200_ema = bool(price > ema_200)
    above_50_ema = bool(price > ema_50)
    golden_cross = bool(ema_50 > ema_200)
    near_highs = bool(dist_52w_pct <= 25.0)

    if above_200_ema:
        passed_criteria.append(f"Price (₹{price}) above 200 EMA (₹{ema_200}) - Long-term bull trend intact")
    else:
        failed_criteria.append(f"Price (₹{price}) is BELOW 200 EMA (₹{ema_200}) - Structural weakness")

    if above_50_ema:
        passed_criteria.append(f"Price above 50 EMA (₹{ema_50}) - Medium-term momentum positive")
    else:
        caution_criteria.append(f"Consolidating below 50 EMA (₹{ema_50})")

    if near_highs:
        passed_criteria.append(f"Near 52W High (₹{high_52w}) - Distance is only {dist_52w_pct}%")
    else:
        caution_criteria.append(f"Lagging {dist_52w_pct}% below 52W High (₹{high_52w})")

    # Fundamental Checks
    is_financial_sector = any(kw in sector.upper() for kw in ["BANK", "FINANCIAL", "NBFC"])

    if is_fund_verified:
        # ROCE Check
        if roce >= 15.0:
            passed_criteria.append(f"High Capital Efficiency: ROCE is {roce}% (>= 15% threshold)")
        elif roce >= 10.0:
            caution_criteria.append(f"Moderate Capital Efficiency: ROCE is {roce}%")
        else:
            failed_criteria.append(f"Weak ROCE: {roce}% (< 10% threshold)")

        # ROE Check
        if roe >= 15.0:
            passed_criteria.append(f"Healthy Profitability: ROE is {roe}% (>= 15% threshold)")
        elif roe >= 10.0:
            caution_criteria.append(f"Moderate ROE: {roe}%")
        else:
            failed_criteria.append(f"Low ROE: {roe}%")

        # Debt/Equity Check (Not applicable to Banks/Financials)
        if not is_financial_sector:
            if debt_equity <= 0.5:
                passed_criteria.append(f"Conservative Leverage: Debt/Equity is {debt_equity} (<= 0.5)")
            elif debt_equity <= 1.0:
                caution_criteria.append(f"Moderate Debt/Equity: {debt_equity}")
            else:
                failed_criteria.append(f"High Debt Alert: Debt/Equity is {debt_equity} (> 1.0 threshold)")
        else:
            passed_criteria.append("Bank/NBFC sector: Debt evaluated via capital adequacy")

        # Growth Check
        if sales_growth > 8.0 and profit_growth > 8.0:
            passed_criteria.append(f"Consistent Growth: Sales +{sales_growth}%, Profit +{profit_growth}%")
        elif sales_growth > 0 or profit_growth > 0:
            caution_criteria.append(f"Subdued Growth: Sales {sales_growth}%, Profit {profit_growth}%")
        else:
            failed_criteria.append(f"Negative Growth: Sales {sales_growth}%, Profit {profit_growth}%")
    else:
        caution_criteria.append("⚠️ Fundamental data unavailable on broker API - Verify financials manually via Screener.in")

    # 4. Strict Classification Logic: Buy Candidate vs Hold vs Exit Review
    score = 0
    if above_200_ema: score += 25
    if above_50_ema: score += 15
    if near_highs: score += 15
    if is_fund_verified:
        if roce >= 15.0: score += 15
        if roe >= 15.0: score += 15
        if is_financial_sector or debt_equity <= 1.0: score += 10
        if sales_growth > 5.0 and profit_growth > 5.0: score += 5
    else:
        # If fundamentals couldn't be loaded, cannot award full buy score without verification
        score += 10

    if not above_200_ema or len(failed_criteria) >= 2:
        classification = "EXIT REVIEW"
        badge_color = "red"
        action_plan = "Review for reduction or exit. Structural trend or fundamental quality has broken down."
    elif score >= 75 and len(failed_criteria) == 0:
        classification = "BUY CANDIDATE"
        badge_color = "green"
        action_plan = "High-conviction monthly candidate. Accumulate on dips toward 50 EMA with 1:3 risk-reward."
    else:
        classification = "HOLD CANDIDATE"
        badge_color = "blue"
        action_plan = "Maintain existing positions. Trailing stop below 200 EMA. Avoid fresh bulk allocation."

    return {
        "symbol": symbol,
        "company_name": company_name,
        "sector": sector,
        "price": price,
        "classification": classification,
        "badge_color": badge_color,
        "score": score,
        "action_plan": action_plan,
        "technical_summary": {
            "ema_50": ema_50,
            "ema_200": ema_200,
            "high_52w": high_52w,
            "dist_52w_pct": dist_52w_pct,
            "return_3m_pct": ret_3m,
            "return_6m_pct": ret_6m,
            "above_200_ema": above_200_ema,
            "above_50_ema": above_50_ema
        },
        "fundamental_summary": {
            "roce": roce,
            "roe": roe,
            "debt_to_equity": debt_equity,
            "sales_growth": sales_growth,
            "profit_growth": profit_growth,
            "pe_ratio": pe_ratio,
            "is_verified": is_fund_verified,
            "data_source": fund_source
        },
        "passed_criteria": passed_criteria,
        "caution_criteria": caution_criteria,
        "failed_criteria": failed_criteria,
        "timestamp": str(df.index[-1].strftime("%Y-%m-%d")) if hasattr(df.index[-1], "strftime") else str(df.index[-1])
    }

def run_monthly_research_scan(
    stocks: List[Dict[str, Any]],
    provider: MarketDataProvider
) -> Dict[str, Any]:
    """
    Runs monthly stock research pipeline across universe.
    Returns categorized lists: Buy Candidates, Hold Candidates, Exit Reviews.
    """
    buy_candidates = []
    hold_candidates = []
    exit_reviews = []

    for s in stocks:
        res = analyze_monthly_candidate(s, provider)
        cls = res.get("classification")
        if cls == "BUY CANDIDATE":
            buy_candidates.append(res)
        elif cls == "HOLD CANDIDATE":
            hold_candidates.append(res)
        elif cls == "EXIT REVIEW":
            exit_reviews.append(res)
        else:
            hold_candidates.append(res)

    # Sort each list by score
    buy_candidates.sort(key=lambda x: x["score"], reverse=True)
    hold_candidates.sort(key=lambda x: x["score"], reverse=True)
    exit_reviews.sort(key=lambda x: x["score"])

    return {
        "buy_candidates": buy_candidates,
        "hold_candidates": hold_candidates,
        "exit_reviews": exit_reviews,
        "total_analyzed": len(stocks),
        "data_provider": provider.get_provider_name()
    }
