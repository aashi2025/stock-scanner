"""
Black-Scholes Option Pricing and Greek Sensitivities Calculator.
Calculates: Delta, Gamma, Theta, Vega, and Implied Volatility (IV).
For educational and quantitative positioning analytics in Indian equity derivatives.
"""

import math
from typing import Dict, Any, Optional

def norm_cdf(x: float) -> float:
    """Standard normal cumulative distribution function approximation."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

def norm_pdf(x: float) -> float:
    """Standard normal probability density function."""
    return (1.0 / math.sqrt(2.0 * math.pi)) * math.exp(-0.5 * x * x)

def calculate_option_greeks(
    spot: float,
    strike: float,
    time_to_expiry_years: float,
    volatility: float = 0.18, # 18% IV
    risk_free_rate: float = 0.065, # 6.5% RBI repo baseline
    is_call: bool = True
) -> Dict[str, float]:
    """
    Computes Black-Scholes theoretical price and Greeks (Delta, Gamma, Theta, Vega).
    """
    if spot <= 0 or strike <= 0 or time_to_expiry_years <= 0 or volatility <= 0:
        return {
            "price": 0.0,
            "delta": 0.5 if is_call else -0.5,
            "gamma": 0.0,
            "theta": 0.0,
            "vega": 0.0,
            "iv": volatility
        }

    t = time_to_expiry_years
    r = risk_free_rate
    sigma = volatility

    d1 = (math.log(spot / strike) + (r + 0.5 * sigma * sigma) * t) / (sigma * math.sqrt(t))
    d2 = d1 - sigma * math.sqrt(t)

    # Price
    if is_call:
        price = spot * norm_cdf(d1) - strike * math.exp(-r * t) * norm_cdf(d2)
        delta = norm_cdf(d1)
    else:
        price = strike * math.exp(-r * t) * norm_cdf(-d2) - spot * norm_cdf(-d1)
        delta = norm_cdf(d1) - 1.0

    gamma = norm_pdf(d1) / (spot * sigma * math.sqrt(t))
    
    # 1-day theta
    term1 = -(spot * norm_pdf(d1) * sigma) / (2.0 * math.sqrt(t))
    if is_call:
        theta_yr = term1 - r * strike * math.exp(-r * t) * norm_cdf(d2)
    else:
        theta_yr = term1 + r * strike * math.exp(-r * t) * norm_cdf(-d2)
    theta_1d = theta_yr / 365.0

    # 1% vega
    vega_1pct = (spot * math.sqrt(t) * norm_pdf(d1)) / 100.0

    return {
        "price": round(max(0.0, price), 2),
        "delta": round(delta, 3),
        "gamma": round(gamma, 5),
        "theta": round(theta_1d, 2),
        "vega": round(vega_1pct, 2),
        "iv": round(volatility * 100.0, 2)
    }


def estimate_implied_volatility(
    market_price: float,
    spot: float,
    strike: float,
    time_to_expiry_years: float,
    is_call: bool = True,
    risk_free_rate: float = 0.065
) -> float:
    """
    Bisection algorithm to solve for Implied Volatility given a market option price.
    Returns IV as percentage (e.g. 18.5%).
    """
    if market_price <= 0 or spot <= 0 or strike <= 0 or time_to_expiry_years <= 0:
        return 18.0

    low_vol = 0.01
    high_vol = 2.50
    target = market_price

    for _ in range(25): # 25 iterations for high precision
        mid_vol = (low_vol + high_vol) / 2.0
        g = calculate_option_greeks(spot, strike, time_to_expiry_years, mid_vol, risk_free_rate, is_call)
        diff = g["price"] - target

        if abs(diff) < 0.05:
            return round(mid_vol * 100.0, 2)
        elif diff > 0:
            high_vol = mid_vol
        else:
            low_vol = mid_vol

    return round(mid_vol * 100.0, 2)
