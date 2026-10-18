"""
Comprehensive Alert Engine with Deduplication, Cooldown, SQLite Persistence, and Telegram Integration.
Adheres strictly to standard alert specification:
INSTRUMENT: [symbol] STRATEGY: [strategy] TIMEFRAME: [timeframe] BIAS: [bullish/bearish] TRIGGER: [level]
INVALIDATION: [level] RISK/REWARD: [estimate] DATA STATUS: [source and timestamp] REASONS: [conditions]
WARNINGS: [missing confirmations]
"""

import os
import time
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from backend.app.database import SessionLocal
from backend.app.models import AlertHistoryModel
from backend.app.logging_config import logger
from backend.app.alerts.whatsapp_notifier import (
    format_whatsapp_alert,
    get_whatsapp_share_url,
    send_whatsapp_callmebot,
    send_test_whatsapp
)

DEFAULT_COOLDOWN_MINUTES = 30

def format_standard_alert(setup: Dict[str, Any]) -> str:
    """
    Formats setup dictionary into the exact required standard terminal alert format.
    """
    sym = setup.get("symbol", "N/A")
    strat = setup.get("strategy_name", "Momentum Strategy")
    tf = setup.get("timeframe", "1d")
    bias = setup.get("bias", "BULLISH").upper()
    trigger = setup.get("entry_trigger", "Confirmed candle close")
    invalidation = setup.get("invalidation_level", "N/A")
    rrr = setup.get("reward_risk_ratio", "1:2.0")
    src = setup.get("data_source", "Market Feed")
    ts = setup.get("signal_timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    reasons = setup.get("conditions_satisfied", ["Technical alignment verified"])
    reasons_str = "; ".join(reasons) if isinstance(reasons, list) else str(reasons)

    warnings = setup.get("conditions_not_satisfied", [])
    if not warnings:
        warnings = ["Candle close confirmation required; not guaranteed financial advice"]
    warnings_str = "; ".join(warnings) if isinstance(warnings, list) else str(warnings)

    alert_text = (
        f"INSTRUMENT: {sym}\n"
        f"STRATEGY: {strat}\n"
        f"TIMEFRAME: {tf}\n"
        f"BIAS: {bias}\n"
        f"TRIGGER: {trigger}\n"
        f"INVALIDATION: ₹{invalidation}\n"
        f"RISK/REWARD: {rrr}\n"
        f"DATA STATUS: {src} ({ts})\n"
        f"REASONS: {reasons_str}\n"
        f"WARNINGS: {warnings_str}"
    )
    return alert_text


class AlertManager:
    """Manages active alerts, duplicate suppression, cooldowns, database logging, and Telegram notifications."""

    def __init__(self, cooldown_minutes: int = DEFAULT_COOLDOWN_MINUTES):
        self.cooldown_minutes = cooldown_minutes
        self._recent_alerts: Dict[str, datetime] = {} # key -> timestamp

    def _get_alert_key(self, symbol: str, strategy: str) -> str:
        return f"{symbol.upper()}_{strategy.upper()}"

    def is_in_cooldown(self, symbol: str, strategy: str) -> bool:
        """Checks if a signal for this symbol and strategy was generated recently."""
        key = self._get_alert_key(symbol, strategy)
        if key in self._recent_alerts:
            elapsed = datetime.now() - self._recent_alerts[key]
            if elapsed < timedelta(minutes=self.cooldown_minutes):
                return True
        return False

    def dispatch_alert(
        self,
        setup: Dict[str, Any],
        send_telegram: bool = True,
        send_whatsapp: bool = True
    ) -> Dict[str, Any]:
        """
        Processes and dispatches alert with deduplication, SQLite storage, and notifications.
        """
        symbol = setup.get("symbol", "UNKNOWN")
        strategy = setup.get("strategy_name", "UNKNOWN")

        # 1. Deduplication & Cooldown Check
        if self.is_in_cooldown(symbol, strategy):
            logger.info(f"Alert suppressed for {symbol} ({strategy}) due to active cooldown.")
            return {
                "dispatched": False,
                "reason": f"Active cooldown ({self.cooldown_minutes} min) in effect for {symbol}."
            }

        # 2. Format Alert
        alert_text = format_standard_alert(setup)
        wa_text = format_whatsapp_alert(setup)
        share_url = get_whatsapp_share_url(wa_text)
        key = self._get_alert_key(symbol, strategy)
        self._recent_alerts[key] = datetime.now()

        # 3. Optional Telegram Dispatch
        telegram_sent = False
        if send_telegram:
            telegram_sent = self._send_telegram_with_retry(alert_text)

        # 4. Optional WhatsApp Dispatch (CallMeBot)
        whatsapp_sent = False
        if send_whatsapp:
            wa_res = send_whatsapp_callmebot(wa_text)
            whatsapp_sent = wa_res.get("success", False)

        # 5. Record to SQLite Database
        try:
            db = SessionLocal()
            rec = AlertHistoryModel(
                symbol=symbol,
                strategy_name=strategy,
                bias=setup.get("bias", "BULLISH"),
                timeframe=setup.get("timeframe", "1d"),
                trigger_level=float(setup.get("invalidation_level", 0.0) or 0.0),
                invalidation_level=float(setup.get("invalidation_level", 0.0) or 0.0),
                risk_reward=str(setup.get("reward_risk_ratio", "1:2.0")),
                status=setup.get("status", "NEW"),
                message_text=alert_text,
                is_telegram_sent=telegram_sent,
                created_at=datetime.utcnow()
            )
            db.add(rec)
            db.commit()
            db.close()
        except Exception as db_err:
            logger.error(f"Failed to persist alert in SQLite: {db_err}")

        return {
            "dispatched": True,
            "symbol": symbol,
            "strategy": strategy,
            "message": alert_text,
            "whatsapp_message": wa_text,
            "whatsapp_share_url": share_url,
            "telegram_sent": telegram_sent,
            "whatsapp_sent": whatsapp_sent
        }

    def _send_telegram_with_retry(self, message: str, max_retries: int = 3) -> bool:
        """Sends message via Telegram Bot API with exponential backoff retry."""
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

        if not token or not chat_id:
            logger.info("Telegram credentials not configured. Skipping live Telegram dispatch.")
            return False

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }

        for attempt in range(1, max_retries + 1):
            try:
                resp = requests.post(url, json=payload, timeout=6)
                if resp.status_code == 200:
                    logger.info("Alert successfully dispatched to Telegram.")
                    return True
                else:
                    logger.warning(f"Telegram API returned {resp.status_code}: {resp.text[:100]}")
            except Exception as e:
                logger.warning(f"Telegram dispatch attempt {attempt} failed: {e}")
            time.sleep(1.0 * attempt)

        return False

    def send_test_telegram(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None) -> Dict[str, Any]:
        """Tests live Telegram Bot connectivity."""
        token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        cid = chat_id or os.environ.get("TELEGRAM_CHAT_ID", "").strip()

        if not token or not cid:
            return {
                "success": False,
                "message": "Telegram Bot Token or Chat ID is missing. Please configure them in Settings."
            }

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        test_msg = (
            "🔔 <b>Indian Market Intelligence Terminal</b>\n\n"
            "✅ <i>Telegram Bot connection test successful!</i>\n"
            f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            "Alerts-only mode active. No live trading orders will be placed."
        )

        try:
            resp = requests.post(url, json={"chat_id": cid, "text": test_msg, "parse_mode": "HTML"}, timeout=6)
            if resp.status_code == 200:
                return {"success": True, "message": "Telegram test message sent successfully!"}
            else:
                return {"success": False, "message": f"Telegram Error ({resp.status_code}): {resp.text}"}
        except Exception as e:
            return {"success": False, "message": f"Connection error: {e}"}

    def send_test_whatsapp(self, phone: Optional[str] = None, apikey: Optional[str] = None) -> Dict[str, Any]:
        """Tests live WhatsApp CallMeBot connectivity."""
        return send_test_whatsapp(phone=phone, apikey=apikey)

    def get_alert_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetches historical alerts stored in SQLite."""
        try:
            db = SessionLocal()
            records = db.query(AlertHistoryModel).order_by(AlertHistoryModel.created_at.desc()).limit(limit).all()
            res = [
                {
                    "id": r.id,
                    "symbol": r.symbol,
                    "strategy": r.strategy_name,
                    "bias": r.bias,
                    "timeframe": r.timeframe,
                    "status": r.status,
                    "message": r.message_text,
                    "telegram_sent": r.is_telegram_sent,
                    "timestamp": r.created_at.strftime("%Y-%m-%d %H:%M:%S")
                }
                for r in records
            ]
            db.close()
            return res
        except Exception as e:
            logger.error(f"Error fetching alert history: {e}")
            return []

alert_manager = AlertManager()
