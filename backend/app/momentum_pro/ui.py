"""
Momentum Pro — Advanced Trading Analysis User Interface.
Renders all 7 modules in one organized, responsive, mobile-friendly Streamlit view:
A. Market Regime Analyzer
B. Sector Strength Analyzer
C. Fresh Momentum Scanner
D. Pre-Breakout Watchlist
E. Trade Planner & Position Sizer
F. Setup Score (0-100 Explainable)
G. Historical Strategy Backtest
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
from typing import List, Dict, Any

from backend.app.data_providers.base import MarketDataProvider
from backend.app.engines.market_trend import analyze_market_trend
from backend.app.engines.sector_trend import analyze_sector_trends
from backend.app.momentum_pro.scanner import run_momentum_pro_scan
from backend.app.momentum_pro.scoring import calculate_momentum_setup_score, SCORE_DISCLAIMER
from backend.app.momentum_pro.trade_planner import calculate_trade_plan, TRADE_PLAN_DISCLAIMER
from backend.app.momentum_pro.backtester import run_momentum_pro_backtest
from backend.app.charts.plotly_charts import create_candlestick_chart


def render_momentum_pro_page(provider: MarketDataProvider, available_symbols: List[str]):
    """
    Renders the complete Momentum Pro dashboard.
    """
    # -----------------------------------------------------------------
    # Top Bar Navigation & Header
    # -----------------------------------------------------------------
    col_nav, col_meta = st.columns([1, 3])
    with col_nav:
        if st.button("← Back to Old Scanner", use_container_width=True, key="btn_back_to_old"):
            st.session_state["current_view"] = "scanner"
            st.rerun()

    with col_meta:
        src_label = provider.get_provider_name()
        badge_mode = "DEMO / SAMPLE" if provider.is_sample_mode() else ("AUTHENTICATED LIVE" if "Live" in src_label else "HISTORICAL EOD")
        st.markdown(
            f"<div style='text-align: right; font-size: 0.85rem; color: #64748b; padding-top: 6px;'>"
            f"<b>Data Source:</b> <code>{src_label}</code> | "
            f"<span style='background:#e2e8f0; padding:2px 8px; border-radius:4px; font-weight:600;'>{badge_mode}</span> | "
            f"<b>Updated:</b> {datetime.now().strftime('%d %b %Y %H:%M:%S')}"
            f"</div>",
            unsafe_allow_html=True
        )

    st.markdown("""
    <div style='background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); color: white; padding: 20px 24px; border-radius: 12px; margin: 12px 0 20px 0;'>
        <div style='display: flex; align-items: center; gap: 12px;'>
            <span style='font-size: 2rem;'>🚀</span>
            <div>
                <h2 style='margin: 0; color: #38bdf8; font-size: 1.6rem; font-weight: 700;'>Momentum Pro — Quantitative Setup Engine</h2>
                <p style='margin: 4px 0 0 0; color: #94a3b8; font-size: 0.9rem;'>
                    Multi-factor momentum detection, structural consolidation breakouts, institutional volume flow, and risk-managed trade plans.
                </p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # -----------------------------------------------------------------
    # Global Controls & Session State
    # -----------------------------------------------------------------
    if "mp_capital" not in st.session_state:
        st.session_state["mp_capital"] = 100000.0
    if "mp_risk_pct" not in st.session_state:
        st.session_state["mp_risk_pct"] = 1.0

    # Controls Bar
    with st.expander("⚙️ Momentum Pro Parameters & Position Sizing Settings", expanded=False):
        c_p1, c_p2, c_p3 = st.columns(3)
        with c_p1:
            st.session_state["mp_capital"] = st.number_input(
                "Account Capital (₹)",
                min_value=10000.0,
                max_value=10000000.0,
                value=float(st.session_state["mp_capital"]),
                step=10000.0,
                help="Total capital available for sizing calculation"
            )
        with c_p2:
            st.session_state["mp_risk_pct"] = st.slider(
                "Max Risk per Trade (%)",
                min_value=0.25,
                max_value=3.0,
                value=float(st.session_state["mp_risk_pct"]),
                step=0.25,
                help="Standard risk management recommendation is 1.0% to 2.0% per trade"
            )
        with c_p3:
            min_score_filter = st.slider(
                "Minimum Setup Score to Display",
                min_value=30.0,
                max_value=85.0,
                value=45.0,
                step=5.0
            )

    # -----------------------------------------------------------------
    # Run Momentum Pro Scan
    # -----------------------------------------------------------------
    with st.spinner("Scanning universe for momentum breakouts, RSI crossovers, and volume expansions..."):
        scan_results = run_momentum_pro_scan(
            provider=provider,
            symbols=available_symbols,
            account_capital=st.session_state["mp_capital"],
            risk_per_trade_pct=st.session_state["mp_risk_pct"],
            min_setup_score=min_score_filter
        )

    # Quick Stats Overview
    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
    
    # Nifty Regime
    mkt = analyze_market_trend(provider)
    regime = mkt.get("classification", "Neutral")
    regime_color = "#16a34a" if "Bullish" in regime else ("#dc2626" if "Bearish" in regime else "#d97706")
    
    kpi1.metric("NIFTY 50 Regime", regime, f"Score: {mkt.get('market_score', 0)}/100")
    kpi2.metric("Total Scanned", f"{scan_results.get('total_scanned', 0)} Stocks")
    kpi3.metric("Confirmed Breakouts", f"{len(scan_results.get('confirmed_breakouts', []))} Setups")
    kpi4.metric("Fresh RSI Cross (>50)", f"{len(scan_results.get('fresh_rsi_crossovers', []))} Signals")
    kpi5.metric("Pre-Breakout Watchlist", f"{len(scan_results.get('pre_breakout_watchlist', []))} Setups")

    st.markdown("<br>", unsafe_allow_html=True)

    # -----------------------------------------------------------------
    # Main Momentum Pro Tabs
    # -----------------------------------------------------------------
    tab_mkt, tab_scan, tab_watch, tab_plan, tab_bt = st.tabs([
        "🌐 Market & Sector Strength",
        "🚀 Fresh Momentum Scanner",
        "🎯 Pre-Breakout Watchlist",
        "📐 Trade Planner & Position Sizer",
        "🧪 Historical Strategy Backtest"
    ])

    # =================================================================
    # MODULE A & B: MARKET REGIME & SECTOR STRENGTH
    # =================================================================
    with tab_mkt:
        st.subheader("A. Market Regime Analyzer (NIFTY 50 Macro Context)")
        st.caption("A rising tide lifts all boats: momentum setups have significantly higher expectancy in Bullish market regimes.")

        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        m_col1.metric("NIFTY 50 Price", f"₹{mkt.get('price', 0.0):,.2f}", f"{mkt.get('change_percent', 0.0)}%")
        m_col2.metric("50 EMA", f"₹{mkt.get('ema_50', 0.0):,.2f}", "Above 50 EMA" if mkt.get('price_above_50_ema') else "Below 50 EMA")
        m_col3.metric("200 EMA", f"₹{mkt.get('ema_200', 0.0):,.2f}", "Macro Bullish" if mkt.get('price_above_200_ema') else "Macro Bearish")
        m_col4.metric("RSI (14)", f"{mkt.get('rsi', mkt.get('nifty_rsi', 50.0)):.1f}", "Bullish Momentum" if mkt.get('rsi', 50) > 50 else "Sub-50 Bearish")

        # Explicit Rules Breakdown Table
        st.markdown("**Regime Rules Scorecard:**")
        bd = mkt.get("breakdown", [])
        if bd:
            bd_df = pd.DataFrame([
                {
                    "Rule": r["rule_name"],
                    "Condition Description": r["description"],
                    "Points": f"{r['points_awarded']} / {r['max_points']}",
                    "Status": "✅ PASSED" if r["passed"] else "❌ FAILED",
                    "Details": r["detail"]
                }
                for r in bd
            ])
            st.dataframe(bd_df, use_container_width=True)

        st.markdown("---")
        st.subheader("B. Sector Strength Analyzer (Relative Performance vs NIFTY 50)")
        st.caption("Leading sectors with positive relative strength generate the highest momentum velocity.")

        try:
            nifty_hist = provider.get_historical_data("NIFTY 50", period="1y", interval="1d")
            sectors = analyze_sector_trends(provider, nifty_hist)
            if sectors:
                # Sort sectors by score
                sectors_sorted = sorted(sectors, key=lambda s: s.get("sector_score", 0), reverse=True)
                sec_display = []
                for s in sectors_sorted:
                    score = s.get("sector_score", 0)
                    lead_label = "🟢 LEADING" if score >= 70 else ("🟡 STABLE / NEUTRAL" if score >= 45 else "🔴 WEAKENING")
                    sec_display.append({
                        "Sector": s.get("sector_name"),
                        "Symbol": s.get("index_symbol"),
                        "Price (₹)": f"₹{s.get('price', 0):,.2f}",
                        "Relative Strength vs Nifty": f"{s.get('rs_vs_nifty', 0):+0.2f}%",
                        "Sector Score / 100": score,
                        "Leadership Status": lead_label,
                        "Above 50 EMA": "✅" if s.get("above_50_ema") else "❌",
                        "Above 200 EMA": "✅" if s.get("above_200_ema") else "❌"
                    })
                st.dataframe(pd.DataFrame(sec_display), use_container_width=True)
            else:
                st.info("Sector index data is currently being fetched or unavailable for this provider.")
        except Exception as e:
            st.warning(f"Sector strength calculation notice: {e}")

    # =================================================================
    # MODULE C: FRESH MOMENTUM SCANNER
    # =================================================================
    with tab_scan:
        st.subheader("C. Fresh Momentum Scanner (Confirmed Breakouts & Fresh RSI Crossovers)")
        st.markdown(r"""
        **Quantitative Filtering Criteria:**
        - **Confirmed Breakout:** Price $\ge$ 20-Day Swing High + Volume surge ($\ge 1.15x$ 20-DMA).
        - **Fresh RSI Crossover:** $\text{RSI}(14) \le 50$ on previous completed bar $\implies > 50$ on current bar.
        - **Trend Structure:** $\text{EMA } 9 > \text{EMA } 20$ and $\text{Price} > \text{SMA } 50$.
        """)

        filter_choice = st.radio(
            "Filter Candidates View:",
            ["All High-Scoring Momentum Setups", "Confirmed Breakouts Only", "Fresh RSI Crossovers Only"],
            horizontal=True
        )

        candidates_pool = []
        if filter_choice == "Confirmed Breakouts Only":
            candidates_pool = scan_results.get("confirmed_breakouts", [])
        elif filter_choice == "Fresh RSI Crossovers Only":
            candidates_pool = scan_results.get("fresh_rsi_crossovers", [])
        else:
            candidates_pool = scan_results.get("all_candidates", [])

        if candidates_pool:
            display_rows = []
            for c in candidates_pool:
                display_rows.append({
                    "Symbol": c["symbol"],
                    "Price (₹)": f"₹{c['price']:,.2f}",
                    "Setup Type": c["momentum_setup_type"],
                    "Setup Score": f"{c['setup_score']} / 100",
                    "RSI (14)": f"{c['rsi_14']:.1f}",
                    "RVOL (x Avg)": f"{c['rvol']:.2f}x",
                    "20D Resistance": f"₹{c['resistance_20d']:,.2f}",
                    "Dist to Breakout": f"{c['dist_to_resistance_pct']:.2f}%",
                    "20D RS vs Nifty": f"{c['rs_vs_nifty_20d']:+0.2f}%",
                    "EMA 9 vs 20": "9 > 20 ✅" if c["ema_9"] > c["ema_20"] else "9 < 20 ❌",
                    "Grade": c["grade"]
                })
            st.dataframe(pd.DataFrame(display_rows), use_container_width=True)

            # Deep-Dive Inspector for Selected Candidate
            st.markdown("---")
            st.subheader("🔍 Deep-Dive Setup Inspector")
            cand_syms = [c["symbol"] for c in candidates_pool]
            selected_sym = st.selectbox("Select Stock for Deep Technical Breakdown:", cand_syms, key="mp_inspect_sym")
            
            cand_item = next((c for c in candidates_pool if c["symbol"] == selected_sym), candidates_pool[0])
            
            c_d1, c_d2 = st.columns([1, 1])
            with c_d1:
                st.markdown(f"### **{cand_item['symbol']} — Setup Score: `{cand_item['setup_score']}/100`**")
                st.markdown(f"**Classification:** `{cand_item['grade']}` | **Type:** `{cand_item['momentum_setup_type']}`")
                st.markdown("**5-Dimension Quantitative Breakdown:**")
                for item in cand_item.get("score_breakdown", []):
                    pct_val = item["points"] / item["max_points"]
                    st.write(f"**{item['category']}** ({item['points']} / {item['max_points']} pts): {item['detail']}")
                    st.progress(pct_val)

            with c_d2:
                # Quick Trade Plan Card for this stock
                tp = cand_item["trade_plan"]
                st.markdown("### **Calculated Trade Plan**")
                st.markdown(f"""
                * **Entry Zone:** `{tp['entry_zone']}`
                * **Stop Loss:** `₹{tp['stop_loss']:,.2f}` (`{tp['stop_loss_pct']}`)
                * **Target 1 (1.5R):** `₹{tp['target_1']:,.2f}` (`{tp['target_1_gain_pct']}`)
                * **Target 2 (2.0R):** `₹{tp['target_2']:,.2f}` (`{tp['target_2_gain_pct']}`)
                * **Target 3 (3.0R):** `₹{tp['target_3']:,.2f}` (`{tp['target_3_gain_pct']}`)
                * **Reward to Risk:** `{tp['reward_risk_ratio']}`
                * **Position Sizing ({st.session_state['mp_risk_pct']}% Risk):** `{tp['position_shares']} shares` (Total: `₹{tp['total_investment']:,.2f}`)
                """)
                st.caption(tp["disclaimer"])

            # Interactive Plotly Chart
            st.markdown("---")
            st.markdown(f"#### 📊 Interactive Candlestick Chart: **{cand_item['symbol']}**")
            stock_df = provider.get_historical_data(cand_item["symbol"], period="6mo", interval="1d")
            if not stock_df.empty:
                fig = create_candlestick_chart(stock_df, cand_item["symbol"], ema_fast=9, ema_slow=20)
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No candidates matched the current minimum score threshold. Try lowering the score slider in Parameters.")

    # =================================================================
    # MODULE D: PRE-BREAKOUT WATCHLIST
    # =================================================================
    with tab_watch:
        st.subheader("D. Pre-Breakout Watchlist (Consolidation Near Resistance)")
        st.markdown("""
        **Unconfirmed Setups:** Stocks trading within **0.2% to 3.0%** of their 20-day swing high resistance with 
        coiled volatility (ATR contraction) and positive Relative Strength.
        
        > [!IMPORTANT]
        > All setups in this tab are strictly **UNCONFIRMED** and labeled **WATCHLIST**. Wait for completed candle breakout confirmation before execution.
        """)

        pre_list = scan_results.get("pre_breakout_watchlist", [])
        if pre_list:
            w_rows = []
            for item in pre_list:
                w_rows.append({
                    "Status": "🟡 WATCHLIST",
                    "Symbol": item["symbol"],
                    "Price (₹)": f"₹{item['price']:,.2f}",
                    "20D Resistance (₹)": f"₹{item['resistance_20d']:,.2f}",
                    "Distance to Breakout": f"{item['dist_to_resistance_pct']:.2f}%",
                    "RSI (14)": f"{item['rsi_14']:.1f}",
                    "RVOL": f"{item['rvol']:.2f}x",
                    "RS vs Nifty (20D)": f"{item['rs_vs_nifty_20d']:+0.2f}%",
                    "Setup Score": f"{item['setup_score']}/100"
                })
            st.dataframe(pd.DataFrame(w_rows), use_container_width=True)

            st.info(r"💡 **Pro-Tip:** Add these stocks to your broker alerts. When price closes above the 20D resistance with $\ge 1.2x$ volume, the setup transitions into a Confirmed Breakout.")
        else:
            st.info("No stocks currently meet the tight pre-breakout consolidation criteria (0.2% - 3.0% below resistance).")

    # =================================================================
    # MODULE E & F: TRADE PLANNER & SETUP SCORE
    # =================================================================
    with tab_plan:
        st.subheader("E & F. Trade Planner & Position Sizing Calculator")
        st.caption("Protect capital first: position size is determined by exact structural risk per share, never guesswork.")

        all_syms = [c["symbol"] for c in scan_results.get("all_candidates", [])]
        if not all_syms:
            all_syms = available_symbols

        col_sel, col_cap, col_r = st.columns(3)
        with col_sel:
            plan_sym = st.selectbox("Select Candidate Stock:", all_syms, key="tp_sym_choice")
        with col_cap:
            plan_capital = st.number_input("Trading Capital (₹):", min_value=10000.0, max_value=50000000.0, value=float(st.session_state["mp_capital"]), step=10000.0, key="tp_cap_input")
        with col_r:
            plan_risk = st.slider("Risk Tolerance per Trade (%):", 0.25, 3.0, float(st.session_state["mp_risk_pct"]), 0.25, key="tp_risk_input")

        # Fetch stock details
        target_cand = next((c for c in scan_results.get("all_candidates", []) if c["symbol"] == plan_sym), None)
        if target_cand:
            price_val = target_cand["price"]
            atr_val = target_cand.get("atr_14", price_val * 0.02)
            res_val = target_cand.get("resistance_20d", price_val)
            low_val = target_cand.get("swing_low_20d", price_val * 0.95)
        else:
            stock_df = provider.get_historical_data(plan_sym, period="3mo", interval="1d")
            price_val = float(stock_df["Close"].iloc[-1]) if not stock_df.empty else 1000.0
            atr_val = price_val * 0.02
            res_val = price_val * 1.02
            low_val = price_val * 0.96

        live_plan = calculate_trade_plan(
            symbol=plan_sym,
            price=price_val,
            atr_14=atr_val,
            swing_low=low_val,
            resistance=res_val,
            account_capital=plan_capital,
            risk_per_trade_pct=plan_risk
        )

        st.markdown("---")
        tp_col1, tp_col2, tp_col3, tp_col4 = st.columns(4)
        tp_col1.metric("Reference Entry", f"₹{live_plan['entry_reference']:,.2f}", f"Zone: {live_plan['entry_zone']}")
        tp_col2.metric("Technical Stop Loss", f"₹{live_plan['stop_loss']:,.2f}", f"{live_plan['stop_loss_pct']} Risk")
        tp_col3.metric("Recommended Quantity", f"{live_plan['position_shares']} Shares", f"₹{live_plan['total_investment']:,.2f} Total")
        tp_col4.metric("Capital Allocation", f"{live_plan['capital_allocation_pct']}% of Capital", f"Max Risk: ₹{live_plan['max_risk_amount']:,.2f}")

        st.markdown("#### **Multi-Tiered Asymmetric Target Projections**")
        tgt_col1, tgt_col2, tgt_col3 = st.columns(3)
        
        tgt_1_profit = round(live_plan["position_shares"] * (live_plan["target_1"] - live_plan["entry_reference"]), 2)
        tgt_2_profit = round(live_plan["position_shares"] * (live_plan["target_2"] - live_plan["entry_reference"]), 2)
        tgt_3_profit = round(live_plan["position_shares"] * (live_plan["target_3"] - live_plan["entry_reference"]), 2)

        tgt_col1.info(f"""
        **Target 1 (1.5R - Conservative):**
        * **Target Price:** `₹{live_plan['target_1']:,.2f}` (`{live_plan['target_1_gain_pct']}`)
        * **Reward-to-Risk:** `1 : 1.5`
        * **Estimated Net Profit:** `₹{tgt_1_profit:,.2f}`
        """)

        tgt_col2.success(f"""
        **Target 2 (2.0R - Standard Swing):**
        * **Target Price:** `₹{live_plan['target_2']:,.2f}` (`{live_plan['target_2_gain_pct']}`)
        * **Reward-to-Risk:** `1 : 2.0`
        * **Estimated Net Profit:** `₹{tgt_2_profit:,.2f}`
        """)

        tgt_col3.info(f"""
        **Target 3 (3.0R - Runner):**
        * **Target Price:** `₹{live_plan['target_3']:,.2f}` (`{live_plan['target_3_gain_pct']}`)
        * **Reward-to-Risk:** `1 : 3.0`
        * **Estimated Net Profit:** `₹{tgt_3_profit:,.2f}`
        """)

        st.markdown(f"<div style='background:#f1f5f9; border-left:4px solid #0284c7; padding:10px 14px; border-radius:4px; font-size:0.85rem; color:#334155;'><b>Notice:</b> {TRADE_PLAN_DISCLAIMER}</div>", unsafe_allow_html=True)

    # =================================================================
    # MODULE G: HISTORICAL STRATEGY BACKTESTING
    # =================================================================
    with tab_bt:
        st.subheader("G. Momentum Pro Historical Strategy Backtester")
        st.markdown(r"""
        **Realistic Execution Engine:**
        - **Zero Look-Ahead Bias:** Signal evaluated on Day T close $\implies$ Execution at Day T+1 Open.
        - **Statutory Delivery Taxes Included:** STT (0.1%), Stamp Duty (0.015%), NSE Exchange Fee, SEBI Turnover, GST (18%).
        - **Slippage Simulator:** Models realistic entry and exit slippage (0.10%).
        """)

        b_c1, b_c2, b_c3, b_c4 = st.columns(4)
        with b_c1:
            bt_symbol = st.selectbox("Backtest Stock:", available_symbols, index=0, key="mp_bt_sym")
        with b_c2:
            bt_mode = st.selectbox(
                "Trigger Signal:",
                ["Breakout & RSI Cross", "Breakout Only", "RSI Cross Only"],
                index=0,
                key="mp_bt_mode"
            )
        with b_c3:
            bt_mult = st.select_slider(
                "Target Multiplier (R):",
                options=[1.5, 2.0, 2.5, 3.0],
                value=2.0,
                key="mp_bt_target"
            )
        with b_c4:
            bt_hold = st.slider("Max Holding Days:", 5, 30, 15, key="mp_bt_hold")

        if st.button("▶️ Execute Realistic Historical Backtest", use_container_width=True, key="btn_run_mp_bt"):
            with st.spinner(f"Running next-day execution backtest for {bt_symbol}..."):
                res = run_momentum_pro_backtest(
                    provider=provider,
                    symbol=bt_symbol,
                    initial_capital=st.session_state["mp_capital"],
                    risk_per_trade_pct=st.session_state["mp_risk_pct"],
                    target_multiplier=bt_mult,
                    max_holding_bars=bt_hold,
                    slippage_pct=0.10,
                    strategy_mode=bt_mode
                )

                if res.get("status") == "success":
                    st.success(f"✅ Backtest completed for **{bt_symbol}** across 2 years of historical data.")
                    
                    # Metrics Grid
                    k1, k2, k3, k4, k5 = st.columns(5)
                    k1.metric("Win Rate", f"{res['win_rate_pct']}%", f"{res['winning_trades']}/{res['total_trades']} Wins")
                    k2.metric("Profit Factor", f"{res['profit_factor']:.2f}", "Gross Win / Gross Loss")
                    k3.metric("Expectancy / Trade", f"₹{res['expectancy']:,.2f}", "Statistically Positive" if res['expectancy'] > 0 else "Negative")
                    k4.metric("Max Drawdown", f"{res['max_drawdown_pct']}%", "Capital Peak-to-Trough")
                    k5.metric("Net Strategy Return", f"{res['total_return_pct']:+0.2f}%", f"₹{res['total_net_pnl']:+,.2f}")

                    # Equity Curve Chart
                    eq_data = res.get("equity_curve", [])
                    if len(eq_data) >= 2:
                        st.markdown("#### **Strategy Cumulative Equity Growth**")
                        eq_df = pd.DataFrame(eq_data)
                        fig_eq = go.Figure()
                        fig_eq.add_trace(go.Scatter(
                            x=eq_df["date"],
                            y=eq_df["equity"],
                            mode="lines",
                            name="Strategy Equity (₹)",
                            line=dict(color="#0284c7", width=2.5)
                        ))
                        fig_eq.add_hline(
                            y=res["initial_capital"],
                            line_dash="dash",
                            line_color="#94a3b8",
                            annotation_text="Starting Capital"
                        )
                        fig_eq.update_layout(
                            template="plotly_white",
                            margin=dict(l=20, r=20, t=30, b=20),
                            height=360,
                            xaxis_title="Date",
                            yaxis_title="Account Equity (₹)"
                        )
                        st.plotly_chart(fig_eq, use_container_width=True)

                    # Trade Log Table
                    tr_list = res.get("trades", [])
                    if tr_list:
                        st.markdown("#### **Historical Trade Execution Log (Last 50 Trades)**")
                        tr_display = []
                        for t in tr_list:
                            tr_display.append({
                                "Entry Date": t["entry_date"],
                                "Exit Date": t["exit_date"],
                                "Entry (₹)": f"₹{t['entry_price']:,.2f}",
                                "Exit (₹)": f"₹{t['exit_price']:,.2f}",
                                "Shares": t["shares"],
                                "Exit Reason": t["exit_reason"],
                                "Net PnL (₹)": f"₹{t['net_pnl']:+,.2f}",
                                "Return %": f"{t['return_pct']:+0.2f}%",
                                "Taxes & Slippage": f"₹{t['statutory_costs']:,.2f}"
                            })
                        st.dataframe(pd.DataFrame(tr_display), use_container_width=True)
                else:
                    st.warning(res.get("message", "Unable to run backtest."))

    # -----------------------------------------------------------------
    # Footer Disclaimer
    # -----------------------------------------------------------------
    st.markdown("---")
    st.caption("Momentum Pro Quantitative Module | Integrated inside Indian Stock Research Platform | Zero Paid APIs Required.")
    st.caption(SCORE_DISCLAIMER)
