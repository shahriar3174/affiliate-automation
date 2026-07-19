# Affiliate Automation

Replaces the old Make.com scenarios. Daily flow:

```
06:00 UTC  daily_kickoff.yml
           1. src/sourcing      - pick today's 8 bestseller products (deduped), append to Queue
           2. src/content_gen   - OpenRouter LLM writes pin/fb/ig copy (variation guard vs last 30 titles)
           3. src/kaggle_trigger- push batch to Kaggle, SDXL img2img polish, pull masters,
                                  crop to pin/square/landscape, upload public to Drive
every 30m  dispatcher.yml
           src/dispatcher       - posts at most 1 item per platform (Pinterest, Facebook) when
                                  3.5h cadence elapsed via Zernio; kill switch: Config tab
                                  paused=TRUE; evergreen reposts after 30d. Instagram is not
                                  posted directly - it rides Facebook's native Page-to-Instagram
                                  auto-crosspost setting (Page Settings > Instagram).
Mon 09:00  weekly_digest.yml
           src/digest           - Telegram summary: posts/platform, errors, queue depth
```

## Google Sheet tabs (auto-created on first run)

- **Queue** — one row per product; statuses per platform; image URLs; generated copy
- **Config** — `paused` (TRUE/FALSE kill switch), `cadence_hours`
- **History** — ASIN dedupe + recent pin titles for the variation guard
- **Errors** — every failure logged here, nothing fails silently

## Setup

1. `pip install -r requirements.txt`, copy `.env.example` to `.env`, fill it in.
2. Google Cloud: create a service account, enable Sheets + Drive APIs, share the
   spreadsheet and the Drive folder with the service account email. Put the JSON
   in `service_account.json` (locally) / `GOOGLE_CREDS_JSON` secret (Actions).
3. Kaggle: verify phone (needed for GPU+internet), put username/key in env,
   edit `kaggle/kernel-metadata.json` with your username, then run
   `python -m src.kaggle_trigger` once to create the dataset + kernel.
4. Zernio (zernio.com): connect Pinterest + Facebook accounts via their dashboard
   (no developer app review needed - Zernio is already the approved app). Grab
   the API key from settings, and account IDs by running `python -m src.publishers.zernio`
   once connected (lists all accounts with their `accountId`).
5. Meta: in Facebook Page Settings > Instagram, enable "Show your Facebook posts
   on Instagram" so posts auto-crosspost - verify this actually fires before
   relying on it; if flaky, add Instagram as a 3rd Zernio account ($6/mo) instead
   and post to it directly.
6. GitHub: push this repo, add all `.env` values as Actions secrets
   (names match `.env.example`).

## Manual controls

- Pause everything: set `paused` to `TRUE` in the Config tab.
- Add a product manually: paste a row in Queue with `asin`, `product_url`,
  `product_title`, `master_image` (photo URL), statuses `new` — the daily
  kickoff fills in copy and images.
- Run any stage locally: `python -m src.sourcing`, `python -m src.content_gen`,
  `python -m src.kaggle_trigger`, `python -m src.dispatcher`, `python -m src.digest`.
