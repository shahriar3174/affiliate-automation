import re

import requests

from . import config

BASE = f"https://{config.RAPIDAPI_HOST}"


def extract_asin(url: str):
    m = re.search(r"/dp/([A-Z0-9]{10})", url, re.IGNORECASE)
    return m.group(1).upper() if m else None


def _get(path: str, params: dict):
    """Try each configured RapidAPI key in order, falling back on
    rate-limit (429) or auth (401/403) errors."""
    last_exc = None
    for key in config.RAPIDAPI_KEYS:
        headers = {"x-rapidapi-host": config.RAPIDAPI_HOST, "x-rapidapi-key": key}
        try:
            r = requests.get(f"{BASE}{path}", headers=headers, params=params, timeout=30)
            if r.status_code in (401, 403, 429):
                last_exc = requests.HTTPError(f"{r.status_code} on key ...{key[-6:]}")
                continue
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            last_exc = e
            continue
    raise last_exc or RuntimeError("No RAPIDAPI_KEYS configured")


def product_details(asin: str, country="US"):
    r = _get("/product-details", {"asin": asin, "country": country})
    data = r.json().get("data", {})
    return {
        "asin": data.get("asin", asin),
        "title": data.get("product_title", ""),
        "price": data.get("product_price", ""),
        "original_price": data.get("product_original_price", ""),
        "rating": data.get("product_star_rating", ""),
        "num_ratings": data.get("product_num_ratings", ""),
        "url": data.get("product_url", f"https://www.amazon.com/dp/{asin}"),
        "photo": data.get("product_photo", ""),
        "about": data.get("about_product", []),
        "category": data.get("category_path", []),
    }


def best_sellers(category="home-garden", country="US", page=1):
    r = _get("/best-sellers", {"category": category, "type": "BEST_SELLERS",
                                "page": page, "country": country})
    return r.json().get("data", {}).get("best_sellers", [])


def affiliate_url(asin: str, platform: str):
    tag = config.AFFILIATE_TAGS.get(platform, "")
    base = f"https://www.amazon.com/dp/{asin}"
    return f"{base}?tag={tag}" if tag else base
