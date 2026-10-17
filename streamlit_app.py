"""
Indian Stock Research Platform — Zero-Budget Mobile-Friendly Dashboard (Phase 2).
Built with Streamlit, Pandas, NumPy, and Plotly for zero-rupee monthly cost.
Phase 2 Additions:
- Multi-Timeframe Weekly Confirmation
- Delivery Volume & Smart Money Accumulation Tracker
- Multi-Stock Portfolio Backtesting Simulator (Sharpe, Sortino, Cash Curve)
- Interactive Plotly Candlestick & RSI Charts
- Personal Watchlist & Setup Invalidation Monitor
- Zero-Cost Telegram Alert Dispatcher & Local Preview
"""

import os
import sys
import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime, date

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.app.data_providers.factory import get_market_data_provider
from backend.app.data_providers.csv_provider import CSVDataProvider
from backend.app.data_providers.upstox import UpstoxDataProvider
from backend.app.config_updater import save_upstox_credentials, get_current_upstox_credentials
from backend.app.engines.swing_scanner import analyze_swing_setup
from backend.app.engines.market_trend import analyze_market_trend
from backend.app.engines.sector_trend import analyze_sector_trends
from backend.app.engines.monthly_research import run_monthly_research_scan
from backend.app.engines.ranking import compute_composite_ranking, HEURISTIC_DISCLAIMER
from backend.app.engines.backtest import run_historical_backtest
from backend.app.engines.portfolio_backtest import run_portfolio_backtest
from backend.app.engines.multi_timeframe import analyze_multi_timeframe_context
from backend.app.engines.delivery_tracker import analyze_accumulation_distribution
from backend.app.watchlist.manager import add_to_watchlist, remove_from_watchlist, monitor_watchlist_health, load_watchlist
from backend.app.alerts.telegram_notifier import format_telegram_alert, send_telegram_alert
from backend.app.charts.plotly_charts import create_candlestick_chart, create_portfolio_equity_chart
from backend.app.momentum_pro.ui import render_momentum_pro_page

# Page Configuration
st.set_page_config(
    page_title="Indian Stock Research Platform (Phase 2)",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for Mobile & Desktop UX
st.markdown("""
<style>
    .main-header {
        font-size: 1.85rem;
        font-weight: 700;
        color: #0F172A;
        margin-bottom: 0.15rem;
    }
    .sub-header {
        font-size: 0.95rem;
        color: #475569;
        margin-bottom: 1.2rem;
    }
    .badge-fresh {
        background-color: #DCFCE7;
        color: #166534;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.82rem;
        font-weight: 600;
        display: inline-block;
    }
    .badge-mtf {
        background-color: #EDE9FE;
        color: #5B21B6;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.82rem;
        font-weight: 600;
        display: inline-block;
    }
    .badge-acc {
        background-color: #E0F2FE;
        color: #0369A1;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.82rem;
        font-weight: 600;
        display: inline-block;
    }
    .metric-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 14px;
        margin-bottom: 10px;
    }
    .disclaimer-box {
        background-color: #F1F5F9;
        border-left: 4px solid #3B82F6;
        padding: 10px 14px;
        border-radius: 4px;
        font-size: 0.82rem;
        color: #475569;
        margin-top: 15px;
    }
</style>
""", unsafe_allow_html=True)


# Sidebar Configuration
st.sidebar.title("🇮🇳 Stock Research Tool")
st.sidebar.caption("Phase 2 — Advanced Quantitative Platform")

current_creds = get_current_upstox_credentials()

provider_options = [
    "Upstox API v2 (Official NSE Feed)",
    "Local CSV Storage (Verified)",
    "Yahoo Finance (Free Live NSE)",
    "Explicit Sample Mode"
]

default_idx = 0 if current_creds.get("provider") == "upstox" else 1

provider_choice = st.sidebar.selectbox(
    "Market Data Provider (डेटा स्रोत)",
    provider_options,
    index=default_idx
)

if provider_choice == "Upstox API v2 (Official NSE Feed)":
    provider = UpstoxDataProvider()
elif provider_choice == "Local CSV Storage (Verified)":
    provider = CSVDataProvider()
elif provider_choice == "Yahoo Finance (Free Live NSE)":
    provider = get_market_data_provider("yahoo")
else:
    provider = get_market_data_provider("sample", force_sample=True)

st.sidebar.markdown(f"**सक्रिय स्रोत:** `{provider.get_provider_name()}`")

# Upstox API Credentials Manager in Sidebar
with st.sidebar.expander("🔑 Upstox API Key & Token", expanded=(provider_choice.startswith("Upstox"))):
    up_key = st.text_input("Upstox API Key", value=current_creds.get("api_key", ""), type="password", key="sb_up_key")
    up_secret = st.text_input("Upstox API Secret", value=current_creds.get("api_secret", ""), type="password", key="sb_up_secret")
    up_token = st.text_input("Daily Access Token", value=current_creds.get("access_token", ""), type="password", help="Upstox Developer Console से कॉपी किया गया टोकन", key="sb_up_token")

    c_up1, c_up2 = st.columns(2)
    if c_up1.button("💾 Save", use_container_width=True, key="btn_save_upstox"):
        save_upstox_credentials(up_key, up_secret, up_token, set_as_default_provider=True)
        st.success("✅ Credentials .env में सेव हो गए!")
        st.rerun()

    if c_up2.button("🔌 Test", use_container_width=True, key="btn_test_upstox"):
        test_prov = UpstoxDataProvider(access_token=up_token or current_creds.get("access_token"))
        status = test_prov.verify_token_status()
        if status.get("valid"):
            st.success(f"🟢 कनेक्टेड! यूज़र: {status.get('user_name', 'Upstox User')}")
        else:
            st.warning(f"🟡 {status.get('reason')}")

    st.markdown("[🔗 Open Upstox Developer Apps](https://account.upstox.com/developer/apps)")


st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Scoring Weights (वजन)")
w_trend = st.sidebar.slider("Trend Weight", 0.0, 1.0, 0.30, 0.05)
w_mom = st.sidebar.slider("Momentum Weight", 0.0, 1.0, 0.30, 0.05)
w_fund = st.sidebar.slider("Quality Weight", 0.0, 1.0, 0.20, 0.05)
w_val = st.sidebar.slider("Valuation Weight", 0.0, 1.0, 0.10, 0.05)
w_safety = st.sidebar.slider("Safety Weight", 0.0, 1.0, 0.10, 0.05)

custom_weights = {
    "trend": w_trend, "momentum": w_mom,
    "fundamental": w_fund, "valuation": w_val, "safety": w_safety
}

st.sidebar.markdown("---")
st.sidebar.subheader("📱 Quick Actions")
if st.sidebar.button("📢 Generate Telegram Alert"):
    st.session_state["show_alert_modal"] = True

st.sidebar.info("💡 **Hinglish Advice:** Phase 2 में मल्टी-टाइमफ्रेम (साप्ताहिक + दैनिक) दोनों की पुष्टि के बाद ही हाई-कॉन्विक्शन सेटअप बनता है।")

# Session State for View Navigation (Preserves selection across reruns)
if "current_view" not in st.session_state:
    st.session_state["current_view"] = "scanner"

# Available Symbols
available_syms = []
if hasattr(provider, "list_available_symbols"):
    available_syms = provider.list_available_symbols()
if not available_syms:
    available_syms = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ITC", "MARUTI", "ICICIBANK", "BHARTIARTL", "SBIN", "LT"]

# Top Header & Navigation Bar
top_c1, top_c2 = st.columns([3, 1])
with top_c1:
    st.markdown("<div class='main-header'>📈 Indian Stock Research Platform — Phase 2</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-header'>Multi-timeframe confirmation, smart money accumulation tracking, portfolio backtesting, and interactive charting.</div>", unsafe_allow_html=True)

with top_c2:
    if st.session_state["current_view"] == "scanner":
        if st.button("🚀 Momentum Pro", type="primary", use_container_width=True, key="btn_open_momentum_pro"):
            st.session_state["current_view"] = "momentum_pro"
            st.rerun()
    else:
        if st.button("← Back to Old Scanner", use_container_width=True, key="btn_top_back"):
            st.session_state["current_view"] = "scanner"
            st.rerun()

# Render View Based on Selection
if st.session_state["current_view"] == "momentum_pro":
    render_momentum_pro_page(provider, available_syms)
    st.stop()

# ==========================================
# OLD SCANNER VIEW (100% UNCHANGED & PRESERVED)
# ==========================================

# Main Navigation Tabs
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📊 Market Overview",
    "⚡ Fresh Swing Signals",
    "📅 Monthly Candidates",
    "🔍 Stock Details & Chart",
    "🧪 Portfolio & Single Backtest",
    "📌 Watchlist & Alerts",
    "🏥 Data Health"
])


# ==========================================
# TAB 1: MARKET OVERVIEW
# ==========================================
with tab1:
    st.subheader("1. NIFTY 50 Macro Regime & Health")
    col1, col2, col3, col4 = st.columns(4)

    try:
        mkt = analyze_market_trend(provider)
        col1.metric("NIFTY 50 Price", f"₹{mkt.get('price', 0.0):,.2f}", f"{mkt.get('change_percent', 0.0)}%")
        col2.metric("Market Score", f"{mkt.get('market_score', 0.0)}/100", mkt.get("classification", "Neutral"))
        col3.metric("50 EMA", f"₹{mkt.get('ema_50', 0.0):,.2f}", "Above 50 EMA" if mkt.get("price_above_50_ema") else "Below 50 EMA")
        col4.metric("200 EMA", f"₹{mkt.get('ema_200', 0.0):,.2f}", "Bullish Regime" if mkt.get("price_above_200_ema") else "Bearish Regime")
    except Exception as e:
        st.warning(f"Unable to load NIFTY 50 trend: {e}")

    st.markdown("---")
    st.subheader("2. Sectoral Performance & Strength Map")
    try:
        nifty_df = provider.get_historical_data("NIFTY 50")
        if nifty_df.empty:
            nifty_df = provider.get_historical_data("NIFTY_50")
        sectors = analyze_sector_trends(provider, nifty_df)
        if sectors:
            sec_df = pd.DataFrame([
                {
                    "Sector": s["sector_name"],
                    "Price (₹)": s["price"],
                    "Change %": f"{s['change_percent']}%",
                    "Score / 100": s["sector_score"],
                    "Trend Regime": s["classification"],
                    "Above 50 EMA": "✅ Yes" if s["above_50_ema"] else "❌ No",
                    "Above 200 EMA": "✅ Yes" if s["above_200_ema"] else "❌ No"
                }
                for s in sectors
            ])
            st.dataframe(sec_df, use_container_width=True)
    except Exception as e:
        st.info(f"Sector data: {e}")

    st.markdown(f"<div class='disclaimer-box'><b>Research Heuristic:</b> {HEURISTIC_DISCLAIMER}</div>", unsafe_allow_html=True)


# ==========================================
# TAB 2: FRESH SWING SIGNALS
# ==========================================
with tab2:
    st.subheader("⚡ Swing Scanner (Fresh RSI Crossovers + Phase 2 MTF Confirmation)")
    st.markdown(r"""
    **नियम (Multi-Stage Rules):**
    1. **Fresh Crossover:** पिछली पूर्ण कैंडल पर $\text{RSI}(14) \le 50$ और ताज़ा कैंडल पर $> 50$।
    2. **Trend:** $\text{Price} > 50\text{ EMA} > 200\text{ EMA}$।
    3. **Volume:** वॉल्यूम $\ge 1.2x$ 20-दिन औसत।
    4. **Phase 2 MTF (साप्ताहिक):** साप्ताहिक क्लोजिंग $> 20\text{ EMA}$ और साप्ताहिक $\text{RSI} > 50$।
    """)

    col_f1, col_f2, col_f3 = st.columns([2, 1, 1])
    min_score_filter = col_f1.slider("Minimum Swing Score", 40.0, 95.0, 60.0, 5.0)
    fresh_only_filter = col_f2.checkbox("⚡ Only Fresh Crossovers", value=True)
    require_mtf_bullish = col_f3.checkbox("🎯 Weekly MTF Confirmed Only", value=False)

    swing_rows = []
    sec_map = {"IT": 72.0, "BANK": 65.0, "AUTO": 68.0, "ENERGY": 60.0, "FMCG": 58.0, "GENERAL": 60.0}
    nifty_df = provider.get_historical_data("NIFTY 50")
    if nifty_df.empty:
        nifty_df = provider.get_historical_data("NIFTY_50")

    with st.spinner("Scanning universe with Multi-Timeframe and Accumulation analysis..."):
        for sym in available_syms:
            if sym in ["NIFTY 50", "NIFTY_50", "^NSEI"]:
                continue
            df = provider.get_historical_data(sym)
            if df.empty or len(df) < 30:
                continue
            stock_meta = {"symbol": sym, "name": sym, "sector": "General"}
            res = analyze_swing_setup(stock_meta, df, nifty_df, sec_map, market_score=65.0, custom_weights=custom_weights)

            # Phase 2: Add MTF and Accumulation analysis
            mtf_info = analyze_multi_timeframe_context(df)
            acc_info = analyze_accumulation_distribution(df)
            res["mtf"] = mtf_info
            res["accumulation"] = acc_info

            if fresh_only_filter and not res["rsi_fresh_crossover"]:
                continue
            if require_mtf_bullish and not mtf_info.get("weekly_trend_bullish"):
                continue
            if res["swing_score"] < min_score_filter:
                continue

            swing_rows.append(res)

    if swing_rows:
        st.success(f"कुल {len(swing_rows)} स्टॉक्स ने नियमों को पूरा किया:")
        for s in swing_rows:
            mtf = s["mtf"]
            acc = s["accumulation"]
            with st.expander(f"📌 {s['symbol']} — Score: {s['swing_score']}/100 | ₹{s['price']} ({s['classification']})", expanded=True):
                col_tags1, col_tags2, col_tags3 = st.columns(3)
                col_tags1.markdown(f"<span class='badge-fresh'>⚡ Fresh RSI Cross ({s['rsi_value']})</span>", unsafe_allow_html=True)
                col_tags2.markdown(f"<span class='badge-mtf'>📅 {mtf['mtf_status']}</span>", unsafe_allow_html=True)
                col_tags3.markdown(f"<span class='badge-acc'>🏦 {acc['status']}</span>", unsafe_allow_html=True)

                c1, c2, c3, c4 = st.columns(4)
                c1.markdown(f"**Volume Surge:** `{s['vol_ratio']}x 20-DMA`")
                c2.markdown(f"**52W High Distance:** `-{s['dist_from_52w_high_pct']}%`")
                c3.markdown(f"**Weekly 20 EMA:** `₹{mtf.get('weekly_ema_20', '-')}`")
                c4.markdown(f"**Candle Date:** `{s['candle_timestamp']}`")

                ref = s["reference_levels"]
                st.markdown(f"""
                **Analytical Reference Levels:**
                - **Ref Entry:** ₹{ref['entry_reference']} | **Stop Loss:** ₹{ref['stop_loss_reference']} (Risk: ₹{ref['risk_per_share']})
                - **Target 1 (1:2 RR):** ₹{ref['target_1_reference']} | **Target 2 (1:3 RR):** ₹{ref['target_2_reference']}
                """)

                # Add to watchlist button
                if st.button(f"⭐ Add {s['symbol']} to Watchlist", key=f"btn_wl_{s['symbol']}"):
                    add_to_watchlist(s['symbol'], company_name=s['company_name'], notes="Fresh Swing Setup")
                    st.success(f"{s['symbol']} वॉचलिस्ट में जोड़ा गया!")
    else:
        st.warning("वर्तमान फिल्टर्स पर कोई नया सिग्नल नहीं मिला।")


# ==========================================
# TAB 3: MONTHLY CANDIDATES
# ==========================================
with tab3:
    st.subheader("📅 Monthly Research Candidates")
    stock_items = [{"symbol": sym, "name": sym, "sector": "General"} for sym in available_syms if sym not in ["NIFTY 50", "NIFTY_50", "^NSEI"]]
    monthly_res = run_monthly_research_scan(stock_items, provider)

    sub_t1, sub_t2, sub_t3 = st.tabs([
        f"🟢 Buy Candidates ({len(monthly_res['buy_candidates'])})",
        f"🔵 Hold Candidates ({len(monthly_res['hold_candidates'])})",
        f"🔴 Exit Reviews ({len(monthly_res['exit_reviews'])})"
    ])

    with sub_t1:
        if monthly_res["buy_candidates"]:
            for b in monthly_res["buy_candidates"]:
                f = b["fundamental_summary"]
                st.markdown(f"### {b['symbol']} (Score: {b['score']}/100) — ₹{b['price']}")
                st.markdown(f"**Action Plan:** {b['action_plan']}")
                col_a, col_b, col_c = st.columns(3)
                col_a.metric("ROCE", f"{f.get('roce')}%" if f.get("roce") else "N/A (अपुष्ट)")
                col_b.metric("ROE", f"{f.get('roe')}%" if f.get("roe") else "N/A (अपुष्ट)")
                col_c.metric("Debt/Equity", f"{f.get('debt_to_equity')}" if f.get("debt_to_equity") is not None else "N/A (अपुष्ट)")
                st.caption(f"डेटा सोर्स: {f.get('data_source')}")
                st.divider()
        else:
            st.info("कोई Buy Candidate नहीं मिला। केवल उच्चतम गुणवत्ता वाले स्टॉक्स ही चयनित होते हैं।")

    with sub_t2:
        for h in monthly_res["hold_candidates"]:
            st.markdown(f"**{h['symbol']}** — ₹{h['price']} (Score: {h['score']}/100) | Plan: _{h['action_plan']}_")

    with sub_t3:
        for e in monthly_res["exit_reviews"]:
            st.markdown(f"⚠️ **{e['symbol']}** — ₹{e['price']} (Score: {e['score']}/100) | Reason: _{e['action_plan']}_")


# ==========================================
# TAB 4: STOCK DETAILS & PLOTLY CHART
# ==========================================
with tab4:
    st.subheader("🔍 Stock Details & Interactive Candlestick Chart (Phase 2)")
    selected_stock = st.selectbox("Select Stock to Analyze", [s for s in available_syms if s not in ["NIFTY 50", "NIFTY_50", "^NSEI"]])

    if selected_stock:
        df_stock = provider.get_historical_data(selected_stock)
        if not df_stock.empty and len(df_stock) >= 20:
            quote = provider.get_quote(selected_stock)

            # Interactive Plotly Candlestick Chart
            ref_lvl = {
                "entry_reference": quote.get("price"),
                "stop_loss_reference": round(quote.get("price", 0) * 0.95, 2),
                "target_1_reference": round(quote.get("price", 0) * 1.10, 2)
            }
            candlestick_fig = create_candlestick_chart(df_stock, symbol=selected_stock, reference_levels=ref_lvl)
            st.plotly_chart(candlestick_fig, use_container_width=True)

            # Phase 2 MTF and Smart Money badges
            mtf_stock = analyze_multi_timeframe_context(df_stock)
            acc_stock = analyze_accumulation_distribution(df_stock)

            mb1, mb2, mb3 = st.columns(3)
            mb1.markdown("<div class='metric-card'>", unsafe_allow_html=True)
            mb1.markdown(f"**Weekly MTF Context:** {mtf_stock['mtf_status']}")
            mb1.caption(f"Weekly 20 EMA: ₹{mtf_stock.get('weekly_ema_20')} | Weekly RSI: {mtf_stock.get('weekly_rsi')}")
            mb1.markdown("</div>", unsafe_allow_html=True)

            mb2.markdown("<div class='metric-card'>", unsafe_allow_html=True)
            mb2.markdown(f"**Institutional Accumulation:** {acc_stock['status']}")
            mb2.caption(f"Close Location Value (CLV): {acc_stock.get('close_location_value')} | OBV: {'Expanding' if acc_stock.get('obv_trending_up') else 'Flat'}")
            mb2.markdown("</div>", unsafe_allow_html=True)

            mb3.markdown("<div class='metric-card'>", unsafe_allow_html=True)
            mb3.markdown(f"**Data Health:** `{quote.get('data_status', 'VERIFIED')}`")
            mb3.caption(f"Source: {quote.get('data_source')} | Date: {quote.get('timestamp')}")
            mb3.markdown("</div>", unsafe_allow_html=True)


# ==========================================
# TAB 5: BACKTEST (PORTFOLIO & SINGLE)
# ==========================================
with tab5:
    st.subheader("🧪 Backtesting Engine — Phase 2 Portfolio & Single Simulation")
    bt_mode = st.radio("Backtest Simulation Mode", ["Multi-Stock Portfolio Simulation (Phase 2)", "Single Stock Analysis (Phase 1)"], horizontal=True)

    if bt_mode == "Multi-Stock Portfolio Simulation (Phase 2)":
        st.markdown("""
        **पोर्टफोलियो सिमुलेशन नियम:**
        - पूरे पोर्टफोलियो (₹5,00,000) पर एक साथ 5 स्टॉक्स तक की पोजीशन लिमिट।
        - कैश रिज़र्व मैनेजमेंट, रैंकिंग प्राथमिकता, और सभी भारतीय टैक्स व स्लिपेज।
        """)
        pc1, pc2, pc3, pc4 = st.columns(4)
        p_cap = pc1.number_input("Portfolio Capital (₹)", 100000.0, 5000000.0, 500000.0, 50000.0)
        p_slots = pc2.slider("Max Concurrent Positions", 2, 10, 5)
        p_sl = pc3.number_input("Portfolio Stop Loss %", 1.0, 15.0, 5.0, 0.5)
        p_tg = pc4.number_input("Portfolio Target %", 3.0, 30.0, 12.0, 1.0)

        if st.button("🚀 Run Portfolio Backtest"):
            with st.spinner("Simulating multi-stock portfolio execution..."):
                p_res = run_portfolio_backtest(
                    provider=provider,
                    symbols=available_syms,
                    start_date="2023-01-01",
                    end_date="2026-10-15",
                    initial_capital=p_cap,
                    max_positions=p_slots,
                    stop_loss_pct=p_sl,
                    target_pct=p_tg
                )

            if "error" not in p_res:
                pm1, pm2, pm3, pm4, pm5 = st.columns(5)
                pm1.metric("Portfolio CAGR", f"{p_res['cagr_pct']}%", f"vs NIFTY {p_res['benchmark_nifty_cagr']}%")
                pm2.metric("Sharpe Ratio", f"{p_res['sharpe_ratio']}")
                pm3.metric("Sortino Ratio", f"{p_res['sortino_ratio']}")
                pm4.metric("Max Drawdown", f"-{p_res['max_drawdown_pct']}%")
                pm5.metric("Win Rate", f"{p_res['win_rate_pct']}% ({p_res['total_trades']} Trades)")

                # Plotly Portfolio Equity Curve
                if p_res["equity_curve"]:
                    eq_fig = create_portfolio_equity_chart(p_res["equity_curve"], p_cap)
                    st.plotly_chart(eq_fig, use_container_width=True)

                if p_res["closed_trades"]:
                    st.markdown("### 📋 Closed Portfolio Trade Log")
                    st.dataframe(pd.DataFrame(p_res["closed_trades"]), use_container_width=True)
            else:
                st.error(p_res["error"])

    else:
        # Single stock backtest
        b_col1, b_col2, b_col3, b_col4 = st.columns(4)
        bt_stop_loss = b_col1.number_input("Stop Loss %", 1.0, 15.0, 5.0, 0.5, key="sb_sl")
        bt_target = b_col2.number_input("Target %", 2.0, 30.0, 12.0, 1.0, key="sb_tg")
        bt_slippage = b_col3.number_input("Slippage %", 0.0, 2.0, 0.2, 0.05, key="sb_slip")
        bt_capital = b_col4.number_input("Capital per trade (₹)", 10000.0, 200000.0, 50000.0, 5000.0, key="sb_cap")

        if st.button("▶️ Run Single Stock Historical Backtest"):
            with st.spinner("Simulating trades..."):
                bt_res = run_historical_backtest(
                    provider=provider,
                    symbols=available_syms,
                    start_date="2023-01-01",
                    end_date="2026-10-15",
                    stop_loss_pct=bt_stop_loss,
                    target_pct=bt_target,
                    slippage_pct=bt_slippage,
                    capital_per_trade=bt_capital
                )

            mc1, mc2, mc3, mc4 = st.columns(4)
            mc1.metric("Win Rate", f"{bt_res['win_rate_pct']}%")
            mc2.metric("Total Trades", f"{bt_res['total_trades']}")
            mc3.metric("Strategy CAGR", f"{bt_res['cagr_pct']}%")
            mc4.metric("Max Drawdown", f"-{bt_res['max_drawdown_pct']}%")

            if bt_res["trades"]:
                st.dataframe(pd.DataFrame(bt_res["trades"]), use_container_width=True)


# ==========================================
# TAB 6: WATCHLIST & INVALIDATION ALERTS
# ==========================================
with tab6:
    st.subheader("📌 Personal Watchlist & Setup Invalidation Monitor")
    st.markdown("""
    **सेटअप इनवैलिडेशन मॉनिटर:** यदि वॉचलिस्ट का कोई स्टॉक 50 EMA के नीचे टूटता है या RSI 45 के नीचे जाता है, तो यह चेतावनी देता है।
    """)

    wl_mon = monitor_watchlist_health(provider)
    if wl_mon:
        for w in wl_mon:
            with st.container():
                wc1, wc2, wc3 = st.columns([2, 2, 1])
                wc1.markdown(f"**{w['symbol']}** — ₹{w['price']}")
                wc1.caption(f"Notes: {w.get('notes', '-')}")

                if w["is_invalidated"]:
                    wc2.markdown(f"<span class='badge-alert'>{w['status']}</span>", unsafe_allow_html=True)
                    for wrn in w["warnings"]:
                        wc2.caption(f"• ⚠️ {wrn}")
                else:
                    wc2.markdown(f"<span class='badge-fresh'>{w['status']}</span>", unsafe_allow_html=True)
                    wc2.caption(f"50 EMA: ₹{w['ema_50']} | RSI: {w['rsi_14']}")

                if wc3.button("🗑️ Remove", key=f"del_wl_{w['symbol']}"):
                    remove_from_watchlist(w['symbol'])
                    st.rerun()
                st.divider()
    else:
        st.info("आपकी वॉचलिस्ट खाली है। 'Fresh Swing Signals' टैब से स्टॉक्स जोड़ें।")


# ==========================================
# TAB 7: DATA HEALTH
# ==========================================
with tab7:
    st.subheader("🏥 Data Health, Verification & Import")
    if hasattr(provider, "get_all_validation_reports"):
        reports = provider.get_all_validation_reports()
        if reports:
            health_table = [
                {
                    "Symbol": r["symbol"],
                    "Status": r.get("status", "UNKNOWN"),
                    "Total Records": r.get("total_records", 0),
                    "Start Date": r.get("date_range", {}).get("start", "-"),
                    "Latest Date": r.get("date_range", {}).get("end", "-"),
                    "Latest Close (₹)": r.get("latest_close", 0.0),
                    "Data Source": r.get("data_source", "-")
                }
                for r in reports
            ]
            st.dataframe(pd.DataFrame(health_table), use_container_width=True)

    st.markdown("---")
    st.subheader("📥 Import Daily OHLCV CSV File")
    uploaded_file = st.file_uploader("Upload CSV File (`Date, Open, High, Low, Close, Volume`)", type=["csv"])
    stock_input_symbol = st.text_input("Stock Symbol (e.g. RELIANCE, TATAMOTORS, NIFTY_50):").strip().upper()

    if uploaded_file and stock_input_symbol and st.button("Validate & Import Dataset"):
        try:
            if hasattr(provider, "import_csv_data"):
                rep = provider.import_csv_data(stock_input_symbol, uploaded_file, data_source_label=f"Uploaded: {uploaded_file.name}")
                if rep["is_valid"]:
                    st.success(f"✅ {stock_input_symbol} सफलतापूर्वक जाँचा और स्टोर किया गया! ({rep['total_records']} Bars, Status: {rep['status']})")
                else:
                    st.error(f"❌ डेटा वैलिडेशन असफल: {rep['errors']}")
            else:
                st.warning("कृपया CSV डेटा प्रोवाइडर चुनें।")
        except Exception as e:
            st.error(f"Import Error: {e}")

    st.markdown("---")
    st.subheader("🔑 Upstox API v2 (आधिकारिक NSE डेटा कनेक्शन)")
    st.markdown("""
    Upstox का API **100% मुफ़्त (Zero Rupee Cost)** है। इससे आपको NSE का आधिकारिक और सबसे सटीक लाइव भाव और पूर्ण कैंडल डेटा मिलता है।
    
    **3 सरल चरण:**
    1. **[Upstox Developer Console](https://account.upstox.com/developer/apps)** खोलें और लॉगिन करें।
    2. **New App** बनाएँ (App Name: `StockScanner`, Redirect URL: `http://localhost:8501`)।
    3. वहाँ से **API Key**, **API Secret** और **Generate Token** से Access Token कॉपी करके साइडबार के `🔑 Upstox API Key & Token` सेक्शन में पेस्ट करें और **Save** दबाएँ।
    """)

    up_prov = UpstoxDataProvider()
    status = up_prov.verify_token_status()
    if status.get("valid"):
        st.success(f"🟢 **Upstox लाइव ऑथेंटिकेटेड है!** यूज़र: `{status.get('user_name', 'Upstox User')}` (User ID: `{status.get('user_id')}`)")
    else:
        st.info(f"ℹ️ **वर्तमान स्थिति:** `{status.get('reason')}` — जब तक आप टोकन नहीं डालते, तब भी टूल Upstox के मुफ़्त पब्लिक EOD कैंडल्स से काम करता रहेगा।")


# Telegram Alert Modal / Preview
if st.session_state.get("show_alert_modal", False):
    st.markdown("---")
    st.subheader("📢 Zero-Cost Telegram Daily Alert Preview")
    alert_text = format_telegram_alert(swing_rows[:3], wl_mon)
    st.code(alert_text, language="markdown")
    st.caption("यह अलर्ट `reports/telegram_alert_preview.txt` में सेव हो गया है। आप इसे कॉपी करके सीधे अपने ग्रुप/चैनल में भेज सकते हैं।")
    if st.button("Close Alert Preview"):
        st.session_state["show_alert_modal"] = False
        st.rerun()

# Footer Disclaimer
st.markdown("---")
st.caption(f"Indian Stock Research Platform v2.0.0 | Phase 2 Active | Zero Budget MVP | Local Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
st.caption(HEURISTIC_DISCLAIMER)
