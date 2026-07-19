import time

import requests

from .. import config

GRAPH = "https://graph.facebook.com/v21.0"


def publish(row: dict) -> str:
    """Two-step IG publish: create media container, then publish it.
    Link goes in bio (caption says so) since IG captions/comments aren't clickable."""
    token = config.META_PAGE_ACCESS_TOKEN
    r = requests.post(
        f"{GRAPH}/{config.IG_USER_ID}/media",
        data={
            "image_url": row.get("img_square") or row["master_image"],
            "caption": row["ig_caption"],
            "access_token": token,
        },
        timeout=60,
    )
    r.raise_for_status()
    container_id = r.json()["id"]

    for _ in range(10):
        s = requests.get(
            f"{GRAPH}/{container_id}",
            params={"fields": "status_code", "access_token": token},
            timeout=30,
        ).json()
        if s.get("status_code") == "FINISHED":
            break
        time.sleep(5)

    r = requests.post(
        f"{GRAPH}/{config.IG_USER_ID}/media_publish",
        data={"creation_id": container_id, "access_token": token},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["id"]
