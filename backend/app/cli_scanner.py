import os
import sys
import json
from datetime import datetime

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


from backend.app.data_providers.factory import get_market_data_provider
from backend.app.universe.universes import get_universe_stocks
from backend.app.engines.swing_scanner import analyze_swing_setup
from backend.app.engines.market_trend import analyze_market_trend
from backend.app.engines.sector_trend import analyze_sector_trends
from backend.app.engines.monthly_research import run_monthly_research_scan

def run_eod_scan():
    print("=" * 60)
    print("   INDIAN STOCK RESEARCH TOOL - END OF DAY SCAN")
    print(f"   Execution Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    provider = get_market_data_provider()
    print(f"Active Provider: {provider.get_provider_name()}\n")

    stocks = get_universe_stocks("NIFTY 50")
    nifty_df = provider.get_historical_data("NIFTY 50", period="1y", interval="day")
    mkt = analyze_market_trend(provider)
    sectors = analyze_sector_trends(provider, nifty_df)
    sec_map = {s["sector_name"].upper(): s["sector_score"] for s in sectors}

    print(f"NIFTY 50 Market Score: {mkt['market_score']}/100 ({mkt['classification']})")

    # 1. Swing Scan
    print("\n>>> Running Swing Trading Scan...")
    swing_results = []
    for s in stocks:
        df = provider.get_historical_data(s["symbol"], period="1y", interval="day")
        if df.empty or len(df) < 20:
            continue
        setup = analyze_swing_setup(s, df, nifty_df, sec_map, mkt["market_score"])
        swing_results.append(setup)

    swing_results.sort(key=lambda x: x["swing_score"], reverse=True)
    top_swings = [s for s in swing_results if s["swing_score"] >= 65.0]

    print(f"Found {len(top_swings)} Confirmed Swing Candidates:")
    for s in top_swings[:5]:
        cross_flag = "⚡ FRESH CROSS" if s["rsi_fresh_crossover"] else ""
        vol_flag = f"🔥 VOL {s['vol_ratio']}x" if s["volume_breakout"] else ""
        print(f"  • {s['symbol']:<12} Price: ₹{s['price']:<8} Score: {s['swing_score']}/100  {cross_flag}  {vol_flag}")

    # 2. Monthly Research Scan
    print("\n>>> Running Monthly Stock Research...")
    monthly_data = run_monthly_research_scan(stocks, provider)
    buys = monthly_data["buy_candidates"]
    holds = monthly_data["hold_candidates"]
    exits = monthly_data["exit_reviews"]

    print(f"Monthly Summary: Buy: {len(buys)} | Hold: {len(holds)} | Exit Review: {len(exits)}")
    if buys:
        print("\nTop Monthly Buy Candidates:")
        for b in buys[:3]:
            f = b["fundamental_summary"]
            print(f"  • {b['symbol']:<12} Score: {b['score']}/100 | ROCE: {f['roce']}% | ROE: {f['roe']}% | 52W Dist: -{b['technical_summary']['dist_52w_pct']}%")

    # Save output to markdown & JSON
    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "reports")
    os.makedirs(out_dir, exist_ok=True)
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    report_file = os.path.join(out_dir, f"scan_report_{today_str}.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "provider": provider.get_provider_name(),
            "market_score": mkt["market_score"],
            "top_swing_candidates": top_swings[:10],
            "monthly_buy_candidates": buys[:10]
        }, f, indent=2)

    print(f"\n[OK] Scan report saved to: {report_file}")
    print("=" * 60)

if __name__ == "__main__":
    run_eod_scan()
