import requests

from .. import amazon_api, config

GRAPH = "https://graph.facebook.com/v21.0"


def publish(row: dict) -> str:
    """Photo post on the Page with the affiliate link in the message."""
    link = amazon_api.affiliate_url(row["asin"], "facebook")
    message = f"{row['fb_text']}\n\n{link}"
    r = requests.post(
        f"{GRAPH}/{config.META_PAGE_ID}/photos",
        data={
            "url": row.get("img_landscape") or row.get("img_square") or row["master_image"],
            "message": message,
            "access_token": config.META_PAGE_ACCESS_TOKEN,
        },
        timeout=60,
    )
    r.raise_for_status()
    return r.json().get("post_id") or r.json()["id"]
