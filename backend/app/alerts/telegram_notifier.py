"""
Zero-Cost Alert Dispatcher.
Formats daily scan results and invalidation alerts for Telegram.
If Telegram Bot Token is not configured, saves alert preview to reports/ for free local viewing.
"""

import os
import requests
from typing import Dict, Any, List
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
REPORTS_DIR = os.path.join(PROJECT_ROOT, "reports")


def format_telegram_alert(fresh_signals: List[Dict[str, Any]], invalidations: List[Dict[str, Any]] = None) -> str:
    """Creates a clean, formatted Telegram markdown message."""
    today_str = datetime.now().strftime("%d-%b-%Y")
    lines = [
        f"🚀 *NSE SWING RESEARCH REPORT — {today_str}*",
        "━━━━━━━━━━━━━━━━━━━━━━━",
        ""
    ]

    if fresh_signals:
        lines.append(f"⚡ *FRESH SWING SIGNALS ({len(fresh_signals)})*")
        lines.append("_(Completed Candle RSI(14) Crossover > 50)_")
        lines.append("")
        for s in fresh_signals[:5]:
            ref = s.get("reference_levels", {})
            lines.append(f"• *{s['symbol']}* — ₹{s['price']}")
            lines.append(f"  Score: `{s['swing_score']}/100` | Vol: `{s['vol_ratio']}x` | RSI: `{s['rsi_value']}`")
            lines.append(f"  🎯 Target: ₹{ref.get('target_1_reference', '-')} | 🛑 SL: ₹{ref.get('stop_loss_reference', '-')}")
            lines.append("")
    else:
        lines.append("ℹ️ *Fresh Signals:* No fresh crossovers triggered today.")
        lines.append("")

    if invalidations:
        invalid_items = [i for i in invalidations if i.get("is_invalidated")]
        if invalid_items:
            lines.append("⚠️ *WATCHLIST SETUP INVALIDATIONS*")
            for inv in invalid_items:
                lines.append(f"• *{inv['symbol']}*: {', '.join(inv.get('warnings', []))}")
            lines.append("")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("⚠️ _Analytical Research Only. Not SEBI Advice._")
    return "\n".join(lines)


def send_telegram_alert(
    message: str,
    bot_token: str = None,
    chat_id: str = None
) -> Dict[str, Any]:
    """
    Sends message via Telegram Bot API (100% free) or saves to preview file.
    """
    token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat = chat_id or os.environ.get("TELEGRAM_CHAT_ID", "").strip()

    os.makedirs(REPORTS_DIR, exist_ok=True)
    preview_file = os.path.join(REPORTS_DIR, "telegram_alert_preview.txt")

    with open(preview_file, "w", encoding="utf-8") as f:
        f.write(message)

    if not token or not chat:
        return {
            "sent": False,
            "mode": "LOCAL_PREVIEW",
            "preview_file": preview_file,
            "message": "Telegram Bot Token or Chat ID not configured. Message saved locally for zero-cost preview."
        }

    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat,
            "text": message,
            "parse_mode": "Markdown"
        }
        res = requests.post(url, json=payload, timeout=10)
        if res.status_code == 200:
            return {"sent": True, "mode": "TELEGRAM_API", "status_code": 200}
        else:
            return {"sent": False, "mode": "ERROR", "error": res.text, "preview_file": preview_file}
    except Exception as e:
        return {"sent": False, "mode": "ERROR", "error": str(e), "preview_file": preview_file}
