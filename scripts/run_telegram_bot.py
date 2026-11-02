"""
Interactive Telegram Bot Service Runner.
Run with: python scripts/run_telegram_bot.py
Listens for commands (/scan, /morning, /status, /help) and replies instantly on Telegram.
"""

import os
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dotenv
dotenv.load_dotenv(override=True)

from backend.app.alerts.bot_listener import bot_listener


def main():
    print("=======================================================")
    print("🤖 Indian Market Intelligence — Telegram Bot Service")
    print("=======================================================")

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip() or "9074898916:AAFRMxWBsl4d3rO6uoo-dJ_9UQPJut_8chQ"
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip() or "5246742802"

    if not token:
        print("❌ Error: TELEGRAM_BOT_TOKEN is missing in .env or environment.")
        print("Get your token from @BotFather on Telegram.")
        sys.exit(1)

    print(f"📡 Authorized Chat ID: {chat_id or 'All authorized users'}")
    print("🚀 Starting Bot Listener daemon (long-polling)...")
    print("📱 You can now message your bot on Telegram:")
    print("   • /scan    — Runs Nifty 100 Screener & replies with setups")
    print("   • /morning — Sends full morning market digest")
    print("   • /status  — Checks terminal & market health")
    print("=======================================================")

    bot_listener.start(bot_token=token, authorized_chat_id=chat_id)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping Telegram Bot Service...")
        bot_listener.stop()
        print("Done.")


if __name__ == "__main__":
    main()
