from pathlib import Path

from PIL import Image

VARIANTS = {
    "pin": (1000, 1500),
    "square": (1080, 1080),
    "landscape": (1200, 630),
}


def _cover_crop(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    src_ratio = img.width / img.height
    dst_ratio = target_w / target_h
    if src_ratio > dst_ratio:
        new_w = int(img.height * dst_ratio)
        left = (img.width - new_w) // 2
        img = img.crop((left, 0, left + new_w, img.height))
    else:
        new_h = int(img.width / dst_ratio)
        top = (img.height - new_h) // 2
        img = img.crop((0, top, img.width, top + new_h))
    return img.resize((target_w, target_h), Image.LANCZOS)


def make_variants(master_path: str, out_dir: str, asin: str) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    img = Image.open(master_path).convert("RGB")
    paths = {}
    for name, (w, h) in VARIANTS.items():
        p = out / f"{asin}_{name}.jpg"
        _cover_crop(img, w, h).save(p, "JPEG", quality=92)
        paths[name] = str(p)
    return paths
