"""
Unit Tests for Telegram Digest, Morning Scheduler, and On-Demand Bot Listener.
"""

import pytest
from unittest.mock import patch, MagicMock
from backend.app.alerts.telegram_digest import (
    split_telegram_message,
    send_telegram_message_safe,
    generate_morning_telegram_digest,
    generate_instant_screener_telegram_alert
)
from backend.app.alerts.morning_scheduler import morning_scheduler
from backend.app.alerts.bot_listener import TelegramBotListener


def test_split_telegram_message():
    short_text = "Hello Trading Terminal"
    assert split_telegram_message(short_text, max_chars=100) == [short_text]

    # Long text with lines
    long_text = "\n".join([f"Line {i}: Stock setup alert description content" for i in range(100)])
    chunks = split_telegram_message(long_text, max_chars=500)
    assert len(chunks) > 1
    for c in chunks:
        assert len(c) <= 600 # within margin
    # Full content reconstructed
    assert "".join(chunks).replace("\n", "") == long_text.replace("\n", "")


def test_generate_instant_screener_telegram_alert():
    mock_results = [
        {
            "symbol": "RELIANCE",
            "cmp": 1390.0,
            "signal": "🟢 READY TO BUY",
            "setup_type": "Setup A: EMA Pullback / Support Test",
            "entry_level": 1390.0,
            "stop_loss": 1345.0,
            "sl_pct": 3.2,
            "target_level": 1480.0,
            "target_pct": 6.5,
            "risk_reward_ratio": "1:2.0",
            "rsi_14": 58.2,
            "ema_200": 1330.0
        }
    ]
    msg = generate_instant_screener_telegram_alert(mock_results)
    assert "RELIANCE" in msg
    assert "READY TO BUY" in msg
    assert "1,390.00" in msg or "1390" in msg
    assert "1:2.0" in msg


def test_generate_morning_telegram_digest():
    mock_results = [
        {
            "symbol": "TCS",
            "cmp": 2500.0,
            "signal": "🟢 READY TO BUY",
            "setup_type": "Setup B: Solid Breakout",
            "entry_level": 2500.0,
            "stop_loss": 2420.0,
            "sl_pct": 3.2,
            "target_level": 2660.0,
            "target_pct": 6.4,
            "risk_reward_ratio": "1:2.0",
            "rsi_14": 62.0,
            "ema_200": 2400.0
        }
    ]
    digest = generate_morning_telegram_digest(mock_results)
    assert "MORNING SWING MARKET DIGEST" in digest
    assert "TCS" in digest
    assert "2660" in digest or "2,660.00" in digest


def test_send_telegram_message_safe_success():
    with patch("requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "ok"
        mock_post.return_value = mock_resp

        res = send_telegram_message_safe("Test Message", bot_token="12345:TEST", chat_id="98765")
        assert res["success"] is True
        assert res["sent_chunks"] == 1


def test_send_telegram_message_safe_missing_creds():
    with patch.dict("os.environ", {}, clear=True):
        res = send_telegram_message_safe("Test Message", bot_token="", chat_id="")
        assert res["success"] is False
        assert "not configured" in res["message"]


def test_morning_scheduler_trigger_now():
    with patch("backend.app.alerts.morning_scheduler.generate_morning_telegram_digest") as mock_digest:
        mock_digest.return_value = "Mock Morning Digest Text"
        with patch("backend.app.alerts.morning_scheduler.send_telegram_message_safe") as mock_send:
            mock_send.return_value = {"success": True, "message": "Dispatched"}
            res = morning_scheduler.trigger_now(bot_token="12345", chat_id="99999")
            assert res["success"] is True


def test_telegram_bot_listener_handle_command():
    listener = TelegramBotListener()
    with patch("backend.app.alerts.bot_listener.send_telegram_message_safe") as mock_send:
        mock_send.return_value = {"success": True}

        # Test /help
        listener._handle_command("TOKEN", "CHAT_ID", "/help")
        assert mock_send.called

        # Test /status
        listener._handle_command("TOKEN", "CHAT_ID", "/status")
        assert mock_send.called
