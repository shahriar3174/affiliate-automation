import requests

from .. import amazon_api, config

API = "https://api.pinterest.com/v5"


def publish(row: dict) -> str:
    """Create a pin from a queue row. Returns the pin id."""
    payload = {
        "board_id": config.PINTEREST_BOARD_ID,
        "title": row["pin_title"],
        "description": row["pin_desc"],
        "alt_text": row.get("alt_text", ""),
        "link": amazon_api.affiliate_url(row["asin"], "pinterest"),
        "media_source": {
            "source_type": "image_url",
            "url": row.get("img_pin") or row["master_image"],
        },
    }
    if row.get("dominant_color", "").startswith("#"):
        payload["dominant_color"] = row["dominant_color"]
    r = requests.post(
        f"{API}/pins",
        headers={"Authorization": f"Bearer {config.PINTEREST_ACCESS_TOKEN}"},
        json=payload,
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["id"]
