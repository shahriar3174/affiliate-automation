"""Kaggle batch img2img polish. Runs once per day on GPU, then the session ends.

Input:  /kaggle/input/<dataset>/batch.json  ->  [{"asin": ..., "image_url": ...}, ...]
Output: /kaggle/working/<asin>.png (768x768 masters)
"""
import json
import os
import subprocess
import sys
from io import BytesIO

# Kaggle's pre-installed torch build sometimes drops support for the older
# P100 GPU (sm_60) that Kaggle's free scheduler can assign. Install a known
# torch/cu118 build that covers Pascal through Hopper (sm_60-sm_90) instead
# of trusting whatever is baked into the image.
subprocess.run([
    sys.executable, "-m", "pip", "install", "-q",
    "torch==2.4.1", "torchvision==0.19.1",
    "--index-url", "https://download.pytorch.org/whl/cu118",
], check=True)
subprocess.run([
    sys.executable, "-m", "pip", "install", "-q",
    "diffusers==0.31.0", "transformers==4.44.2", "accelerate==0.34.2", "safetensors",
], check=True)
print("deps installed", flush=True)

import requests
import torch
from diffusers import StableDiffusionImg2ImgPipeline
from PIL import Image

print("torch:", torch.__version__, "cuda available:", torch.cuda.is_available(), flush=True)
if torch.cuda.is_available():
    print("device:", torch.cuda.get_device_name(0), "capability:", torch.cuda.get_device_capability(0), flush=True)

PROMPT_TEMPLATE = (
    "{title}, exact same product and colors, professional product photograph, "
    "premium commercial photography, studio lighting, balanced composition, product centered, "
    "clean premium background, realistic shadows and reflections, sharp focus, DSLR quality, "
    "high-end e-commerce advertising photo"
)
NEGATIVE = (
    "different color, color shift, hue change, cartoon, illustration, painting, fantasy, "
    "artistic, cluttered, busy background, unrealistic colors, distorted product, "
    "altered logo, text, watermark, low quality, blurry"
)
STRENGTH = 0.22
SIZE = 768

batch_file = None
for root, _, files in os.walk("/kaggle/input"):
    if "batch.json" in files:
        batch_file = os.path.join(root, "batch.json")
        break
assert batch_file, "batch.json not found in any attached dataset"

with open(batch_file) as f:
    batch = json.load(f)
print(f"{len(batch)} images to process", flush=True)

print("loading SD 1.5 img2img pipeline...", flush=True)
pipe = StableDiffusionImg2ImgPipeline.from_pretrained(
    "stable-diffusion-v1-5/stable-diffusion-v1-5",
    torch_dtype=torch.float16,
    safety_checker=None,
).to("cuda")
pipe.enable_attention_slicing()
print("pipeline loaded", flush=True)

for item in batch:
    asin = item["asin"]
    try:
        print(f"processing {asin}...", flush=True)
        resp = requests.get(item["image_url"], timeout=30)
        resp.raise_for_status()
        src = Image.open(BytesIO(resp.content)).convert("RGB")

        side = max(src.size)
        canvas = Image.new("RGB", (side, side), (255, 255, 255))
        canvas.paste(src, ((side - src.width) // 2, (side - src.height) // 2))
        canvas = canvas.resize((SIZE, SIZE), Image.LANCZOS)

        title = (item.get("title") or "product")[:120]
        out = pipe(
            prompt=PROMPT_TEMPLATE.format(title=title),
            negative_prompt=NEGATIVE,
            image=canvas,
            strength=STRENGTH,
            guidance_scale=6.0,
            num_inference_steps=25,
        ).images[0]
        out.save(f"/kaggle/working/{asin}.png")
        print(f"done: {asin}", flush=True)
    except Exception as e:
        print(f"FAILED {asin}: {e}", flush=True)

print("batch complete", flush=True)
