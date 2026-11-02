"""
Comprehensive Telegram Digest and Alert Dispatcher.
Generates:
1. Automatic Morning Market & Swing Digest (Nifty 50 Trend, Nifty 100 Action Setups, Watchlist Invalidation)
2. On-Demand Instant Screener & Swing Alerts
3. Safe Chunking (>4096 char protection), HTML Formatting, and SQLite Logging
"""

import os
import time
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime, date

from backend.app.database import SessionLocal
from backend.app.models import AlertHistoryModel
from backend.app.logging_config import logger
from backend.app.engines.swing_action_screener import scan_nifty_100_market
from backend.app.engines.market_trend import analyze_market_trend
from backend.app.data_providers.factory import get_market_data_provider


def split_telegram_message(text: str, max_chars: int = 3800) -> List[str]:
    """
    Splits long messages into chunks within Telegram's 4096-character limit,
    preserving paragraph and line structure.
    """
    if len(text) <= max_chars:
        return [text]

    chunks = []
    lines = text.split("\n")
    current_chunk = []
    current_len = 0

    for line in lines:
        line_len = len(line) + 1
        if current_len + line_len > max_chars:
            chunks.append("\n".join(current_chunk))
            current_chunk = [line]
            current_len = line_len
        else:
            current_chunk.append(line)
            current_len += line_len

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks


def send_telegram_message_safe(
    text: str,
    bot_token: Optional[str] = None,
    chat_id: Optional[str] = None,
    parse_mode: str = "HTML"
) -> Dict[str, Any]:
    """
    Sends text to Telegram, handling multi-chunk splitting, retries, and SQLite history logging.
    """
    token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    cid = chat_id or os.environ.get("TELEGRAM_CHAT_ID", "").strip()

    if not token or not cid:
        return {
            "success": False,
            "message": "Telegram Bot Token or Chat ID not configured. Configure in Alerts Config sidebar."
        }

    chunks = split_telegram_message(text)
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    total_chunks = len(chunks)
    sent_chunks = 0

    for idx, chunk in enumerate(chunks, 1):
        payload = {
            "chat_id": cid,
            "text": chunk,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True
        }

        # Retry up to 3 times
        success = False
        last_error = ""
        for attempt in range(1, 4):
            try:
                resp = requests.post(url, json=payload, timeout=8)
                if resp.status_code == 200:
                    success = True
                    sent_chunks += 1
                    break
                else:
                    last_error = f"HTTP {resp.status_code}: {resp.text[:150]}"
                    # If HTML parsing failed, fallback to plain text
                    if "can't parse entities" in resp.text.lower():
                        payload.pop("parse_mode", None)
            except Exception as e:
                last_error = str(e)
            time.sleep(1.0 * attempt)

        if not success:
            logger.error(f"Telegram chunk {idx}/{total_chunks} failed: {last_error}")
            return {
                "success": False,
                "message": f"Failed to send chunk {idx}/{total_chunks}: {last_error}"
            }

        # Small delay between chunks
        if idx < total_chunks:
            time.sleep(0.5)

    # Record to SQLite database
    try:
        db = SessionLocal()
        rec = AlertHistoryModel(
            symbol="NIFTY100_DIGEST",
            strategy_name="Telegram Digest & Screener",
            bias="BULLISH",
            timeframe="1d",
            trigger_level=0.0,
            invalidation_level=0.0,
            risk_reward="1:2.0",
            status="SENT",
            message_text=text[:500] + ("..." if len(text) > 500 else ""),
            is_telegram_sent=True,
            created_at=datetime.utcnow()
        )
        db.add(rec)
        db.commit()
        db.close()
    except Exception as db_err:
        logger.error(f"Failed to record Telegram alert in SQLite: {db_err}")

    return {
        "success": True,
        "sent_chunks": sent_chunks,
        "message": f"Telegram alert successfully dispatched ({sent_chunks} message chunk{'s' if sent_chunks > 1 else ''})!"
    }


def generate_morning_telegram_digest(screener_results: Optional[List[Dict[str, Any]]] = None) -> str:
    """
    Creates the comprehensive Morning Market & Swing Trading Daily Digest.
    """
    today_str = datetime.now().strftime("%d-%b-%Y, %A")
    lines = [
        "🌅 <b>MORNING SWING MARKET DIGEST — NSE</b>",
        f"📅 <b>Date:</b> {today_str}",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        ""
    ]

    # 1. Macro Market Trend
    try:
        prov = get_market_data_provider("yahoo")
        mkt = analyze_market_trend(prov)
        regime_emoji = "🟢" if "Bullish" in mkt.get("classification", "") else ("🔴" if "Bearish" in mkt.get("classification", "") else "🟡")
        lines.append(f"<b>📊 NIFTY 50 Macro Regime:</b> {regime_emoji} <b>{mkt.get('classification', 'Neutral').upper()}</b>")
        lines.append(f"• Index Close: <code>₹{mkt.get('price', 0.0):,.2f}</code> ({mkt.get('change_percent', 0.0)}%)")
        lines.append(f"• Market Health Score: <code>{mkt.get('market_score', 0.0)}/100</code>")
        lines.append(f"• 50 EMA: <code>₹{mkt.get('ema_50', 0.0):,.2f}</code> | 200 EMA: <code>₹{mkt.get('ema_200', 0.0):,.2f}</code>")
        lines.append("")
    except Exception as e:
        logger.warning(f"Could not fetch NIFTY 50 macro trend for morning digest: {e}")

    # 2. Top Swing Action Screener Picks (Nifty 100)
    results = screener_results if screener_results is not None else scan_nifty_100_market(force_refresh=False)
    ready_picks = [r for r in results if "READY" in r.get("signal", "")]
    wait_picks = [r for r in results if "WAIT" in r.get("signal", "")]

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"🎯 <b>NIFTY 100 SWING ACTION PICKS ({len(results)} Setups)</b>")
    lines.append("<i>Rules: Close &gt; 200 EMA + Supertrend Bullish | RSI 50-68 | Pullback &amp; Breakouts</i>")
    lines.append("")

    if ready_picks:
        lines.append(f"🟢 <b>READY TO BUY — HIGH CONVICTION ({len(ready_picks)}):</b>")
        for p in ready_picks[:6]:
            lines.append(f"• <b>{p['symbol']}</b> — CMP: <code>₹{p['cmp']:,.2f}</code>")
            lines.append(f"  <b>Setup:</b> {p['setup_type']}")
            lines.append(f"  🎯 <b>Target:</b> <code>₹{p['target_level']:,.2f}</code> (+{p['target_pct']}%) | 🛑 <b>SL:</b> <code>₹{p['stop_loss']:,.2f}</code> (-{p['sl_pct']}%)")
            lines.append(f"  ⚖️ <b>R:R:</b> <code>{p['risk_reward_ratio']}</code> | <b>RSI(14):</b> <code>{p['rsi_14']}</code>")
            lines.append("")
    else:
        lines.append("ℹ️ <i>No stocks triggered 'Ready to Buy' today. Capital protection mode.</i>\n")

    if wait_picks:
        lines.append(f"⏳ <b>WAIT FOR CONFIRMATION / NEAR SUPPORT ({len(wait_picks)}):</b>")
        for w in wait_picks[:4]:
            lines.append(f"• <b>{w['symbol']}</b> (CMP: <code>₹{w['cmp']:,.2f}</code>) — <i>{w['setup_type']}</i>")
            lines.append(f"  Trigger: Breakout above day's high | SL: <code>₹{w['stop_loss']:,.2f}</code> | R:R: <code>{w['risk_reward_ratio']}</code>")
        lines.append("")

    # 3. Footer and Action Instructions
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("💡 <i>On-Demand Alerts: Type <code>/scan</code> in this chat anytime to get fresh setups!</i>")
    lines.append("⚠️ <i>Analytical Research Only. Alerts-only mode. Not SEBI registered investment advice.</i>")

    return "\n".join(lines)


def generate_instant_screener_telegram_alert(screener_results: Optional[List[Dict[str, Any]]] = None) -> str:
    """
    Creates an on-demand instant alert of current screened stocks.
    """
    results = screener_results if screener_results is not None else scan_nifty_100_market(force_refresh=False)
    now_str = datetime.now().strftime("%d-%b-%Y %H:%M:%S")

    lines = [
        "⚡ <b>INSTANT SWING ACTION SCREENER ALERT</b>",
        f"🕒 <i>Generated At: {now_str}</i>",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"<b>Total Screened Universe:</b> 100 Liquid NSE Stocks",
        f"<b>Passed All 4 Core Filters:</b> {len(results)} Stocks",
        ""
    ]

    ready = [r for r in results if "READY" in r.get("signal", "")]
    if ready:
        lines.append(f"🟢 <b>READY TO BUY SETUPS ({len(ready)}):</b>")
        for r in ready[:8]:
            lines.append(f"• <b>{r['symbol']}</b> | CMP: <code>₹{r['cmp']:,.2f}</code>")
            lines.append(f"  {r['setup_type']}")
            lines.append(f"  🎯 Target: <code>₹{r['target_level']:,.2f}</code> (+{r['target_pct']}%) | 🛑 SL: <code>₹{r['stop_loss']:,.2f}</code> (-{r['sl_pct']}%)")
            lines.append(f"  Risk/Reward: <code>{r['risk_reward_ratio']}</code> | RSI: <code>{r['rsi_14']}</code>")
            lines.append("")
    else:
        lines.append("ℹ️ <i>No stocks meeting strict 'Ready to Buy' breakout/pullback criteria right now.</i>\n")

    wait = [r for r in results if "WAIT" in r.get("signal", "")]
    if wait:
        lines.append(f"⏳ <b>WAITING CONFIRMATION ({len(wait)}):</b>")
        for w in wait[:4]:
            lines.append(f"• <b>{w['symbol']}</b> (₹{w['cmp']:,.2f}) — SL: ₹{w['stop_loss']} | Target: ₹{w['target_level']}")
        lines.append("")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("⚠️ <i>Analytical Research Only. Alerts-only mode. Not SEBI Advice.</i>")
    return "\n".join(lines)
