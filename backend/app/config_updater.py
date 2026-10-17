"""
Configuration Helper to safely read and persist Upstox API credentials to .env
"""

import os
import dotenv

ENV_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")


def save_upstox_credentials(
    api_key: str = "",
    api_secret: str = "",
    access_token: str = "",
    set_as_default_provider: bool = True
) -> bool:
    """
    Saves or updates Upstox API credentials directly into .env and runtime os.environ.
    """
    try:
        os.makedirs(os.path.dirname(ENV_FILE), exist_ok=True)
        
        # Read existing key-values
        existing = {}
        if os.path.exists(ENV_FILE):
            with open(ENV_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        existing[k.strip()] = v.strip().strip("'\"")

        # Update values
        if api_key:
            existing["UPSTOX_API_KEY"] = api_key.strip()
            os.environ["UPSTOX_API_KEY"] = api_key.strip()

        if api_secret:
            existing["UPSTOX_API_SECRET"] = api_secret.strip()
            os.environ["UPSTOX_API_SECRET"] = api_secret.strip()

        if access_token:
            existing["UPSTOX_ACCESS_TOKEN"] = access_token.strip()
            os.environ["UPSTOX_ACCESS_TOKEN"] = access_token.strip()

        if set_as_default_provider:
            existing["MARKET_DATA_PROVIDER"] = "upstox"
            os.environ["MARKET_DATA_PROVIDER"] = "upstox"

        # Write back to .env
        with open(ENV_FILE, "w", encoding="utf-8") as f:
            f.write("# Indian Stock Research Tool - Environment Configuration\n")
            for k, v in existing.items():
                f.write(f'{k}="{v}"\n')

        return True
    except Exception as e:
        print(f"Failed to update .env: {e}")
        return False


def get_current_upstox_credentials():
    """Returns current credentials in .env / os.environ."""
    dotenv.load_dotenv(ENV_FILE, override=True)
    return {
        "api_key": os.getenv("UPSTOX_API_KEY", "").strip("'\""),
        "api_secret": os.getenv("UPSTOX_API_SECRET", "").strip("'\""),
        "access_token": os.getenv("UPSTOX_ACCESS_TOKEN", "").strip("'\""),
        "provider": os.getenv("MARKET_DATA_PROVIDER", "upstox").strip("'\"")
    }
