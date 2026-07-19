"""Runs on a short cron (e.g. every 30 min). Posts at most one item per platform
per run, only when the cadence window has elapsed. Honors the Config 'paused' flag."""
from datetime import datetime, timedelta, timezone

from . import config, sheets
from .publishers import zernio

# Instagram isn't posted directly - it rides on Facebook's native
# Page-to-Instagram auto-crosspost setting instead of a separate API call.
PLATFORMS = ["pinterest", "facebook"]


def _parse(ts):
    try:
        return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def _ready(row, platform):
    if row.get(f"{platform}_status") != "new":
        return False
    if not row.get("pin_title"):
        return False
    if platform == "pinterest" and not (row.get("img_pin") or row.get("master_image")):
        return False
    return True


def _last_posted(rows, platform):
    times = [_parse(r.get(f"{platform}_posted_at")) for r in rows]
    times = [t for t in times if t]
    return max(times) if times else None


def _evergreen_candidate(rows):
    cutoff = datetime.now(timezone.utc) - timedelta(days=config.EVERGREEN_REPOST_DAYS)
    posted = [r for r in rows
              if r.get("pinterest_status") == "posted"
              and (_parse(r.get("last_reposted_at")) or _parse(r.get("pinterest_posted_at")) or datetime.now(timezone.utc)) < cutoff
              and r.get("img_pin")]
    posted.sort(key=lambda r: int(r.get("repost_count") or 0))
    return posted[0] if posted else None


def run():
    if sheets.is_paused():
        print("Paused via Config tab, exiting")
        return

    cadence = timedelta(hours=float(sheets.get_config_value("cadence_hours", config.CADENCE_HOURS)))
    rows = sheets.queue_rows()
    now = datetime.now(timezone.utc)

    for platform in PLATFORMS:
        last = _last_posted(rows, platform)
        if last and now - last < cadence:
            print(f"{platform}: not due (last {last:%H:%M}, cadence {cadence})")
            continue

        candidates = [r for r in rows if _ready(r, platform)]
        item = candidates[0] if candidates else None
        is_repost = False

        if item is None and platform == "pinterest":
            item = _evergreen_candidate(rows)
            is_repost = item is not None

        if item is None:
            print(f"{platform}: nothing ready")
            continue

        try:
            post_id = zernio.publish(item, platform)
            updates = {}
            if is_repost:
                updates["repost_count"] = int(item.get("repost_count") or 0) + 1
                updates["last_reposted_at"] = sheets.now_iso()
            else:
                updates[f"{platform}_status"] = "posted"
                updates[f"{platform}_posted_at"] = sheets.now_iso()
                if platform == "pinterest":
                    updates["pinterest_pin_id"] = post_id
                    sheets.append_history(item["asin"], item.get("product_title", ""),
                                          item.get("pin_title", ""))
            sheets.update_queue_cells(item["_row"], updates)
            print(f"{platform}: posted {item['asin']} ({'repost' if is_repost else 'new'}) -> {post_id}")
        except Exception as e:
            sheets.log_error(f"dispatcher/{platform}", item.get("asin"), e)
            print(f"{platform}: FAILED {item.get('asin')}: {e}")


if __name__ == "__main__":
    run()
