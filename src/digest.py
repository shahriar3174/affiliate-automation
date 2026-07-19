"""Weekly summary sent to Telegram (skips silently if not configured)."""
from datetime import datetime, timedelta, timezone

import requests

from . import config, sheets


def build_summary():
    rows = sheets.queue_rows()
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)

    def recent(ts):
        try:
            return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc) > week_ago
        except (ValueError, TypeError):
            return False

    lines = ["Weekly affiliate digest\n"]
    for p in ("pinterest", "facebook", "instagram"):
        n = sum(1 for r in rows if recent(r.get(f"{p}_posted_at")))
        lines.append(f"{p.capitalize()}: {n} posts")

    errors = sheets.spreadsheet().worksheet(sheets.ERRORS_TAB).get_all_records()
    recent_errors = [e for e in errors if recent(e.get("timestamp"))]
    lines.append(f"Errors this week: {len(recent_errors)}")
    for e in recent_errors[-5:]:
        lines.append(f"  - [{e.get('module')}] {e.get('item')}: {str(e.get('message'))[:80]}")

    queued = sum(1 for r in rows if r.get("pinterest_status") == "new")
    lines.append(f"Items still queued: {queued}")
    return "\n".join(lines)


def send():
    text = build_summary()
    print(text)
    if not (config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID):
        print("(Telegram not configured, printed only)")
        return
    requests.post(
        f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage",
        json={"chat_id": config.TELEGRAM_CHAT_ID, "text": text},
        timeout=30,
    ).raise_for_status()


if __name__ == "__main__":
    send()
