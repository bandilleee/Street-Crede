import os
import sys
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

_FALLBACK = {"reviews": [], "follower_count": 0, "platform": "unknown"}


def _detect_platform(url: str) -> str:
    host = urlparse(url).netloc.lower()
    for name in ("facebook", "instagram", "twitter", "tiktok", "linkedin"):
        if name in host:
            return name
    return "unknown"


def handler(event, context):
    url = event.get("url", "")
    if not url:
        return _FALLBACK

    try:
        r = httpx.get(url, timeout=15, follow_redirects=True,
                      headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        # Generic review extraction: grab visible text blocks that look like reviews
        reviews = [
            p.get_text(strip=True)
            for p in soup.find_all(["p", "span", "div"], class_=lambda c: c and "review" in c.lower())
            if len(p.get_text(strip=True)) > 20
        ][:10]

        # Follower count: look for common patterns in text
        follower_count = 0
        for tag in soup.find_all(string=lambda t: t and ("follower" in t.lower() or "likes" in t.lower())):
            import re
            m = re.search(r"([\d,]+)\s*(follower|like)", tag.lower())
            if m:
                follower_count = int(m.group(1).replace(",", ""))
                break

        return {
            "reviews": reviews,
            "follower_count": follower_count,
            "platform": _detect_platform(url),
        }
    except Exception:
        return _FALLBACK
