"""
Standalone Morning Telegram Alert Dispatcher Script.
Can be executed:
1. Directly from command line: python scripts/dispatch_morning_telegram.py
2. Automatically by GitHub Actions Cron every morning at 08:30 AM IST (03:00 UTC)
3. By Windows Task Scheduler or Linux crontab
"""

import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dotenv
dotenv.load_dotenv(override=True)

from backend.app.alerts.morning_scheduler import morning_scheduler


def main():
    print("=======================================================")
    print("🌅 NSE Morning Swing Market Alert Dispatcher")
    print("=======================================================")

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

    if not token or not chat_id:
        print("❌ Error: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID environment variable not found.")
        print("Please configure them in .env or GitHub Secrets.")
        sys.exit(1)

    print(f"📡 Target Chat ID: {chat_id}")
    print("⏳ Scanning Nifty 100 universe and compiling Morning Digest...")

    res = morning_scheduler.trigger_now(bot_token=token, chat_id=chat_id)

    if res.get("success"):
        print(f"✅ SUCCESS: {res.get('message')}")
        sys.exit(0)
    else:
        print(f"❌ FAILED: {res.get('message')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
