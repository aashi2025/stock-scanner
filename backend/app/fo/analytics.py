"""
Futures and Options (F&O) Analytics Engine for Indian Equities and Indices.
Calculates:
- Price / Open Interest (OI) Buildup (Long Buildup, Short Buildup, Short Covering, Long Unwinding)
- Option Chain with Greeks (Delta, Gamma, Theta, Vega)
- Put-Call Ratio (PCR)
- Max Pain Strike
- Major Options Support (Max Put OI) and Resistance (Max Call OI)

Disclaimer: Derivatives positioning, PCR, and Max Pain are contextual metrics,
NOT standalone buy/sell trading signals.
"""

from typing import List, Dict, Any, Optional
import math
from datetime import datetime
from backend.app.fo.greeks import calculate_option_greeks

FO_DISCLAIMER = (
    "Derivatives Open Interest (OI), PCR, and Max Pain are positioning indicators reflecting "
    "aggregate market participation. They do NOT guarantee price direction or prove institutional "
    "intent, and should never be used in isolation for trade decisions."
)

def interpret_price_oi_buildup(price_change_pct: float, oi_change_pct: float) -> Dict[str, str]:
    """
    Standard quantitative interpretation of Price and Open Interest co-movement.
    """
    if price_change_pct > 0 and oi_change_pct > 0:
        return {
            "buildup": "Long Buildup",
            "bias": "BULLISH",
            "color": "#16a34a",
            "interpretation": "Fresh buyers entering the market with expanding open contracts."
        }
    elif price_change_pct < 0 and oi_change_pct > 0:
        return {
            "buildup": "Short Buildup",
            "bias": "BEARISH",
            "color": "#dc2626",
            "interpretation": "Aggressive short sellers entering with expanding open contracts."
        }
    elif price_change_pct > 0 and oi_change_pct < 0:
        return {
            "buildup": "Short Covering",
            "bias": "BULLISH BOUNCE",
            "color": "#0284c7",
            "interpretation": "Sellers buying back and closing existing short positions."
        }
    elif price_change_pct < 0 and oi_change_pct < 0:
        return {
            "buildup": "Long Unwinding",
            "bias": "BEARISH WEAKNESS",
            "color": "#d97706",
            "interpretation": "Longs closing profitable or losing positions without fresh buying."
        }
    else:
        return {
            "buildup": "Neutral / Sideways",
            "bias": "NEUTRAL",
            "color": "#64748b",
            "interpretation": "Minimal shift in price and open interest."
        }


def calculate_max_pain(strikes: List[float], call_oi: List[int], put_oi: List[int]) -> float:
    """
    Calculates Max Pain strike: The strike price where option sellers encounter minimum payout.
    """
    if not strikes or len(strikes) != len(call_oi) or len(strikes) != len(put_oi):
        return strikes[0] if strikes else 0.0

    min_loss = float("inf")
    max_pain_strike = strikes[0]

    for test_strike in strikes:
        total_payout = 0.0
        for s, c_oi, p_oi in zip(strikes, call_oi, put_oi):
            # Call buyer payout if price expires at test_strike
            if test_strike > s:
                total_payout += (test_strike - s) * c_oi
            # Put buyer payout if price expires at test_strike
            if test_strike < s:
                total_payout += (s - test_strike) * p_oi

        if total_payout < min_loss:
            min_loss = total_payout
            max_pain_strike = test_strike

    return max_pain_strike


def generate_synthetic_option_chain(
    symbol: str,
    spot_price: float,
    expiry_days: int = 7,
    num_strikes: int = 15
) -> Dict[str, Any]:
    """
    Generates a structured, mathematically coherent option chain model with Greeks.
    When real NSE / Upstox option chain credentials are provided, live values map seamlessly.
    """
    if spot_price <= 0:
        spot_price = 24000.0 if "NIFTY" in symbol.upper() else 1000.0

    # Determine standard strike interval for Indian instruments
    if "BANK" in symbol.upper():
        step = 100.0
    elif "NIFTY" in symbol.upper():
        step = 50.0
    elif spot_price > 2000:
        step = 50.0
    elif spot_price > 500:
        step = 20.0
    else:
        step = 10.0

    atm_strike = round(spot_price / step) * step
    half = num_strikes // 2
    strikes = [round(atm_strike + (i - half) * step, 1) for i in range(num_strikes)]

    t_years = max(1.0, float(expiry_days)) / 365.0
    base_iv = 0.15 # 15% IV baseline

    chain_rows = []
    call_oi_list = []
    put_oi_list = []

    for s in strikes:
        # Distance from ATM
        dist = abs(s - spot_price) / spot_price
        # Volatility smile
        iv = base_iv + (dist * 0.4)

        # Greeks
        call_g = calculate_option_greeks(spot_price, s, t_years, iv, is_call=True)
        put_g = calculate_option_greeks(spot_price, s, t_years, iv, is_call=False)

        # Realistic OI distribution centered around ATM and round levels
        weight = math.exp(-0.5 * ((s - spot_price) / (step * 2.5)) ** 2)
        c_oi = int(120000 * weight * (1.1 if s >= spot_price else 0.8)) + 15000
        p_oi = int(120000 * weight * (1.1 if s <= spot_price else 0.8)) + 15000

        c_chg_oi = int(c_oi * 0.12 * (1 if s >= spot_price else -0.5))
        p_chg_oi = int(p_oi * 0.12 * (1 if s <= spot_price else -0.5))

        call_oi_list.append(c_oi)
        put_oi_list.append(p_oi)

        chain_rows.append({
            "call_oi": c_oi,
            "call_chg_oi": c_chg_oi,
            "call_volume": int(c_oi * 0.65),
            "call_iv": call_g["iv"],
            "call_delta": call_g["delta"],
            "call_ltp": call_g["price"],
            "strike_price": s,
            "is_atm": bool(s == atm_strike),
            "put_ltp": put_g["price"],
            "put_delta": put_g["delta"],
            "put_iv": put_g["iv"],
            "put_volume": int(p_oi * 0.65),
            "put_chg_oi": p_chg_oi,
            "put_oi": p_oi
        })

    total_call_oi = sum(call_oi_list)
    total_put_oi = sum(put_oi_list)
    pcr = round(total_put_oi / total_call_oi, 2) if total_call_oi > 0 else 1.0

    max_pain = calculate_max_pain(strikes, call_oi_list, put_oi_list)
    
    # Resistance = Strike with highest Call OI
    max_c_idx = call_oi_list.index(max(call_oi_list))
    res_strike = strikes[max_c_idx]

    # Support = Strike with highest Put OI
    max_p_idx = put_oi_list.index(max(put_oi_list))
    sup_strike = strikes[max_p_idx]

    # PCR interpretation
    if pcr >= 1.3:
        pcr_sentiment = "Oversold / Strong Bullish Put Writing Support"
    elif pcr >= 1.0:
        pcr_sentiment = "Moderately Bullish / Put Dominated"
    elif pcr >= 0.7:
        pcr_sentiment = "Neutral / Balanced"
    else:
        pcr_sentiment = "Overbought / Strong Call Writing Resistance"

    return {
        "symbol": symbol,
        "spot_price": spot_price,
        "atm_strike": atm_strike,
        "expiry_days": expiry_days,
        "total_call_oi": total_call_oi,
        "total_put_oi": total_put_oi,
        "pcr": pcr,
        "pcr_sentiment": pcr_sentiment,
        "max_pain_strike": max_pain,
        "major_resistance_strike": res_strike,
        "major_support_strike": sup_strike,
        "chain": chain_rows,
        "disclaimer": FO_DISCLAIMER
    }
