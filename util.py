from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Optional, Union

import requests

CONTACT = os.environ.get("CONTACT_EMAIL", "you@yourdomain.com")
SESSION = requests.Session()
SESSION.headers["User-Agent"] = (
    f"LeadRadar/1.0 (personal research tool; contact: {CONTACT})"
)


def load_dotenv(path: Optional[Union[str, Path]] = None) -> None:
    """Load KEY=VALUE pairs from .env into os.environ (no overwrite)."""
    env_path = Path(path) if path else Path(__file__).parent / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def _retry(method, url, **kwargs):
    for attempt in range(6):
        r = method(url, **kwargs)
        if r.status_code == 429:
            time.sleep(min(2**attempt, 60))
            continue
        r.raise_for_status()
        return r
    r.raise_for_status()


def get_json(url, **kwargs):
    r = _retry(SESSION.get, url, **kwargs)
    return r.json() if r.content else {}


def get_text(url, **kwargs):
    r = _retry(SESSION.get, url, **kwargs)
    return r.text or ""


def post_json(url, data, **kwargs):
    r = _retry(SESSION.post, url, data=data, **kwargs)
    return r.json() if r.content else {}
