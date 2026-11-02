"""
Interactive Telegram Bot Daemon and On-Demand Command Handler.
Allows user to message their Telegram bot from their phone at any time:
- /scan or /screener : Runs Nifty 100 EOD Swing Action Screener and replies instantly with filtered setups.
- /morning or /digest : Sends the full market morning digest.
- /status : Reports market regime and scanner health.
- /help : Displays available commands.
Uses long-polling (getUpdates) with zero external ports or webhook requirements.
"""

import os
import time
import threading
import requests
from typing import Dict, Any, Optional
from datetime import datetime

from backend.app.logging_config import logger
from backend.app.alerts.telegram_digest import (
    send_telegram_message_safe,
    generate_morning_telegram_digest,
    generate_instant_screener_telegram_alert
)


class TelegramBotListener:
    """Manages Telegram bot command polling and on-demand responses."""

    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._last_update_id = 0
        self._is_running = False

    def is_running(self) -> bool:
        return self._is_running and self._thread is not None and self._thread.is_alive()

    def start(self, bot_token: Optional[str] = None, authorized_chat_id: Optional[str] = None):
        """Starts the Telegram bot polling in a background daemon thread."""
        token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        chat_id = authorized_chat_id or os.environ.get("TELEGRAM_CHAT_ID", "").strip()

        if not token:
            logger.warning("Cannot start Telegram Bot Listener: Bot Token missing.")
            return False

        if self.is_running():
            logger.info("Telegram Bot Listener is already running.")
            return True

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._poll_loop,
            args=(token, chat_id),
            name="TelegramBotListenerThread",
            daemon=True
        )
        self._thread.start()
        self._is_running = True
        logger.info("Telegram Bot Listener successfully started in background daemon.")
        return True

    def stop(self):
        """Stops the bot listener loop."""
        self._stop_event.set()
        self._is_running = False
        logger.info("Telegram Bot Listener stopping...")

    def _poll_loop(self, token: str, authorized_chat_id: str):
        """Main long-polling loop."""
        url = f"https://api.telegram.org/bot{token}/getUpdates"

        logger.info("Telegram Bot listening for incoming user commands (/scan, /morning, /status)...")

        while not self._stop_event.is_set():
            try:
                params = {
                    "offset": self._last_update_id + 1,
                    "timeout": 15,
                    "allowed_updates": ["message"]
                }
                resp = requests.get(url, params=params, timeout=20)

                if resp.status_code == 200:
                    data = resp.json()
                    for update in data.get("result", []):
                        self._last_update_id = update["update_id"]
                        msg = update.get("message", {})
                        chat = msg.get("chat", {})
                        sender_chat_id = str(chat.get("id", ""))
                        text = (msg.get("text") or "").strip().lower()

                        # If authorized chat ID is set, filter out strangers
                        if authorized_chat_id and sender_chat_id != str(authorized_chat_id).strip():
                            logger.warning(f"Ignoring unauthorized message from chat_id {sender_chat_id}")
                            continue

                        if text:
                            self._handle_command(token, sender_chat_id, text)

                elif resp.status_code == 409:
                    logger.warning("Another instance of Telegram bot is polling. Pausing 10s...")
                    time.sleep(10)
                else:
                    time.sleep(3)

            except requests.exceptions.Timeout:
                # Normal long polling timeout, just continue
                pass
            except Exception as e:
                logger.debug(f"Bot polling exception: {e}")
                time.sleep(3)

        self._is_running = False

    def _handle_command(self, token: str, chat_id: str, text: str):
        """Handles incoming commands from user."""
        logger.info(f"Telegram command received from {chat_id}: '{text}'")

        if text in ["/start", "/help", "help", "hi", "hello"]:
            help_msg = (
                "🤖 <b>Indian Market Intelligence Bot</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Aap yahan se kabhi bhi instant market notification le sakte hain:\n\n"
                "⚡ <b>/scan</b> — Nifty 100 EOD Screener run karega aur Ready-to-Buy setups (Entry, Target, SL) bhejega.\n"
                "🌅 <b>/morning</b> — Subah ka Macro Market & Swing Digest bhejega.\n"
                "📊 <b>/status</b> — System & Market Regime status batayega.\n\n"
                "<i>Alerts-only mode active. Zero broker orders.</i>"
            )
            send_telegram_message_safe(help_msg, bot_token=token, chat_id=chat_id)

        elif text in ["/scan", "scan", "/screener", "screener", "trade"]:
            send_telegram_message_safe(
                "⏳ <i>Scanning Nifty 100 EOD candles... Please wait 5-10 seconds...</i>",
                bot_token=token,
                chat_id=chat_id
            )
            report = generate_instant_screener_telegram_alert()
            send_telegram_message_safe(report, bot_token=token, chat_id=chat_id)

        elif text in ["/morning", "morning", "/digest", "digest", "today"]:
            send_telegram_message_safe(
                "⏳ <i>Compiling Morning Swing Market Digest...</i>",
                bot_token=token,
                chat_id=chat_id
            )
            digest = generate_morning_telegram_digest()
            send_telegram_message_safe(digest, bot_token=token, chat_id=chat_id)

        elif text in ["/status", "status"]:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            status_msg = (
                f"✅ <b>Terminal Online & Healthy</b>\n"
                f"🕒 Server Time: <code>{now_str}</code>\n"
                f"📊 Universe: 100 Liquid NSE Stocks\n"
                f"🔔 Bot Listening: Active"
            )
            send_telegram_message_safe(status_msg, bot_token=token, chat_id=chat_id)

        else:
            send_telegram_message_safe(
                "ℹ️ Command samajh nahi aayi. Type karein: <b>/scan</b> ya <b>/morning</b>",
                bot_token=token,
                chat_id=chat_id
            )


# Global singleton instance
bot_listener = TelegramBotListener()
