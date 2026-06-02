"""
Thumbnail Engine — Space Fact Check.
Dark cosmic theme with CLAIM vs REALITY contrast.
"""
import os
import re
import math
import random
import logging
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from config.settings import THUMB_DIR
from storage.database import save_thumbnail_scores

logger = logging.getLogger(__name__)

W, H = 1280, 720

THEMES = [
    {"bg": "#000008", "accent": "#003399", "text": "#00E5FF"},   # deep blue / cyan
    {"bg": "#050005", "accent": "#6600CC", "text": "#FFFFFF"},   # dark purple / white
    {"bg": "#000805", "accent": "#006633", "text": "#00FF88"},   # dark green / mint
    {"bg": "#080000", "accent": "#CC2200", "text": "#FFFFFF"},   # dark red / white (WRONG claim)
]


def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in [
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _hex_rgb(h: str) -> tuple:
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _wrap(text: str, font, max_w: int, draw) -> list[str]:
    words, lines, line = text.split(), [], []
    for word in words:
        test = " ".join(line + [word])
        if draw.textbbox((0, 0), test, font=font)[2] <= max_w:
            line.append(word)
        else:
            if line:
                lines.append(" ".join(line))
            line = [word]
    if line:
        lines.append(" ".join(line))
    return lines[:3]


def _outlined_text(draw, pos, text, font, fill, outline, stroke=10, anchor="lt"):
    x, y = pos
    for dx in range(-stroke, stroke + 1):
        for dy in range(-stroke, stroke + 1):
            if dx*dx + dy*dy <= stroke*stroke:
                draw.text((x+dx, y+dy), text, font=font, fill=outline, anchor=anchor)
    draw.text(pos, text, font=font, fill=fill, anchor=anchor)


def _star_field(draw, n: int = 200, seed: int = 1):
    rng = random.Random(seed)
    for _ in range(n):
        x = rng.randint(0, W)
        y = rng.randint(0, H)
        r = rng.choice([1, 1, 1, 2])
        b = rng.randint(120, 255)
        draw.ellipse([x-r, y-r, x+r, y+r], fill=(b, b, b))


def _render_thumbnail(image_paths: list, title_text: str,
                       subtitle_text: str, theme: dict,
                       variant: int, run_id: str) -> str:
    os.makedirs(THUMB_DIR, exist_ok=True)
    path = os.path.join(THUMB_DIR, f"{run_id}_thumb_v{variant}.jpg")

    preferred = [3, 1, 4, 0, 2]
    bg_img    = None
    for idx in preferred:
        if idx < len(image_paths) and os.path.exists(image_paths[idx]):
            bg_img = Image.open(image_paths[idx]).convert("RGB")
            break

    if bg_img is None:
        bg_img = Image.new("RGB", (W, H), theme["bg"])
        draw_bg = ImageDraw.Draw(bg_img)
        _star_field(draw_bg, n=300, seed=variant)
    else:
        iw, ih = bg_img.size
        ratio  = W / H
        if iw / ih > ratio:
            new_w = int(ih * ratio)
            bg_img = bg_img.crop(((iw - new_w) // 2, 0, (iw - new_w) // 2 + new_w, ih))
        bg_img = bg_img.resize((W, H), Image.LANCZOS)
        bg_img = ImageEnhance.Contrast(bg_img).enhance(1.5)
        bg_img = ImageEnhance.Brightness(bg_img).enhance(0.7)

    # Dark gradient overlay
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for row in range(int(H * 0.35), H):
        alpha = int(220 * (row - H * 0.35) / (H * 0.65))
        od.rectangle([0, row, W, row+1], fill=(0, 0, 10, alpha))
    bg_img = Image.alpha_composite(bg_img.convert("RGBA"), overlay).convert("RGB")
    draw   = ImageDraw.Draw(bg_img)

    # Left edge bar
    draw.rectangle([0, 0, 10, H], fill=theme["accent"])

    # Channel badge
    draw.rectangle([18, 18, 280, 58], fill=theme["accent"])
    draw.text((149, 38), "SPACE FACT CHECK", font=_font(24), fill="white", anchor="mm")

    # FACT CHECK stamp (variant 1 and 3 show CLAIM badge)
    stamp_text  = "FACT CHECK" if variant % 2 == 0 else "DEBUNKED"
    stamp_color = "#003399" if variant % 2 == 0 else "#CC0000"
    cx, cy, r = W - 65, 65, 55
    draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=stamp_color)
    draw.ellipse([cx-r+3, cy-r+3, cx+r-3, cy+r-3], outline="#FFFFFF", width=3)
    draw.text((cx, cy - 8), stamp_text[:4], font=_font(22), fill="white", anchor="mm")
    draw.text((cx, cy + 12), stamp_text[4:], font=_font(22), fill="white", anchor="mm")

    # Main title
    tf    = _font(96)
    pad   = 20
    lines = _wrap(title_text.upper(), tf, W - pad*2 - 80, draw)
    lh    = 108
    total = len(lines) * lh
    y     = H - total - 55

    backing = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(backing)
    bd.rectangle([0, y - 8, W, y + total + 8], fill=(0, 0, 10, 190))
    bg_img = Image.alpha_composite(bg_img.convert("RGBA"), backing).convert("RGB")
    draw   = ImageDraw.Draw(bg_img)

    accent_rgb = _hex_rgb(theme["accent"])
    for i, line in enumerate(lines):
        _outlined_text(draw, (pad, y), line, tf,
                        fill=theme["text"], outline="#000010", stroke=11, anchor="lt")
        bbox = draw.textbbox((pad, y), line, font=tf, anchor="lt")
        draw.rectangle([pad, bbox[3]+2, bbox[2], bbox[3]+7], fill=theme["accent"])
        y += lh

    if subtitle_text:
        draw.text((pad, H - 48), subtitle_text, font=_font(36), fill="#AACCFF", anchor="lt")

    # Bottom bar
    draw.rectangle([0, H - 44, W, H], fill=theme["accent"])
    draw.text((W//2, H - 22), "SUBSCRIBE  •  DAILY FACT CHECKS  •  SPACE FACT CHECK",
              font=_font(22), fill="white", anchor="mm")

    bg_img.save(path, "JPEG", quality=95)
    return path


_CTR_KEYWORDS = [
    "wrong", "false", "myth", "actually", "truth", "real", "proof",
    "nasa", "alien", "discovered", "secret", "revealed", "shocking",
    "never told", "they lied", "real story", "what they", "the truth",
]

_EMOTION_KEYWORDS = {
    "shock":     ["wrong", "false", "debunked", "actually", "shocking", "impossible"],
    "curiosity": ["truth", "real story", "what really", "secret", "hidden", "why"],
    "wonder":    ["discovered", "nasa", "universe", "space", "cosmos", "mind blowing"],
    "trust":     ["fact check", "science", "scientists", "study", "research", "proof"],
}

_THEME_BOOST = [0.8, 0.5, 0.6, 0.7]


def _score_title(title: str) -> dict:
    title_lower = title.lower()
    ctr_hits  = sum(1 for kw in _CTR_KEYWORDS if kw in title_lower)
    has_num   = bool(re.search(r'\d', title))
    length_ok = 4 <= len(title.split()) <= 8
    ctr_score = min(10.0, 6.0 + ctr_hits * 0.8 + (0.8 if has_num else 0) + (0.5 if length_ok else 0))

    emotion_scores = {e: sum(1 for k in kws if k in title_lower)
                      for e, kws in _EMOTION_KEYWORDS.items()}
    top_val       = max(emotion_scores.values())
    emotion_score = min(10.0, 7.0 + top_val * 0.8)

    words        = len(title.split())
    readability  = 10.0 if words <= 5 else (8.5 if words <= 7 else 7.0)
    upper_ratio  = sum(1 for w in title.split() if w.isupper()) / max(len(title.split()), 1)
    mobile_score = min(10.0, 7.5 + upper_ratio * 2.0)

    total = (ctr_score * 0.40 + emotion_score * 0.30 +
             readability * 0.15 + mobile_score * 0.15)

    return {
        "ctr_score":    round(ctr_score, 1),
        "emotion_score": round(emotion_score, 1),
        "readability":  round(readability, 1),
        "mobile_score": round(mobile_score, 1),
        "total_score":  round(total, 1),
    }


def generate_thumbnails(story: dict, run_id: str) -> tuple[str, list[dict]]:
    image_paths    = story.get("image_paths", [])
    title_variants = story.get("title_variants",
                                [story.get("youtube_title", story["title"])] * 4)
    while len(title_variants) < 4:
        title_variants.append(title_variants[0])

    thumbnails_meta = []

    for variant in range(4):
        theme    = THEMES[variant]
        title    = title_variants[variant]
        subtitle = story.get("reality_statement", "")[:40] if variant % 2 == 1 else ""
        path     = _render_thumbnail(image_paths, title, subtitle,
                                      theme, variant + 1, run_id)
        thumbnails_meta.append({
            "variant": variant + 1,
            "path":    path,
            "title":   title,
            "selected": 0,
        })
        logger.info(f"Thumbnail v{variant+1} rendered: {path}")

    # Score
    for i, t in enumerate(thumbnails_meta):
        scores = _score_title(t.get("title", story.get("youtube_title", "")))
        scores["total_score"] = round(min(10.0, scores["total_score"] + _THEME_BOOST[i]), 1)
        t.update(scores)

    best = max(thumbnails_meta, key=lambda x: x.get("total_score", 0))
    best["selected"] = 1
    logger.info(f"Best thumbnail: v{best['variant']} (score={best.get('total_score', 0):.1f})")

    save_thumbnail_scores(run_id, thumbnails_meta)
    story["thumbnail_path"] = best["path"]
    story["all_thumbnails"] = thumbnails_meta
    return best["path"], thumbnails_meta
