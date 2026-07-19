"""Daily sourcing: pick products to promote and append them to the Queue.

Two modes:
- manual rows already in Queue (asin present, no content yet) are left alone
- bestseller pull fills the remainder up to DAILY_PRODUCT_COUNT
"""
import sys

from . import amazon_api, config, sheets

BESTSELLER_CATEGORIES = [
    "home-garden",
    "kitchen",
    "fashion",
    "beauty",
    "sporting-goods",
]


def next_queue_id(rows):
    ids = [int(r["id"]) for r in rows if str(r.get("id", "")).isdigit()]
    return (max(ids) + 1) if ids else 1


def source_daily(count=None):
    count = count or config.DAILY_PRODUCT_COUNT
    sheets.setup_tabs()
    rows = sheets.queue_rows()
    seen = sheets.known_asins() | {r["asin"] for r in rows if r.get("asin")}

    added_today = [r for r in rows if r.get("date_added", "").startswith(sheets.now_iso()[:10])]
    needed = count - len(added_today)
    if needed <= 0:
        print(f"Queue already has {len(added_today)} items today, nothing to do")
        return []

    picked = []
    next_id = next_queue_id(rows)
    for category in BESTSELLER_CATEGORIES:
        if len(picked) >= needed:
            break
        try:
            items = amazon_api.best_sellers(category=category)
        except Exception as e:
            sheets.log_error("sourcing", category, e)
            continue
        for item in items:
            if len(picked) >= needed:
                break
            asin = item.get("asin")
            if not asin or asin in seen:
                continue
            try:
                details = amazon_api.product_details(asin)
            except Exception as e:
                sheets.log_error("sourcing", asin, e)
                continue
            if not details["photo"] or not details["title"]:
                continue
            row = {
                "id": next_id,
                "date_added": sheets.now_iso(),
                "asin": asin,
                "product_url": details["url"],
                "product_title": details["title"],
                "price": details["price"],
                "rating": details["rating"],
                "master_image": details["photo"],
                "pinterest_status": "new",
                "facebook_status": "new",
                "instagram_status": "new",
                "repost_count": 0,
            }
            sheets.append_queue_row(row)
            sheets.append_history(asin, details["title"])
            seen.add(asin)
            picked.append(asin)
            next_id += 1
            print(f"Added {asin}: {details['title'][:60]}")

    print(f"Sourced {len(picked)} new products")
    return picked


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else None
    source_daily(n)
