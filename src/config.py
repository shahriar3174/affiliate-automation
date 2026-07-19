import json
import os

from dotenv import load_dotenv

load_dotenv()


def env(key, default=None, required=False):
    val = os.getenv(key, default)
    if required and not val:
        raise RuntimeError(f"Missing required env var: {key}")
    return val


SPREADSHEET_ID = env("SPREADSHEET_ID", required=True)
DRIVE_FOLDER_ID = env("DRIVE_FOLDER_ID")

RAPIDAPI_HOST = env("RAPIDAPI_HOST", "real-time-amazon-data.p.rapidapi.com")
RAPIDAPI_KEYS = [k.strip() for k in env("RAPIDAPI_KEYS", "").split(",") if k.strip()]
if not RAPIDAPI_KEYS:
    single = env("RAPIDAPI_KEY")
    RAPIDAPI_KEYS = [single] if single else []

OPENROUTER_API_KEY = env("OPENROUTER_API_KEY")
_default_models = "google/gemma-4-31b-it:free,google/gemma-4-26b-a4b-it:free,nvidia/nemotron-3-nano-30b-a3b:free"
OPENROUTER_MODELS = [m.strip() for m in env("OPENROUTER_MODELS", _default_models).split(",") if m.strip()]

AFFILIATE_TAGS = {
    "pinterest": env("AFFILIATE_TAG_PINTEREST", ""),
    "facebook": env("AFFILIATE_TAG_FACEBOOK", ""),
    "instagram": env("AFFILIATE_TAG_INSTAGRAM", ""),
}

PINTEREST_ACCESS_TOKEN = env("PINTEREST_ACCESS_TOKEN")
PINTEREST_BOARD_ID = env("PINTEREST_BOARD_ID")

META_PAGE_ID = env("META_PAGE_ID")
META_PAGE_ACCESS_TOKEN = env("META_PAGE_ACCESS_TOKEN")
IG_USER_ID = env("IG_USER_ID")

KAGGLE_NOTEBOOK_SLUG = env("KAGGLE_NOTEBOOK_SLUG")

TELEGRAM_BOT_TOKEN = env("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = env("TELEGRAM_CHAT_ID")

DAILY_PRODUCT_COUNT = int(env("DAILY_PRODUCT_COUNT", "8"))
CADENCE_HOURS = float(env("CADENCE_HOURS", "3.5"))
EVERGREEN_REPOST_DAYS = int(env("EVERGREEN_REPOST_DAYS", "30"))
HISTORY_TITLES_FOR_VARIATION = 30


def google_credentials():
    from google.oauth2.service_account import Credentials

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    inline = os.getenv("GOOGLE_CREDS_JSON")
    if inline:
        return Credentials.from_service_account_info(json.loads(inline), scopes=scopes)
    path = env("GOOGLE_CREDS_FILE", "service_account.json")
    return Credentials.from_service_account_file(path, scopes=scopes)
