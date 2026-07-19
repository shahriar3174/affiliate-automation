from datetime import datetime, timezone

import gspread

from . import config

QUEUE_TAB = "Queue"
CONFIG_TAB = "Config"
HISTORY_TAB = "History"
ERRORS_TAB = "Errors"

QUEUE_COLUMNS = [
    "id", "date_added", "asin", "product_url", "product_title", "price",
    "rating", "master_image", "img_pin", "img_square", "img_landscape",
    "pin_title", "pin_desc", "alt_text", "fb_text", "ig_caption",
    "dominant_color",
    "pinterest_status", "pinterest_posted_at", "pinterest_pin_id",
    "facebook_status", "facebook_posted_at",
    "instagram_status", "instagram_posted_at",
    "repost_count", "last_reposted_at",
]

HISTORY_COLUMNS = ["asin", "title", "pin_title", "date"]
ERROR_COLUMNS = ["timestamp", "module", "item", "message"]

_client = None


def client():
    global _client
    if _client is None:
        _client = gspread.authorize(config.google_credentials())
    return _client


def spreadsheet():
    return client().open_by_key(config.SPREADSHEET_ID)


def _ensure_tab(name, columns):
    ss = spreadsheet()
    try:
        ws = ss.worksheet(name)
    except gspread.WorksheetNotFound:
        ws = ss.add_worksheet(name, rows=1000, cols=len(columns))
        ws.append_row(columns)
    return ws


def setup_tabs():
    _ensure_tab(QUEUE_TAB, QUEUE_COLUMNS)
    _ensure_tab(HISTORY_TAB, HISTORY_COLUMNS)
    _ensure_tab(ERRORS_TAB, ERROR_COLUMNS)
    ss = spreadsheet()
    try:
        ss.worksheet(CONFIG_TAB)
    except gspread.WorksheetNotFound:
        ws = ss.add_worksheet(CONFIG_TAB, rows=20, cols=2)
        ws.update("A1:B3", [["key", "value"], ["paused", "FALSE"], ["cadence_hours", "3.5"]])


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def is_paused():
    ws = spreadsheet().worksheet(CONFIG_TAB)
    for row in ws.get_all_records():
        if str(row.get("key", "")).lower() == "paused":
            return str(row.get("value", "")).strip().upper() == "TRUE"
    return False


def get_config_value(key, default=None):
    ws = spreadsheet().worksheet(CONFIG_TAB)
    for row in ws.get_all_records():
        if str(row.get("key", "")).lower() == key.lower():
            return row.get("value")
    return default


def queue_rows():
    ws = spreadsheet().worksheet(QUEUE_TAB)
    records = ws.get_all_records()
    for i, rec in enumerate(records):
        rec["_row"] = i + 2
    return records


def append_queue_row(item: dict):
    ws = spreadsheet().worksheet(QUEUE_TAB)
    ws.append_row([str(item.get(col, "")) for col in QUEUE_COLUMNS],
                  value_input_option="RAW")


def update_queue_cells(row_number: int, updates: dict):
    ws = spreadsheet().worksheet(QUEUE_TAB)
    cells = []
    for col_name, value in updates.items():
        col_idx = QUEUE_COLUMNS.index(col_name) + 1
        cells.append(gspread.Cell(row_number, col_idx, str(value)))
    if cells:
        ws.update_cells(cells, value_input_option="RAW")


def known_asins():
    ws = spreadsheet().worksheet(HISTORY_TAB)
    return {r["asin"] for r in ws.get_all_records() if r.get("asin")}


def recent_pin_titles(limit=config.HISTORY_TITLES_FOR_VARIATION):
    ws = spreadsheet().worksheet(HISTORY_TAB)
    titles = [r["pin_title"] for r in ws.get_all_records() if r.get("pin_title")]
    return titles[-limit:]


def append_history(asin, title, pin_title=""):
    ws = spreadsheet().worksheet(HISTORY_TAB)
    ws.append_row([asin, title, pin_title, now_iso()], value_input_option="RAW")


def log_error(module, item, message):
    ws = spreadsheet().worksheet(ERRORS_TAB)
    ws.append_row([now_iso(), module, str(item), str(message)[:500]],
                  value_input_option="RAW")
