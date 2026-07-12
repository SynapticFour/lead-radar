import os
import time

import requests

CONTACT = os.environ.get("CONTACT_EMAIL", "you@yourdomain.com")
SESSION = requests.Session()
SESSION.headers["User-Agent"] = f"LeadRadar/1.0 (personal research tool; contact: {CONTACT})"


def _retry(method, url, **kwargs):
    for attempt in range(6):
        r = method(url, **kwargs)
        if r.status_code == 429:
            time.sleep(min(2**attempt, 60))
            continue
        r.raise_for_status()
        return r.json() if r.content else {}
    r.raise_for_status()


def get_json(url, **kwargs):
    return _retry(SESSION.get, url, **kwargs)


def post_json(url, data, **kwargs):
    return _retry(SESSION.post, url, data=data, **kwargs)
