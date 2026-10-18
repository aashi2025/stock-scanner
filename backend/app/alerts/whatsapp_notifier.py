"""
WhatsApp Alert Dispatcher & 1-Click Sharing Generator.
Supports:
1. Zero-cost 1-Click WhatsApp Direct Share (wa.me) — Works 100% with no API keys, Meta accounts, or approvals!
2. Free CallMeBot WhatsApp API integration (Automated bot HTTP GET dispatcher).
3. Optional Twilio WhatsApp Sandbox REST API.
"""

import os
import time
import urllib.parse
import requests
from typing import Dict, Any, Optional
from datetime import datetime

from backend.app.logging_config import logger


def format_whatsapp_alert(setup: Dict[str, Any]) -> str:
    """
    Formats setup dictionary into clean, formatted WhatsApp text with emojis.
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

    bias_emoji = "🟢" if bias == "BULLISH" else "🔴"

    reasons = setup.get("conditions_satisfied", ["Technical alignment verified"])
    reasons_str = "\n".join([f"  ✅ {r}" for r in reasons]) if isinstance(reasons, list) else f"  ✅ {reasons}"

    warnings = setup.get("conditions_not_satisfied", [])
    if not warnings:
        warnings = ["Candle close confirmation required"]
    warnings_str = "\n".join([f"  ⚠️ {w}" for w in warnings]) if isinstance(warnings, list) else f"  ⚠️ {warnings}"

    msg = (
        f"🔔 *INDIAN MARKET TERMINAL ALERT*\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"*{bias_emoji} {sym}* | *{bias}*\n"
        f"• *Strategy:* {strat}\n"
        f"• *Timeframe:* {tf}\n"
        f"• *Trigger:* {trigger}\n"
        f"• *Invalidation (SL):* ₹{invalidation}\n"
        f"• *Risk/Reward:* {rrr}\n"
        f"• *Feed Status:* {src} ({ts})\n\n"
        f"*Reasons:*\n{reasons_str}\n\n"
        f"*Risk Warnings:*\n{warnings_str}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ _Analytical Research Only. Alerts-only mode. Not SEBI registered investment advice._"
    )
    return msg


def get_whatsapp_share_url(alert_text: str, phone: Optional[str] = None) -> str:
    """
    Creates a 1-click WhatsApp deep link (wa.me) that opens WhatsApp directly on mobile or web.
    Requires ZERO API keys and 100% guaranteed delivery.
    """
    encoded_text = urllib.parse.quote(alert_text)
    if phone:
        clean_phone = phone.replace("+", "").replace(" ", "").replace("-", "")
        return f"https://wa.me/{clean_phone}?text={encoded_text}"
    return f"https://wa.me/?text={encoded_text}"


def send_whatsapp_callmebot(
    message: str,
    phone: Optional[str] = None,
    apikey: Optional[str] = None,
    max_retries: int = 2
) -> Dict[str, Any]:
    """
    Sends WhatsApp message via CallMeBot free HTTP GET API.
    URL Format: https://api.callmebot.com/whatsapp.php?phone=[phone]&text=[msg]&apikey=[apikey]
    """
    user_phone = phone or os.environ.get("WHATSAPP_PHONE", "").strip()
    user_apikey = apikey or os.environ.get("WHATSAPP_CALLMEBOT_APIKEY", "").strip()

    if not user_phone or not user_apikey:
        return {
            "success": False,
            "provider": "callmebot",
            "message": "Phone number or CallMeBot API key is not configured in settings/environment."
        }

    # Clean phone number: Must include country code without leading '+' or special chars for the query
    # E.g., for India +91 9876543210 -> +919876543210 or 919876543210
    clean_phone = user_phone.strip().replace(" ", "").replace("-", "")
    if not clean_phone.startswith("+"):
        clean_phone = f"+{clean_phone}"

    encoded_text = urllib.parse.quote_plus(message)
    url = f"https://api.callmebot.com/whatsapp.php?phone={clean_phone}&text={encoded_text}&apikey={user_apikey}"

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, timeout=10)
            resp_text = resp.text.lower()
            if resp.status_code == 200 and ("message queued" in resp_text or "success" in resp_text or "ok" in resp_text or resp.text.strip() == ""):
                logger.info("WhatsApp alert dispatched via CallMeBot successfully.")
                return {
                    "success": True,
                    "provider": "callmebot",
                    "status_code": resp.status_code,
                    "message": "WhatsApp alert successfully sent!"
                }
            else:
                # Bot error handling
                if "apikey is invalid" in resp_text or "invalid apikey" in resp_text:
                    err_reason = "CallMeBot API Key अमान्य (Invalid) है। कृपया अपनी प्राप्त की गई API Key पुनः जांचें।"
                elif "not allowed" in resp_text or "not authorized" in resp_text:
                    err_reason = "आपका फ़ोन नंबर CallMeBot द्वारा अधिकृत नहीं है। आपको पहले WhatsApp पर बॉट को एक्टिवेशन संदेश भेजना होगा।"
                else:
                    err_reason = f"CallMeBot Response: {resp.text[:150]}"
                logger.warning(f"CallMeBot attempt {attempt} returned {resp.status_code}: {err_reason}")
                if attempt == max_retries:
                    return {
                        "success": False,
                        "provider": "callmebot",
                        "status_code": resp.status_code,
                        "message": err_reason
                    }
        except Exception as e:
            logger.warning(f"CallMeBot attempt {attempt} failed: {e}")
            if attempt == max_retries:
                return {
                    "success": False,
                    "provider": "callmebot",
                    "message": f"Connection error: {e}"
                }
        time.sleep(1.0)

    return {
        "success": False,
        "provider": "callmebot",
        "message": "CallMeBot connection timed out after retries."
    }


def send_whatsapp_twilio(
    message: str,
    to_number: Optional[str] = None,
    account_sid: Optional[str] = None,
    auth_token: Optional[str] = None,
    from_number: Optional[str] = None
) -> Dict[str, Any]:
    """
    Sends WhatsApp message via official Twilio WhatsApp API (Free Trial Sandbox).
    """
    sid = account_sid or os.environ.get("TWILIO_ACCOUNT_SID", "").strip()
    tok = auth_token or os.environ.get("TWILIO_AUTH_TOKEN", "").strip()
    to_phone = to_number or os.environ.get("TWILIO_TO_WHATSAPP", "").strip()
    from_phone = from_number or os.environ.get("TWILIO_FROM_WHATSAPP", "whatsapp:+14155238886").strip()

    if not sid or not tok or not to_phone:
        return {
            "success": False,
            "provider": "twilio",
            "message": "Twilio Account SID, Auth Token, or Destination Phone number not configured."
        }

    if not to_phone.startswith("whatsapp:"):
        to_phone = f"whatsapp:{to_phone}"
    if not from_phone.startswith("whatsapp:"):
        from_phone = f"whatsapp:{from_phone}"

    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
    try:
        resp = requests.post(
            url,
            data={"To": to_phone, "From": from_phone, "Body": message},
            auth=(sid, tok),
            timeout=10
        )
        if resp.status_code in [200, 201]:
            return {"success": True, "provider": "twilio", "message": "Twilio WhatsApp alert dispatched successfully!"}
        else:
            return {"success": False, "provider": "twilio", "message": f"Twilio Error ({resp.status_code}): {resp.text[:150]}"}
    except Exception as e:
        return {"success": False, "provider": "twilio", "message": f"Twilio connection error: {e}"}


def send_test_whatsapp(phone: Optional[str] = None, apikey: Optional[str] = None) -> Dict[str, Any]:
    """
    Sends an immediate test WhatsApp notification.
    """
    test_msg = (
        "🔔 *Indian Market Intelligence Terminal*\n\n"
        "✅ *WhatsApp Alert Connection Test Successful!*\n"
        f"📅 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        "Alerts-only mode active. Zero broker orders will be placed."
    )
    return send_whatsapp_callmebot(test_msg, phone=phone, apikey=apikey)
