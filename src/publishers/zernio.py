"""Publisher for Pinterest + Facebook via Zernio's unified API
(https://docs.zernio.com). Instagram is not posted directly here — it rides
on Facebook's native Page-to-Instagram auto-crosspost setting instead."""
import requests

from .. import amazon_api, config

API = "https://zernio.com/api/v1/posts"

PLATFORM_MAP = {
    "pinterest": "pinterest",
    "facebook": "facebook",
}


def _content(row: dict, platform: str) -> str:
    link = amazon_api.affiliate_url(row["asin"], platform)
    if platform == "pinterest":
        return row["pin_desc"]
    if platform == "facebook":
        return f"{row['fb_text']}\n\n{link}"
    raise ValueError(f"Unknown platform: {platform}")


def _image_for(row: dict, platform: str) -> str:
    if platform == "pinterest":
        return row.get("img_pin") or row["master_image"]
    return row.get("img_landscape") or row.get("img_square") or row["master_image"]


def _platform_specific(row: dict, platform: str) -> dict:
    if platform == "pinterest":
        return {
            "boardId": config.PINTEREST_BOARD_ID,
            "title": row["pin_title"],
            "link": amazon_api.affiliate_url(row["asin"], "pinterest"),
        }
    if platform == "facebook":
        data = {}
        if config.META_PAGE_ID:
            data["pageId"] = config.META_PAGE_ID
        return data
    return {}


def publish(row: dict, platform: str) -> str:
    account_id = config.ZERNIO_ACCOUNT_IDS.get(platform)
    if not account_id:
        raise RuntimeError(f"No Zernio account id configured for {platform}")

    payload = {
        "content": _content(row, platform),
        "mediaItems": [{"type": "image", "url": _image_for(row, platform)}],
        "platforms": [{
            "platform": PLATFORM_MAP[platform],
            "accountId": account_id,
            "platformSpecificData": _platform_specific(row, platform),
        }],
        "publishNow": True,
    }
    r = requests.post(
        API,
        headers={
            "Authorization": f"Bearer {config.ZERNIO_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=60,
    )
    r.raise_for_status()
    data = r.json()
    if isinstance(data, dict) and data.get("error"):
        raise RuntimeError(data["error"])
    return str(data.get("id") or data.get("postId") or data.get("_id") or "posted")


def list_accounts() -> list:
    """Helper for one-time setup: run this to find your accountId values."""
    r = requests.get(
        "https://zernio.com/api/v1/accounts",
        headers={"Authorization": f"Bearer {config.ZERNIO_API_KEY}"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


if __name__ == "__main__":
    import json
    print(json.dumps(list_accounts(), indent=2))
