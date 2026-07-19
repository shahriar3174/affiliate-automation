"""Kaggle batch img2img polish. Runs once per day on GPU, then the session ends.

Input:  /kaggle/input/<dataset>/batch.json  ->  [{"asin": ..., "image_url": ...}, ...]
Output: /kaggle/working/<asin>.png (1024x1024 masters)
"""
import json
import os
from io import BytesIO

import requests
import torch
from diffusers import StableDiffusionXLImg2ImgPipeline
from PIL import Image

PROMPT = (
    "professional product photograph, premium commercial photography, studio lighting, "
    "balanced composition, product centered, clean premium background, realistic shadows "
    "and reflections, sharp focus, DSLR quality, high-end e-commerce advertising photo"
)
NEGATIVE = (
    "cartoon, illustration, painting, fantasy, artistic, cluttered, busy background, "
    "unrealistic colors, distorted product, altered logo, text, watermark, low quality, blurry"
)
STRENGTH = 0.35

batch_file = None
for root, _, files in os.walk("/kaggle/input"):
    if "batch.json" in files:
        batch_file = os.path.join(root, "batch.json")
        break
assert batch_file, "batch.json not found in any attached dataset"

with open(batch_file) as f:
    batch = json.load(f)
print(f"{len(batch)} images to process")

pipe = StableDiffusionXLImg2ImgPipeline.from_pretrained(
    "stabilityai/stable-diffusion-xl-base-1.0",
    torch_dtype=torch.float16,
    variant="fp16",
    use_safetensors=True,
).to("cuda")
pipe.enable_attention_slicing()

for item in batch:
    asin = item["asin"]
    try:
        resp = requests.get(item["image_url"], timeout=30)
        resp.raise_for_status()
        src = Image.open(BytesIO(resp.content)).convert("RGB")

        side = max(src.size)
        canvas = Image.new("RGB", (side, side), (255, 255, 255))
        canvas.paste(src, ((side - src.width) // 2, (side - src.height) // 2))
        canvas = canvas.resize((1024, 1024), Image.LANCZOS)

        out = pipe(
            prompt=PROMPT,
            negative_prompt=NEGATIVE,
            image=canvas,
            strength=STRENGTH,
            guidance_scale=6.0,
            num_inference_steps=30,
        ).images[0]
        out.save(f"/kaggle/working/{asin}.png")
        print(f"done: {asin}")
    except Exception as e:
        print(f"FAILED {asin}: {e}")

print("batch complete")
