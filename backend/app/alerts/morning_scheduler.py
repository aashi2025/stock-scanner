"""
Morning Daily Scheduled Telegram Alert Daemon.
Automatically dispatches the Morning Swing Market Digest every morning (default 08:30 AM IST) on trading days.
Ensures exactly ONE delivery per day with local state tracking.
"""

import os
import json
import time
import threading
from typing import Optional, Dict, Any
from datetime import datetime, date

from backend.app.logging_config import logger
from backend.app.alerts.telegram_digest import (
    send_telegram_message_safe,
    generate_morning_telegram_digest
)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
STATE_FILE = os.path.join(PROJECT_ROOT, "data", "morning_alert_state.json")


class MorningAlertScheduler:
    """Schedules and executes automatic morning Telegram digests."""

    def __init__(self, target_time: str = "08:30"):
        self.target_time = target_time  # Format: "HH:MM" 24hr format
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._is_running = False

    def is_running(self) -> bool:
        return self._is_running and self._thread is not None and self._thread.is_alive()

    def _get_last_sent_date(self) -> Optional[str]:
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("last_sent_date")
            except Exception:
                return None
        return None

    def _record_sent_date(self, sent_date: str):
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "last_sent_date": sent_date,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving morning alert state: {e}")

    def trigger_now(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Manually triggers the morning digest immediately."""
        logger.info("Executing immediate on-demand Morning Digest dispatch...")
        digest = generate_morning_telegram_digest()
        res = send_telegram_message_safe(digest, bot_token=bot_token, chat_id=chat_id)
        if res.get("success"):
            today_str = date.today().isoformat()
            self._record_sent_date(today_str)
        return res

    def start(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None, target_time: str = "08:30"):
        """Starts the background scheduler loop."""
        self.target_time = target_time
        token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        cid = chat_id or os.environ.get("TELEGRAM_CHAT_ID", "").strip()

        if not token or not cid:
            logger.warning("MorningAlertScheduler cannot start: Missing Telegram credentials.")
            return False

        if self.is_running():
            logger.info("MorningAlertScheduler is already running.")
            return True

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._scheduler_loop,
            args=(token, cid),
            name="MorningAlertSchedulerThread",
            daemon=True
        )
        self._thread.start()
        self._is_running = True
        logger.info(f"MorningAlertScheduler started. Scheduled daily at {self.target_time} IST.")
        return True

    def stop(self):
        self._stop_event.set()
        self._is_running = False

    def _scheduler_loop(self, token: str, cid: str):
        while not self._stop_event.is_set():
            try:
                now = datetime.now()
                # Check trading days: Monday = 0, Friday = 4, Saturday = 5, Sunday = 6
                # We can allow Mon-Fri, or all days
                is_weekday = now.weekday() < 5
                current_hm = now.strftime("%H:%M")
                today_str = now.date().isoformat()

                # If current time matches or is slightly after target_time, and hasn't been sent today
                last_sent = self._get_last_sent_date()
                if is_weekday and last_sent != today_str and current_hm >= self.target_time:
                    logger.info(f"Morning alert trigger reached at {current_hm}. Dispatching digest...")
                    res = self.trigger_now(bot_token=token, chat_id=cid)
                    if res.get("success"):
                        logger.info("Morning daily alert successfully dispatched automatically!")
                    else:
                        logger.error(f"Failed to dispatch scheduled morning alert: {res.get('message')}")

            except Exception as e:
                logger.error(f"Error in morning alert scheduler loop: {e}")

            # Sleep 45 seconds before next check
            for _ in range(45):
                if self._stop_event.is_set():
                    break
                time.sleep(1)


# Global singleton instance
morning_scheduler = MorningAlertScheduler()
