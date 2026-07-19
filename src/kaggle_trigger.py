"""Push today's batch to Kaggle, run the polish kernel, pull results, build
platform variants, upload to Drive, and write image URLs back to the Queue."""
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

from . import config, images, sheets

DATASET_SLUG = "product-batch-input"
POLL_SECONDS = 60
MAX_WAIT_MINUTES = 45

# The kaggle CLI writes kernel logs without specifying an encoding, which
# crashes on Windows (cp1252) if the log contains non-ASCII characters (e.g.
# pip's Unicode progress bars). Forcing UTF-8 mode on the subprocess avoids it.
_ENV = {**os.environ, "PYTHONUTF8": "1"}


def _run(cmd, **kw):
    print("+", " ".join(cmd))
    return subprocess.run(cmd, check=True, capture_output=True, text=True, env=_ENV, **kw)


def pending_rows():
    return [r for r in sheets.queue_rows()
            if r.get("master_image", "").startswith("http")
            and not r.get("img_pin")]


def push_batch_dataset(batch, workdir: Path):
    ds_dir = workdir / "dataset"
    ds_dir.mkdir()
    (ds_dir / "batch.json").write_text(json.dumps(batch))
    meta = {
        "title": DATASET_SLUG,
        "id": f"{config.KAGGLE_USERNAME}/{DATASET_SLUG}",
        "licenses": [{"name": "CC0-1.0"}],
    }
    (ds_dir / "dataset-metadata.json").write_text(json.dumps(meta))
    try:
        _run(["kaggle", "datasets", "version", "-p", str(ds_dir), "-m", "daily batch"])
    except subprocess.CalledProcessError:
        _run(["kaggle", "datasets", "create", "-p", str(ds_dir)])


def run_kernel_and_wait():
    slug = config.KAGGLE_NOTEBOOK_SLUG
    _run(["kaggle", "kernels", "push", "-p", "kaggle"])
    deadline = time.time() + MAX_WAIT_MINUTES * 60
    while time.time() < deadline:
        time.sleep(POLL_SECONDS)
        out = _run(["kaggle", "kernels", "status", slug]).stdout
        print(out.strip())
        if "complete" in out.lower():
            return True
        if "error" in out.lower() or "cancel" in out.lower():
            raise RuntimeError(f"Kaggle kernel failed: {out.strip()}")
    raise TimeoutError("Kaggle kernel did not finish in time")


def pull_outputs(workdir: Path) -> Path:
    out_dir = workdir / "masters"
    out_dir.mkdir()
    _run(["kaggle", "kernels", "output", config.KAGGLE_NOTEBOOK_SLUG, "-p", str(out_dir)])
    return out_dir


REPO_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = REPO_ROOT / "assets" / "images"


def publish_assets_to_github(ready_asins):
    """Commit and push the generated variants so raw.githubusercontent.com
    serves them - permanent public URLs with no storage-quota issues
    (service accounts can't own files in a personal Drive)."""
    _run(["git", "-C", str(REPO_ROOT), "add", "assets/images"])
    status = _run(["git", "-C", str(REPO_ROOT), "status", "--porcelain", "assets/images"]).stdout
    if not status.strip():
        print("no new assets to push")
        return
    _run(["git", "-C", str(REPO_ROOT), "commit", "-m",
          f"Add polished images: {', '.join(ready_asins)}"])
    _run(["git", "-C", str(REPO_ROOT), "push"])


def process_batch():
    config.ensure_kaggle_auth()
    rows = pending_rows()
    if not rows:
        print("No pending images")
        return
    batch = [{"asin": r["asin"], "image_url": r["master_image"],
              "title": r.get("product_title", "")} for r in rows]

    with tempfile.TemporaryDirectory() as tmp:
        workdir = Path(tmp)
        push_batch_dataset(batch, workdir)
        run_kernel_and_wait()
        masters = pull_outputs(workdir)

        ready = []
        for row in rows:
            asin = row["asin"]
            master = masters / f"{asin}.png"
            if not master.exists():
                sheets.log_error("kaggle", asin, "no output image from kernel")
                continue
            try:
                images.make_variants(str(master), str(ASSETS_DIR), asin)
                ready.append((row, asin))
            except Exception as e:
                sheets.log_error("kaggle", asin, e)

        if not ready:
            print("no images produced")
            return

        publish_assets_to_github([asin for _, asin in ready])

        base = config.ASSETS_BASE_URL.rstrip("/")
        for row, asin in ready:
            urls = {
                "img_pin": f"{base}/{asin}_pin.jpg",
                "img_square": f"{base}/{asin}_square.jpg",
                "img_landscape": f"{base}/{asin}_landscape.jpg",
            }
            sheets.update_queue_cells(row["_row"], urls)
            print(f"images ready: {asin}")


if __name__ == "__main__":
    process_batch()
