import pytest
from unittest.mock import patch, MagicMock
from backend.app.alerts.whatsapp_notifier import (
    format_whatsapp_alert,
    get_whatsapp_share_url,
    send_whatsapp_callmebot,
    send_whatsapp_twilio,
    send_test_whatsapp
)
from backend.app.alerts.manager import alert_manager


def test_format_whatsapp_alert():
    setup = {
        "symbol": "RELIANCE",
        "strategy_name": "Opening Range Breakout (ORB 15m)",
        "timeframe": "15m",
        "bias": "BULLISH",
        "entry_trigger": "Price crossed above 15m high 2950",
        "invalidation_level": 2920.0,
        "reward_risk_ratio": "1:2.0",
        "data_source": "Verified EOD Feed",
        "conditions_satisfied": ["Price > VWAP", "RVOL > 1.5x"],
        "conditions_not_satisfied": ["Candle close confirmation required"]
    }
    msg = format_whatsapp_alert(setup)
    assert "RELIANCE" in msg
    assert "BULLISH" in msg
    assert "Opening Range Breakout" in msg
    assert "2920.0" in msg
    assert "Price > VWAP" in msg
    assert "Not SEBI registered" in msg


def test_get_whatsapp_share_url():
    text = "Hello Trading Terminal"
    url_general = get_whatsapp_share_url(text)
    assert url_general.startswith("https://wa.me/?text=")
    assert "Hello" in url_general

    url_phone = get_whatsapp_share_url(text, phone="+91 9876543210")
    assert url_phone.startswith("https://wa.me/919876543210?text=")


def test_send_whatsapp_callmebot_missing_creds():
    with patch.dict("os.environ", {}, clear=True):
        res = send_whatsapp_callmebot("Test Msg", phone="", apikey="")
        assert res["success"] is False
        assert "not configured" in res["message"]


def test_send_whatsapp_callmebot_success():
    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "Message queued."
        mock_get.return_value = mock_resp

        res = send_whatsapp_callmebot("Hello", phone="+919876543210", apikey="123456")
        assert res["success"] is True
        assert res["status_code"] == 200


def test_send_whatsapp_callmebot_invalid_key():
    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = "APIKEY is invalid"
        mock_get.return_value = mock_resp

        res = send_whatsapp_callmebot("Hello", phone="+919876543210", apikey="wrongkey")
        assert res["success"] is False
        assert "अमान्य" in res["message"]


def test_alert_manager_dispatch_whatsapp():
    setup = {
        "symbol": "TCS",
        "strategy_name": "Momentum Test",
        "bias": "BULLISH",
        "timeframe": "1d",
        "invalidation_level": 3500.0,
        "reward_risk_ratio": "1:2.0"
    }
    with patch.object(alert_manager, "_send_telegram_with_retry", return_value=True):
        with patch("backend.app.alerts.manager.send_whatsapp_callmebot", return_value={"success": True}):
            res = alert_manager.dispatch_alert(setup, send_telegram=True, send_whatsapp=True)
            assert res["dispatched"] is True
            assert res["symbol"] == "TCS"
            assert "whatsapp_share_url" in res
            assert res["telegram_sent"] is True
            assert res["whatsapp_sent"] is True
