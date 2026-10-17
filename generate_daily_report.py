"""
Daily Report Generator.
Strict Rule: Generates a daily research report ONLY AFTER input data passes all validation checks.
Saves validated Markdown and JSON reports to reports/.
Zero monthly rupee budget.
"""

import os
import sys
import json
from datetime import datetime

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.app.data_providers.csv_provider import CSVDataProvider
from backend.app.data_providers.data_validator import validate_ohlcv_dataframe
from backend.app.engines.swing_scanner import analyze_swing_setup
from backend.app.engines.monthly_research import run_monthly_research_scan
from backend.app.engines.ranking import HEURISTIC_DISCLAIMER
from backend.app.engines.multi_timeframe import analyze_multi_timeframe_context
from backend.app.engines.delivery_tracker import analyze_accumulation_distribution
from backend.app.watchlist.manager import monitor_watchlist_health
from backend.app.alerts.telegram_notifier import format_telegram_alert, send_telegram_alert

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR = os.path.join(PROJECT_ROOT, "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)


def generate_validated_daily_report() -> bool:
    print("=" * 65)
    print("   INDIAN STOCK RESEARCH PLATFORM - DAILY SCAN & REPORT")
    print(f"   Execution Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 65)

    provider = CSVDataProvider()
    symbols = provider.list_available_symbols()

    if not symbols:
        print("[ABORTED] No stock data found in data/stocks/ directory.")
        print("Please run 'python scripts/download_starter_data.py' or import CSVs first.")
        return False

    # 1. DATA VALIDATION GATE
    print("\n[STEP 1] Validating Input Datasets...")
    reports = provider.get_all_validation_reports()
    valid_symbols = []
    stale_symbols = []
    invalid_symbols = []

    for r in reports:
        sym = r["symbol"]
        status = r.get("status", "UNKNOWN")
        if status == "VERIFIED":
            valid_symbols.append(sym)
        elif status == "STALE":
            stale_symbols.append(sym)
            valid_symbols.append(sym)  # Include with warning
        else:
            invalid_symbols.append(sym)

    print(f"  • Verified Datasets: {len(valid_symbols) - len(stale_symbols)}")
    print(f"  • Stale Datasets (warned): {len(stale_symbols)}")
    print(f"  • Invalid / Corrupt Datasets: {len(invalid_symbols)}")

    if not valid_symbols:
        print("\n[CRITICAL ERROR] All datasets failed validation. Report generation aborted to prevent false signals.")
        return False

    # 2. RUN SWING SCAN
    print("\n[STEP 2] Running Swing Scanner on Validated Data...")
    nifty_df = provider.get_historical_data("NIFTY_50")
    if nifty_df.empty:
        nifty_df = provider.get_historical_data("NIFTY 50")

    # Sector scores default
    sec_map = {"IT": 72.0, "BANK": 65.0, "AUTO": 68.0, "ENERGY": 60.0, "FMCG": 58.0, "GENERAL": 60.0}

    swing_results = []
    for sym in valid_symbols:
        if sym in ["NIFTY_50", "NIFTY 50", "^NSEI"]:
            continue
        df = provider.get_historical_data(sym)
        if df.empty or len(df) < 20:
            continue

        stock_info = {"symbol": sym, "name": sym, "sector": "General"}
        setup = analyze_swing_setup(stock_info, df, nifty_df, sec_map, market_score=65.0, data_source="Validated Local CSV")
        swing_results.append(setup)

    swing_results.sort(key=lambda x: x["swing_score"], reverse=True)
    fresh_swings = [s for s in swing_results if s["rsi_fresh_crossover"] and s["swing_score"] >= 60.0]

    # 3. RUN MONTHLY RESEARCH SCAN
    print("\n[STEP 3] Running Monthly Research Scanner...")
    stock_dicts = [{"symbol": sym, "name": sym, "sector": "General"} for sym in valid_symbols if sym not in ["NIFTY_50", "NIFTY 50", "^NSEI"]]
    monthly_data = run_monthly_research_scan(stock_dicts, provider)

    # 4. EXPORT REPORT
    today_str = datetime.now().strftime("%Y-%m-%d")
    json_path = os.path.join(REPORTS_DIR, f"daily_report_{today_str}.json")
    md_path = os.path.join(REPORTS_DIR, f"daily_report_{today_str}.md")

    report_payload = {
        "report_date": today_str,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "validation_summary": {
            "total_datasets": len(reports),
            "verified": len(valid_symbols) - len(stale_symbols),
            "stale": len(stale_symbols),
            "invalid": len(invalid_symbols)
        },
        "fresh_swing_signals": fresh_swings,
        "top_swing_ranked": swing_results[:10],
        "monthly_summary": {
            "buy_candidates": len(monthly_data["buy_candidates"]),
            "hold_candidates": len(monthly_data["hold_candidates"]),
            "exit_reviews": len(monthly_data["exit_reviews"])
        },
        "disclaimer": HEURISTIC_DISCLAIMER
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_payload, f, indent=2)

    # Write Markdown Report
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# Indian Stock Research Platform — Daily EOD Report\n\n")
        f.write(f"**Generated:** {report_payload['generated_at']} | **Date:** {today_str}\n\n")
        f.write(f"> **Validation Gate:** {report_payload['validation_summary']['verified']} Verified Datasets, {report_payload['validation_summary']['stale']} Stale (Flagged), {report_payload['validation_summary']['invalid']} Rejected.\n\n")

        f.write("## 1. ⚡ Fresh Swing Crossover Signals (Completed Candles Only)\n\n")
        if fresh_swings:
            f.write("| Symbol | Price | Swing Score | RSI(14) | Vol Ratio | 52W High Dist | Stop Loss | Target 1 |\n")
            f.write("|:---|:---|:---|:---|:---|:---|:---|:---|\n")
            for s in fresh_swings:
                f.write(f"| **{s['symbol']}** | ₹{s['price']} | {s['swing_score']}/100 | {s['rsi_value']} (Fresh) | {s['vol_ratio']}x | -{s['dist_from_52w_high_pct']}% | ₹{s['reference_levels']['stop_loss_reference']} | ₹{s['reference_levels']['target_1_reference']} |\n")
        else:
            f.write("_No fresh RSI crossovers triggered today. Only disciplined setups passing all rules are displayed._\n\n")

        f.write("\n## 2. 🏆 Top Quantitative Swing Candidates\n\n")
        f.write("| Symbol | Price | Trend | Momentum | Safety | Composite Score | Classification |\n")
        f.write("|:---|:---|:---|:---|:---|:---|:---|\n")
        for s in swing_results[:8]:
            rk = s.get("ranking", {})
            f.write(f"| **{s['symbol']}** | ₹{s['price']} | {rk.get('trend_score', '-')} | {rk.get('momentum_score', '-')} | {rk.get('safety_score', '-')} | **{rk.get('composite_score', s['swing_score'])}/100** | {s['classification']} |\n")

        f.write(f"\n## 3. ⚠️ Disclaimer\n\n_{HEURISTIC_DISCLAIMER}_\n")

    # 5. Generate Zero-Cost Telegram Alert Preview
    wl_status = monitor_watchlist_health(provider)
    tg_msg = format_telegram_alert(fresh_swings, wl_status)
    tg_res = send_telegram_alert(tg_msg)

    print(f"\n[SUCCESS] Daily report generated successfully:")
    print(f"  • JSON: {json_path}")
    print(f"  • Markdown: {md_path}")
    if tg_res.get("preview_file"):
        print(f"  • Telegram Alert Preview: {tg_res['preview_file']}")
    print("=" * 65)
    return True


if __name__ == "__main__":
    success = generate_validated_daily_report()
    if not success:
        sys.exit(1)
