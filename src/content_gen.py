import json

import requests

from . import config, sheets

DISCLOSURE = "As an Amazon Associate I earn from qualifying purchases."

SYSTEM_PROMPT = """You are an expert affiliate marketer and copywriter for Pinterest, Facebook and Instagram.

Generate high-converting, SEO-friendly content for one product. Vary tone across outputs
(inspirational, problem-solving, lifestyle-focused, trendy). Never invent features.
Write naturally, like recommending to a friend. No emojis in the Pinterest fields.

Avoid starting titles with any of these recently used patterns:
{recent_titles}

Respond ONLY with valid JSON:
{{
  "pin_title": "Catchy Pinterest title, max 100 chars, strong keywords",
  "pin_desc": "Hook + benefits + lifestyle angle + call to action. Exactly 5 relevant hashtags. Max 780 chars.",
  "alt_text": "SEO-friendly image description mentioning color/material/function",
  "fb_text": "Facebook post text: conversational, 1-3 short paragraphs, ends with a call to action to the link. Emojis ok, sparingly.",
  "ig_caption": "Instagram caption: hook first line, benefits, CTA saying the link is in bio. 8-12 hashtags at the end.",
  "dominant_color": "#hexcolor of the product's dominant color"
}}"""


def _call_model(model: str, system: str, user: str):
    r = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {config.OPENROUTER_API_KEY}"},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 1.0,
            "max_tokens": 1200,
            "response_format": {"type": "json_object"},
        },
        timeout=120,
    )
    if r.status_code == 429:
        raise requests.HTTPError(f"429 rate-limited on {model}")
    r.raise_for_status()
    content = r.json()["choices"][0]["message"]["content"]
    content = content.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
    return json.loads(content)


def generate(product: dict, recent_titles=None):
    recent = recent_titles if recent_titles is not None else sheets.recent_pin_titles()
    system = SYSTEM_PROMPT.format(recent_titles="\n".join(f"- {t}" for t in recent) or "- (none yet)")
    user = (
        f"Product:\n"
        f"Title: {product['product_title']}\n"
        f"Price: {product.get('price', '')}\n"
        f"Rating: {product.get('rating', '')}\n"
        f"URL: {product['product_url']}"
    )

    last_exc = None
    result = None
    for model in config.OPENROUTER_MODELS:
        try:
            result = _call_model(model, system, user)
            break
        except (requests.RequestException, json.JSONDecodeError) as e:
            last_exc = e
            continue
    if result is None:
        raise last_exc or RuntimeError("No OPENROUTER_MODELS configured")

    for key in ("pin_title", "pin_desc", "alt_text", "fb_text", "ig_caption"):
        if not result.get(key):
            raise ValueError(f"LLM response missing '{key}'")
    result["pin_title"] = result["pin_title"][:100]
    # Amazon Associates requires disclosure in the content itself, not just the
    # profile bio - appended in code so it can never be dropped by the LLM.
    result["pin_desc"] = f"{result['pin_desc'][:780]}\n\n{DISCLOSURE}"[:800]
    result["fb_text"] = f"{result['fb_text']}\n\n{DISCLOSURE}"
    result["ig_caption"] = f"{result['ig_caption']}\n\n{DISCLOSURE}"
    return result


def fill_queue_content():
    """Generate copy for all queue rows that have product data but no content yet."""
    rows = sheets.queue_rows()
    recent = sheets.recent_pin_titles()
    done = 0
    for row in rows:
        if row.get("pin_title") or not row.get("product_title"):
            continue
        try:
            result = generate(row, recent_titles=recent)
        except Exception as e:
            sheets.log_error("content_gen", row.get("asin"), e)
            continue
        sheets.update_queue_cells(row["_row"], result)
        recent.append(result["pin_title"])
        done += 1
        print(f"Content generated for {row.get('asin')}")
    print(f"Generated content for {done} products")
    return done


if __name__ == "__main__":
    fill_queue_content()
