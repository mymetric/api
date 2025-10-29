import os
import requests
from datetime import datetime, timezone
from typing import Optional, Dict, Any


def _get_iso_utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def log_to_better_stack(
    message: str,
    level: str = "info",
    extra: Optional[Dict[str, Any]] = None,
    token: Optional[str] = None,
    url: Optional[str] = None,
) -> bool:
    """Send a log entry to Better Stack. Returns True on success, False otherwise.

    Configuration via env (falls back if args not provided):
      - BETTER_STACK_TOKEN
      - BETTER_STACK_URL  (e.g. https://sXXXX.eu-YYY.betterstackdata.com)
    """

    import json

    def _load_telemetry_json():
        try:
            with open("credentials/telemetry.json", "r") as f:
                data = json.load(f)
            return data
        except Exception:
            return {}

    _telemetry_data = _load_telemetry_json()

    bs_token = (
        token
        or os.getenv("BETTER_STACK_TOKEN")
        or _telemetry_data.get("token")
    )
    bs_url = (
        url
        or os.getenv("BETTER_STACK_URL")
        or _telemetry_data.get("url")
    )

    if not bs_token or not bs_url:
        # Silently skip if not configured
        return False

    headers = {
        "Authorization": f"Bearer {bs_token}",
        "Content-Type": "application/json",
    }

    payload: Dict[str, Any] = {
        "dt": _get_iso_utc_now(),
        "message": message,
        "level": level,
    }

    if extra:
        # Flatten common fields or attach under 'extra'
        payload["extra"] = extra

    try:
        resp = requests.post(bs_url, json=payload, headers=headers, timeout=5)
        return 200 <= resp.status_code < 300
    except Exception:
        return False


