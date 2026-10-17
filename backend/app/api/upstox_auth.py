import os
import requests
import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, Body, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import AppSettingModel
from backend.app.config import settings
from backend.app.data_providers.upstox import UpstoxDataProvider
from backend.app.data_providers.upstox_instruments import instrument_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/upstox", tags=["Upstox Official Integration"])

def get_resolved_redirect_uri(request: Optional[Request] = None) -> str:
    """
    Dynamically determines the exact redirect URI based on port and host:
    1. Check if explicitly set in UPSTOX_REDIRECT_URI env var.
    2. Dynamically resolve from incoming request host (e.g. localhost:8000).
    3. Fallback to http://localhost:{settings.PORT}/api/upstox/callback.
    """
    configured = os.getenv("UPSTOX_REDIRECT_URI", "").strip("'\"")
    if configured and configured != "":
        return configured
    if request:
        host = request.headers.get("host")
        if host:
            return f"http://{host}/api/upstox/callback"
    port = getattr(settings, "PORT", 8000)
    return f"http://localhost:{port}/api/upstox/callback"

def update_env_variable(key: str, value: str):
    """Updates key in .env file safely."""
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
    lines = []
    found = False
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        for i, line in enumerate(lines):
            if line.startswith(f"{key}=") or line.startswith(f"{key} ="):
                lines[i] = f"{key}='{value}'\n"
                found = True
                break
    if not found:
        lines.append(f"{key}='{value}'\n")
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    os.environ[key] = value

@router.get("/status")
def get_upstox_status(request: Request, db: Session = Depends(get_db)):
    """Returns current Upstox API connection, exact redirect URL and token status."""
    token = os.getenv("UPSTOX_ACCESS_TOKEN", "").strip("'\"")
    api_key = os.getenv("UPSTOX_API_KEY", "").strip("'\"")
    api_secret = os.getenv("UPSTOX_API_SECRET", "").strip("'\"")

    provider = UpstoxDataProvider(access_token=token)
    token_status = provider.verify_token_status()

    mode = "AUTHENTICATED_LIVE" if token_status["valid"] else "PUBLIC_EOD_HISTORICAL"
    redirect_uri = get_resolved_redirect_uri(request)

    # Masked API Key for safety
    masked_key = (api_key[:4] + "********" + api_key[-4:]) if len(api_key) > 8 else ("********" if api_key else "")

    return {
        "status": "online",
        "provider": "Upstox API v2",
        "mode": mode,
        "is_authenticated": token_status["valid"],
        "token_reason": token_status["reason"],
        "user_name": token_status.get("user_name"),
        "user_id": token_status.get("user_id"),
        "api_key_configured": bool(api_key),
        "api_secret_configured": bool(api_secret),
        "masked_api_key": masked_key,
        "redirect_url": redirect_uri,
        "port": getattr(settings, "PORT", 8000),
        "rate_limits": {
            "per_second": 50,
            "per_minute": 500,
            "throttling_safety": "Active (Enforced locally at 20 req/sec max)",
            "monthly_cost": "₹0 / Free"
        },
        "instrument_count": len(instrument_manager.equity_map),
        "public_eod_status": "Active (Upstox official historical candles available without token)"
    }

@router.get("/login-url")
def get_login_url(request: Request):
    """Generates OAuth 2.0 authorization URL for 1-click Upstox authentication."""
    api_key = os.getenv("UPSTOX_API_KEY", "").strip("'\"")
    redirect_uri = get_resolved_redirect_uri(request)

    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="Upstox API Key (Client ID) .env में नहीं मिला। कृपया पहले अपनी API Key और Secret भरें।"
        )

    auth_url = (
        f"https://api.upstox.com/v2/login/authorization/dialog"
        f"?response_type=code&client_id={api_key}&redirect_uri={requests.utils.quote(redirect_uri)}"
    )
    return {
        "auth_url": auth_url,
        "redirect_uri": redirect_uri
    }

@router.get("/callback")
def upstox_oauth_callback(
    request: Request,
    code: str = Query(None),
    error: str = Query(None),
    db: Session = Depends(get_db)
):
    """
    OAuth Callback Handler.
    Receives auth code from Upstox, exchanges it for access_token, and safely saves it.
    """
    if error or not code:
        return HTMLResponse(
            content=f"""
            <html><body style="font-family:sans-serif;text-align:center;padding:50px;background:#0f172a;color:#fff;">
                <h2 style="color:#f87171;">Upstox Login Failed</h2>
                <p style="color:#94a3b8;">Error: {error or 'No authorization code received'}</p>
                <br>
                <a href="/" style="padding:10px 20px;background:#0284c7;color:#fff;text-decoration:none;border-radius:8px;">Return to Dashboard</a>
            </body></html>
            """,
            status_code=400
        )

    api_key = os.getenv("UPSTOX_API_KEY", "").strip("'\"")
    api_secret = os.getenv("UPSTOX_API_SECRET", "").strip("'\"")
    redirect_uri = get_resolved_redirect_uri(request)

    # Exchange code for access_token
    token_url = "https://api.upstox.com/v2/login/authorization/token"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    payload = {
        "code": code,
        "client_id": api_key,
        "client_secret": api_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }

    try:
        resp = requests.post(token_url, headers=headers, data=payload, timeout=12)
        if resp.status_code == 200:
            data = resp.json()
            access_token = data.get("access_token")
            user_name = data.get("user_name", "Upstox Trader")

            if access_token:
                # Store token securely in .env
                update_env_variable("UPSTOX_ACCESS_TOKEN", access_token)
                
                # Update DB setting
                db_setting = db.query(AppSettingModel).first()
                if db_setting:
                    db_setting.api_key = access_token
                    db.commit()

                return HTMLResponse(
                    content=f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <meta charset="utf-8">
                        <title>Upstox Login Successful</title>
                        <style>
                            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }}
                            .card {{ background: #1e293b; border: 1px solid #334155; padding: 40px; border-radius: 16px; text-align: center; max-width: 450px; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.5); }}
                            h2 {{ color: #4ade80; margin-top: 0; }}
                            p {{ color: #94a3b8; font-size: 14px; line-height: 1.6; }}
                            .btn {{ display: inline-block; margin-top: 20px; padding: 12px 24px; background: #0284c7; color: white; text-decoration: none; border-radius: 10px; font-weight: bold; transition: background 0.2s; }}
                            .btn:hover {{ background: #0369a1; }}
                        </style>
                    </head>
                    <body>
                        <div class="card">
                            <h2>✅ Upstox Login Successful!</h2>
                            <p>स्वागत है <strong>{user_name}</strong>!</p>
                            <p>आपका Access Token सुरक्षित रूप से सक्रिय हो चुका है। अब Live Market Quotes और पूर्ण Upstox API सेवाएँ चालू हैं।</p>
                            <a href="/" class="btn">Go to Dashboard</a>
                        </div>
                    </body>
                    </html>
                    """
                )
        return HTMLResponse(
            content=f"""
            <html><body style="font-family:sans-serif;text-align:center;padding:50px;background:#0f172a;color:#fff;">
                <h2 style="color:#f87171;">Token Exchange Failed (Status {resp.status_code})</h2>
                <p style="color:#94a3b8;">Response: {resp.text}</p>
                <p style="color:#cbd5e1;font-size:12px;">Make sure your API Secret matches the one in Upstox Developer Console.</p>
                <br>
                <a href="/" style="padding:10px 20px;background:#0284c7;color:#fff;text-decoration:none;border-radius:8px;">Return to Dashboard</a>
            </body></html>
            """,
            status_code=400
        )
    except Exception as e:
        logger.error(f"Error in token exchange: {e}")
        return HTMLResponse(
            content=f"""
            <html><body style="font-family:sans-serif;text-align:center;padding:50px;background:#0f172a;color:#fff;">
                <h2 style="color:#f87171;">Connection Error</h2>
                <p style="color:#94a3b8;">{e}</p>
                <br>
                <a href="/" style="padding:10px 20px;background:#0284c7;color:#fff;text-decoration:none;border-radius:8px;">Return to Dashboard</a>
            </body></html>
            """,
            status_code=500
        )

@router.post("/credentials")
def save_credentials(
    api_key: str = Body(..., embed=True),
    api_secret: str = Body(..., embed=True),
    redirect_uri: Optional[str] = Body(None, embed=True)
):
    """
    Saves API Key and Secret into .env file securely.
    Ensures credentials are saved on local machine only.
    """
    clean_key = api_key.strip().strip("'\"")
    clean_secret = api_secret.strip().strip("'\"")

    if not clean_key or not clean_secret:
        raise HTTPException(status_code=400, detail="API Key और API Secret खाली नहीं हो सकते।")

    update_env_variable("UPSTOX_API_KEY", clean_key)
    update_env_variable("UPSTOX_API_SECRET", clean_secret)
    
    if redirect_uri:
        update_env_variable("UPSTOX_REDIRECT_URI", redirect_uri.strip().strip("'\""))

    return {
        "status": "success",
        "message": "Upstox API Key और API Secret सुरक्षित रूप से .env में सेव हो गए हैं।"
    }

@router.post("/set-token")
def set_token_manually(token: str = Body(..., embed=True), db: Session = Depends(get_db)):
    """Allows manual token paste from Upstox Developer Console."""
    clean_token = token.strip().strip("'\"")
    if not clean_token:
        raise HTTPException(status_code=400, detail="Token cannot be empty")
    
    provider = UpstoxDataProvider(access_token=clean_token)
    status = provider.verify_token_status()
    if not status["valid"]:
        raise HTTPException(status_code=400, detail=f"Token verification failed: {status['reason']}")
    
    update_env_variable("UPSTOX_ACCESS_TOKEN", clean_token)
    return {
        "status": "success",
        "message": f"Upstox token verified and saved! Active user: {status.get('user_name')}",
        "user_name": status.get("user_name")
    }

@router.post("/sync-instruments")
def sync_instruments():
    """Forces sync of official Upstox NSE instrument list."""
    ok = instrument_manager.download_and_update_instruments()
    return {
        "success": ok,
        "total_equities": len(instrument_manager.equity_map),
        "total_indices": len(instrument_manager.index_map)
    }
