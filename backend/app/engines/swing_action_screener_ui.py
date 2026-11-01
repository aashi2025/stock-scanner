"""
Streamlit UI Component for Indian Stocks Swing Trading Action Screener (Nifty 100).
Renders the dark-themed interactive dashboard requested by the user.
"""

import urllib.parse
import pandas as pd
import streamlit as st
from datetime import datetime
from backend.app.engines.swing_action_screener import scan_nifty_100_market, NIFTY_100_SYMBOLS


def render_swing_action_screener_tab():
    """
    Renders the Swing Delivery Trade Screener (Nifty 100) inside Streamlit.
    """
    # Header Section
    st.markdown("""
    <div style="background: linear-gradient(135deg, #090d16 0%, #111827 100%); border: 1px solid #1f2937; border-radius: 12px; padding: 22px 24px; margin-bottom: 20px;">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 15px;">
            <div>
                <h2 style="color: #38bdf8; margin: 0; font-size: 1.65rem; font-weight: 700; display: flex; align-items: center; gap: 10px;">
                    🎯 Swing Delivery Trade Screener (Nifty 100)
                </h2>
                <p style="color: #9ca3af; margin: 6px 0 0 0; font-size: 0.92rem;">
                    Automated daily EOD screener: <b>Close &gt; 200 EMA</b> + <b>Supertrend (7, 3)</b> Bullish | <b>RSI 50-68</b> | <b>EMA Pullback & Solid Breakouts</b> | Auto SL &amp; 1:2 Target Levels.
                </p>
            </div>
            <div style="text-align: right;">
                <span style="background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); padding: 4px 12px; border-radius: 20px; font-size: 0.82rem; font-weight: 600;">
                    LIVE EOD SCANNER
                </span>
                <div style="color: #6b7280; font-size: 0.78rem; margin-top: 4px;">Universe: Top 100 Liquid NSE Equities</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Initialize Session State
    if "swing_screener_results" not in st.session_state:
        st.session_state["swing_screener_results"] = None
    if "swing_screener_last_run" not in st.session_state:
        st.session_state["swing_screener_last_run"] = None

    # Prominent Action Bar
    col_act1, col_act2, col_act3 = st.columns([2, 1, 1])
    with col_act1:
        scan_btn = st.button("⚡ Scan Market Today (EOD Daily Data)", type="primary", use_container_width=True, key="btn_run_swing_screener")
    with col_act2:
        sort_by = st.selectbox(
            "Sort Table By:",
            ["Risk-Reward Ratio", "RSI (14) Momentum", "CMP (Price)", "Signal"],
            index=0,
            key="sb_screener_sort"
        )
    with col_act3:
        filter_signal = st.selectbox(
            "Filter Signals:",
            ["All Setups", "🟢 READY TO BUY Only", "⏳ WAIT FOR CONFIRMATION Only", "Setup B (Breakout) Only", "Setup A (Pullback) Only"],
            index=0,
            key="sb_screener_filter"
        )

    # Handle Scan Execution
    if scan_btn or st.session_state["swing_screener_results"] is None:
        with st.spinner("Fetching daily OHLCV candles for Nifty 100 universe via yfinance and evaluating 4 Core Filters..."):
            force = bool(scan_btn)
            results = scan_nifty_100_market(force_refresh=force)
            st.session_state["swing_screener_results"] = results
            st.session_state["swing_screener_last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    results = st.session_state.get("swing_screener_results") or []
    last_run = st.session_state.get("swing_screener_last_run", "Never")

    # Metrics Summary
    ready_count = sum(1 for r in results if r["signal"] == "🟢 READY TO BUY")
    wait_count = sum(1 for r in results if r["signal"] == "⏳ WAIT FOR CONFIRMATION")
    pullback_count = sum(1 for r in results if "Pullback" in r["setup_type"])
    breakout_count = sum(1 for r in results if "Breakout" in r["setup_type"])

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Universe Scanned", f"{len(NIFTY_100_SYMBOLS)} Stocks", "Nifty 100")
    m2.metric("Matching Setups", f"{len(results)} Stocks", "Passed 4 Filters")
    m3.metric("🟢 Ready to Buy", f"{ready_count}", "Confirmed Trigger")
    m4.metric("⏳ Confirmation Needed", f"{wait_count}", "Testing Support")
    m5.metric("Setup Types", f"{breakout_count} Breakout", f"{pullback_count} Pullback")

    st.markdown("---")

    # Apply Filtering
    filtered_results = list(results)
    if filter_signal == "🟢 READY TO BUY Only":
        filtered_results = [r for r in filtered_results if r["signal"] == "🟢 READY TO BUY"]
    elif filter_signal == "⏳ WAIT FOR CONFIRMATION Only":
        filtered_results = [r for r in filtered_results if r["signal"] == "⏳ WAIT FOR CONFIRMATION"]
    elif filter_signal == "Setup B (Breakout) Only":
        filtered_results = [r for r in filtered_results if "Breakout" in r["setup_type"]]
    elif filter_signal == "Setup A (Pullback) Only":
        filtered_results = [r for r in filtered_results if "Pullback" in r["setup_type"]]

    # Apply Sorting
    if sort_by == "Risk-Reward Ratio":
        filtered_results.sort(key=lambda x: (x["rr_numeric"], -x["rsi_14"]), reverse=True)
    elif sort_by == "RSI (14) Momentum":
        filtered_results.sort(key=lambda x: x["rsi_14"], reverse=True)
    elif sort_by == "CMP (Price)":
        filtered_results.sort(key=lambda x: x["cmp"], reverse=True)
    elif sort_by == "Signal":
        filtered_results.sort(key=lambda x: (x["signal"] == "🟢 READY TO BUY"), reverse=True)

    # Results Table Display
    if filtered_results:
        st.subheader(f"📋 Screened Stocks Output ({len(filtered_results)} Opportunities)")
        st.caption(f"Last Scanned: {last_run} | Real EOD Candle Data (yfinance)")

        table_data = []
        for r in filtered_results:
            table_data.append({
                "Symbol": r["symbol"],
                "CMP (₹)": f"₹{r['cmp']:,.2f}",
                "Signal": r["signal"],
                "Setup Type": r["setup_type"],
                "Entry Level": f"₹{r['entry_level']:,.2f}",
                "Stop Loss (SL)": f"₹{r['stop_loss']:,.2f} (-{r['sl_pct']}%)",
                "Target Level": f"₹{r['target_level']:,.2f} (+{r['target_pct']}%)",
                "Risk-Reward": r["risk_reward_ratio"],
                "RSI (14)": r["rsi_14"],
                "200 EMA": f"₹{r['ema_200']:,.2f}",
                "Supertrend": f"₹{r['supertrend']:,.2f}"
            })

        st.dataframe(pd.DataFrame(table_data), use_container_width=True)

        st.markdown("### 🔍 Detailed Action Cards & Instant WhatsApp Alerts")

        for r in filtered_results:
            with st.expander(f"📌 {r['symbol']} — {r['signal']} | CMP: ₹{r['cmp']:,.2f} | Setup: {r['setup_type']}", expanded=False):
                c_c1, c_c2, c_c3, c_c4 = st.columns(4)
                c_c1.metric("Entry Level", f"₹{r['entry_level']:,.2f}", "CMP Trigger")
                c_c2.metric("Stop Loss (SL)", f"₹{r['stop_loss']:,.2f}", f"-{r['sl_pct']}% Risk")
                c_c3.metric("Target Level", f"₹{r['target_level']:,.2f}", f"+{r['target_pct']}% Upside")
                c_c4.metric("Risk-to-Reward", f"{r['risk_reward_ratio']}", f"RSI: {r['rsi_14']}")

                st.markdown(f"""
                * **Primary Trend:** `Close (₹{r['cmp']:,.2f}) > 200 EMA (₹{r['ema_200']:,.2f})` and `Supertrend (7, 3) Bullish (₹{r['supertrend']:,.2f})` ✅
                * **Momentum:** `Daily RSI(14) = {r['rsi_14']}` (Within optimal 50-68 bull swing band) ✅
                * **Pattern Detail:** {r['status_note']}
                """)

                # WhatsApp 1-Click Alert
                wa_text = (
                    f"🎯 *SWING ACTION SCREENER ALERT*\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"*{r['symbol']}* | *{r['signal']}*\n"
                    f"• *Setup:* {r['setup_type']}\n"
                    f"• *CMP / Entry:* ₹{r['entry_level']:,.2f}\n"
                    f"• *Stop Loss (SL):* ₹{r['stop_loss']:,.2f} (-{r['sl_pct']}%)\n"
                    f"• *Target Level:* ₹{r['target_level']:,.2f} (+{r['target_pct']}%)\n"
                    f"• *Risk/Reward:* {r['risk_reward_ratio']}\n"
                    f"• *RSI (14):* {r['rsi_14']} | *200 EMA:* ₹{r['ema_200']:,.2f}\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"⚠️ _Analytical Research Only. Alerts-only mode. Not SEBI Advice._"
                )
                wa_url = f"https://wa.me/?text={urllib.parse.quote(wa_text)}"
                st.link_button(f"📲 Share {r['symbol']} Setup to WhatsApp (1-Click)", wa_url)

        # Bulk WhatsApp Share Button
        st.markdown("---")
        top_picks = [r for r in filtered_results if r["signal"] == "🟢 READY TO BUY"][:5]
        if not top_picks:
            top_picks = filtered_results[:5]

        bulk_msg = [
            f"🎯 *NIFTY 100 SWING ACTION SCREENER REPORT*",
            f"📅 Date: {datetime.now().strftime('%d-%b-%Y')} | Last Scanned: {last_run}",
            f"━━━━━━━━━━━━━━━━━━━",
            f"⚡ *Top Filtered Opportunities ({len(top_picks)}):*",
            ""
        ]
        for p in top_picks:
            bulk_msg.append(f"• *{p['symbol']}* ({p['signal']})")
            bulk_msg.append(f"  CMP: ₹{p['cmp']:,.2f} | Setup: {p['setup_type']}")
            bulk_msg.append(f"  🎯 Target: ₹{p['target_level']:,.2f} (+{p['target_pct']}%) | 🛑 SL: ₹{p['stop_loss']:,.2f} (-{p['sl_pct']}%) | RR: {p['risk_reward_ratio']}")
            bulk_msg.append("")

        bulk_msg.append("━━━━━━━━━━━━━━━━━━━")
        bulk_msg.append("⚠️ _Analytical Research Only. Alerts-only mode. Not SEBI Advice._")
        bulk_url = f"https://wa.me/?text={urllib.parse.quote(chr(10).join(bulk_msg))}"

        st.link_button("📲 Share Top Screened Swing Setups to WhatsApp (1-Click Free)", bulk_url, use_container_width=True)

    else:
        st.info("💡 वर्तमान फिल्टर्स पर कोई स्टॉक नहीं मिला। [⚡ Scan Market Today] बटन दबाकर ताज़ा डेटा स्कैन करें।")
