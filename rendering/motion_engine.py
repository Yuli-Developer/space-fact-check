"""
Motion Engine — cinematic effects applied to still images.
Supports: Ken Burns, parallax, camera shake, manga speed lines,
rain/fire overlays, particles, zoom burst.
"""

import math
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from moviepy import VideoClip
from config.settings import VIDEO_WIDTH as W, VIDEO_HEIGHT as H, FPS


# ── Ken Burns ──────────────────────────────────────────────────────────────

def ken_burns_clip(image_path: str, duration: float,
                   effect: str = None) -> VideoClip:
    """Zoom/pan a still image for cinematic motion."""
    img = Image.open(image_path).convert("RGB").resize((W, H), Image.LANCZOS)
    arr = np.array(img)
    effect = effect or random.choice(["zoom_in", "zoom_out", "pan_right", "pan_left"])

    def make_frame(t):
        progress = t / max(duration, 0.001)
        scale = {
            "zoom_in":   1.0 + 0.12 * progress,
            "zoom_out":  1.12 - 0.12 * progress,
            "pan_right": 1.08,
            "pan_left":  1.08,
        }[effect]

        cw, ch = int(W / scale), int(H / scale)

        if effect == "pan_right":
            ox = int((W - cw) * progress)
            oy = (H - ch) // 2
        elif effect == "pan_left":
            ox = int((W - cw) * (1 - progress))
            oy = (H - ch) // 2
        else:
            ox = (W - cw) // 2
            oy = (H - ch) // 2

        ox = max(0, min(ox, W - cw))
        oy = max(0, min(oy, H - ch))
        cropped = arr[oy:oy + ch, ox:ox + cw]
        return np.array(Image.fromarray(cropped).resize((W, H), Image.LANCZOS))

    return VideoClip(make_frame, duration=duration).with_fps(FPS)


# ── Parallax ───────────────────────────────────────────────────────────────

def parallax_clip(image_path: str, duration: float,
                  layers: int = 3) -> VideoClip:
    """
    Simulates parallax by splitting image into horizontal bands
    that move at different speeds — creates depth illusion.
    """
    img   = Image.open(image_path).convert("RGB").resize((W, H), Image.LANCZOS)
    arr   = np.array(img)
    bands = np.array_split(arr, layers, axis=0)
    speeds = [0.04 * (i + 1) for i in range(layers)]   # pixels per second

    def make_frame(t):
        canvas = arr.copy()
        y = 0
        for band, speed in zip(bands, speeds):
            bh = band.shape[0]
            shift = int(t * speed * FPS) % W
            shifted = np.roll(band, shift, axis=1)
            canvas[y:y + bh] = shifted
            y += bh
        return canvas

    return VideoClip(make_frame, duration=duration).with_fps(FPS)


# ── Camera Shake ───────────────────────────────────────────────────────────

def add_camera_shake(clip: VideoClip, intensity: int = 4) -> VideoClip:
    """Add subtle random camera shake to a clip."""
    duration = clip.duration

    def make_frame(t):
        frame = clip.get_frame(t)
        img   = Image.fromarray(frame)
        dx    = random.randint(-intensity, intensity)
        dy    = random.randint(-intensity, intensity)
        img   = img.transform(
            (W, H), Image.AFFINE,
            (1, 0, dx, 0, 1, dy),
            fillcolor=(0, 0, 0),
        )
        return np.array(img)

    return VideoClip(make_frame, duration=duration).with_fps(FPS)


# ── Speed Lines Overlay ────────────────────────────────────────────────────

def speed_lines_frame(frame: np.ndarray, cx: int = None,
                       cy: int = None, intensity: float = 1.0) -> np.ndarray:
    """Draw radial speed lines on a single frame (manga action effect)."""
    cx = cx or W // 2
    cy = cy or H // 3
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw    = ImageDraw.Draw(overlay)

    n_lines = int(60 * intensity)
    for i in range(n_lines):
        angle  = (2 * math.pi * i) / n_lines + random.uniform(-0.03, 0.03)
        length = random.randint(300, 900)
        gap    = random.randint(10, 30)
        x0 = cx + gap * math.cos(angle)
        y0 = cy + gap * math.sin(angle)
        x1 = cx + length * math.cos(angle)
        y1 = cy + length * math.sin(angle)
        alpha = random.randint(40, 100)
        width = random.choice([1, 1, 2])
        draw.line([(x0, y0), (x1, y1)], fill=(255, 255, 255, alpha), width=width)

    base = Image.fromarray(frame).convert("RGBA")
    comp = Image.alpha_composite(base, overlay)
    return np.array(comp.convert("RGB"))


# ── Rain Overlay ───────────────────────────────────────────────────────────

def rain_frame(frame: np.ndarray, t: float, density: int = 200) -> np.ndarray:
    """Add animated rain streaks to a frame."""
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw    = ImageDraw.Draw(overlay)
    rng     = random.Random(int(t * 30))

    for _ in range(density):
        x   = rng.randint(0, W)
        y   = (rng.randint(0, H) + int(t * 800)) % H
        length = rng.randint(15, 40)
        alpha  = rng.randint(60, 130)
        draw.line([(x, y), (x - 3, y + length)],
                  fill=(180, 200, 255, alpha), width=1)

    base = Image.fromarray(frame).convert("RGBA")
    return np.array(Image.alpha_composite(base, overlay).convert("RGB"))


# ── Particle Overlay ───────────────────────────────────────────────────────

def particles_frame(frame: np.ndarray, t: float,
                     count: int = 40, color=(255, 220, 50)) -> np.ndarray:
    """Floating particle effect (embers / dust)."""
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw    = ImageDraw.Draw(overlay)
    rng     = random.Random(42)

    for _ in range(count):
        x    = rng.randint(0, W)
        base_y = rng.randint(0, H)
        y    = (base_y - int(t * rng.randint(30, 100))) % H
        r    = rng.randint(2, 5)
        alpha = rng.randint(100, 200)
        draw.ellipse([x - r, y - r, x + r, y + r],
                     fill=(*color, alpha))

    base = Image.fromarray(frame).convert("RGBA")
    return np.array(Image.alpha_composite(base, overlay).convert("RGB"))


# ── Manga Transition Flash ─────────────────────────────────────────────────

def flash_transition(duration: float = 0.15) -> VideoClip:
    """White flash frame for manga-style scene cuts."""
    white = np.full((H, W, 3), 255, dtype=np.uint8)
    return VideoClip(lambda t: white, duration=duration).with_fps(FPS)


# ── Zoom Burst ─────────────────────────────────────────────────────────────

def zoom_burst_clip(image_path: str, duration: float) -> VideoClip:
    """Fast zoom into image center — high energy manga impact."""
    img = Image.open(image_path).convert("RGB").resize((W, H), Image.LANCZOS)
    arr = np.array(img)

    def make_frame(t):
        progress = (t / duration) ** 1.5    # accelerating zoom
        scale    = 1.0 + 0.5 * progress
        cw, ch   = int(W / scale), int(H / scale)
        ox, oy   = (W - cw) // 2, (H - ch) // 2
        ox = max(0, min(ox, W - cw))
        oy = max(0, min(oy, H - ch))
        cropped  = arr[oy:oy + ch, ox:ox + cw]
        return np.array(Image.fromarray(cropped).resize((W, H), Image.LANCZOS))

    return VideoClip(make_frame, duration=duration).with_fps(FPS)


# ── Glitch Effect ──────────────────────────────────────────────────────────

def glitch_frame(frame: np.ndarray, t: float, intensity: float = 1.0) -> np.ndarray:
    """TV signal glitch — horizontal slice shifts and RGB channel split."""
    img = frame.copy()
    rng = random.Random(int(t * 60))

    # Horizontal slice shifts
    n_slices = rng.randint(2, 6)
    for _ in range(n_slices):
        y0 = rng.randint(0, img.shape[0] - 20)
        h  = rng.randint(4, 20)
        shift = rng.randint(-30, 30)
        slice_ = img[y0:y0 + h].copy()
        img[y0:y0 + h] = np.roll(slice_, shift, axis=1)

    # RGB channel offset
    shift_r = int(rng.uniform(-6, 6) * intensity)
    shift_b = int(rng.uniform(-6, 6) * intensity)
    if shift_r:
        img[:, :, 0] = np.roll(img[:, :, 0], shift_r, axis=1)
    if shift_b:
        img[:, :, 2] = np.roll(img[:, :, 2], shift_b, axis=1)

    return img


def glitch_clip(image_path: str, duration: float,
                canvas_w: int = None, canvas_h: int = None) -> VideoClip:
    """Apply glitch effect throughout a clip."""
    cw = canvas_w or W
    ch = canvas_h or H
    img = Image.open(image_path).convert("RGB").resize((cw, ch), Image.LANCZOS)
    arr = np.array(img)

    def make_frame(t):
        # Glitch fires in short bursts
        beat = 1.5
        phase = (t % beat) / beat
        if phase < 0.12:
            return glitch_frame(arr, t, intensity=1.5)
        return arr

    return VideoClip(make_frame, duration=duration).with_fps(FPS)


# ── Red Alert Flash Overlay ─────────────────────────────────────────────────

def red_alert_overlay(frame: np.ndarray, t: float,
                      canvas_w: int = None, canvas_h: int = None) -> np.ndarray:
    """Pulsing red border — breaking news alert effect."""
    cw = canvas_w or W
    ch = canvas_h or H
    pulse = abs(math.sin(math.pi * t * 2.5))  # 2.5 Hz pulse
    if pulse < 0.3:
        return frame

    overlay = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    draw    = ImageDraw.Draw(overlay)
    border  = 18
    alpha   = int(180 * pulse)
    draw.rectangle([0, 0, cw - 1, ch - 1], outline=(220, 0, 0, alpha), width=border)
    base = Image.fromarray(frame).convert("RGBA")
    return np.array(Image.alpha_composite(base, overlay).convert("RGB"))


# ── Scanline Overlay ────────────────────────────────────────────────────────

def scanline_overlay(frame: np.ndarray,
                     canvas_w: int = None, canvas_h: int = None) -> np.ndarray:
    """Horizontal TV scanlines — fake broadcast aesthetic."""
    ch = canvas_h or frame.shape[0]
    cw = canvas_w or frame.shape[1]
    result = frame.copy()
    result[::3] = (result[::3] * 0.72).astype(np.uint8)   # darken every 3rd row
    return result


# ── Breaking News Ticker Bar ────────────────────────────────────────────────

def ticker_bar(frame: np.ndarray, t: float, headline: str,
               canvas_w: int = None, canvas_h: int = None) -> np.ndarray:
    """Scrolling red ticker bar at bottom of frame."""
    cw = canvas_w or W
    ch = canvas_h or H
    overlay = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    draw    = ImageDraw.Draw(overlay)

    bar_h   = max(40, ch // 22)
    bar_y   = ch - bar_h - 2
    draw.rectangle([0, bar_y, cw, ch - 2], fill=(200, 0, 0, 220))

    text    = f"BREAKING: {headline.upper()}  •  BREAKING: {headline.upper()}  •  "
    speed   = cw * 0.08   # pixels per second
    x_off   = int((-t * speed) % (cw * 2))

    try:
        from PIL import ImageFont
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", bar_h - 10)
    except Exception:
        from PIL import ImageFont
        font = ImageFont.load_default()

    draw.text((cw - x_off, bar_y + bar_h // 2), text,
              font=font, fill=(255, 255, 255, 255), anchor="lm")

    base = Image.fromarray(frame).convert("RGBA")
    return np.array(Image.alpha_composite(base, overlay).convert("RGB"))


# ── Animated Portrait Clip (Shorts) ────────────────────────────────────────

SHORTS_EFFECTS = ["zoom_in", "zoom_out", "pan_right", "pan_left", "zoom_burst", "parallax"]


def make_animated_portrait(image_path: str, duration: float,
                            scene_index: int = 0,
                            headline: str = "",
                            canvas_w: int = 1080, canvas_h: int = 1920) -> VideoClip:
    """
    Full cinematic portrait clip for Shorts:
      - Motion effect (cycles per scene)
      - Camera shake on odd scenes
      - Scanline overlay (always)
      - Red alert pulse (always)
      - Ticker bar (when headline provided)
    """
    effect = SHORTS_EFFECTS[scene_index % len(SHORTS_EFFECTS)]

    # Base motion clip
    if effect == "zoom_burst":
        img = Image.open(image_path).convert("RGB").resize((canvas_w, canvas_h), Image.LANCZOS)
        arr = np.array(img)

        def zoom_frame(t):
            progress = (t / max(duration, 0.001)) ** 1.5
            scale = 1.0 + 0.4 * progress
            cw2, ch2 = int(canvas_w / scale), int(canvas_h / scale)
            ox = (canvas_w - cw2) // 2
            oy = (canvas_h - ch2) // 2
            cropped = arr[oy:oy + ch2, ox:ox + cw2]
            return np.array(Image.fromarray(cropped).resize((canvas_w, canvas_h), Image.LANCZOS))

        base_clip = VideoClip(zoom_frame, duration=duration).with_fps(FPS)

    elif effect == "parallax":
        base_clip = parallax_clip(image_path, duration, layers=3)
        # parallax_clip uses W/H — override with portrait size via simple resize
        img = Image.open(image_path).convert("RGB").resize((canvas_w, canvas_h), Image.LANCZOS)
        arr = np.array(img)
        bands = [arr[i * (canvas_h // 3):(i + 1) * (canvas_h // 3)] for i in range(3)]
        speeds = [0.03 * (i + 1) for i in range(3)]

        def par_frame(t):
            canvas = arr.copy()
            for i, (band, speed) in enumerate(zip(bands, speeds)):
                bh = band.shape[0]
                shift = int(t * speed * canvas_w) % canvas_w
                shifted = np.roll(band, shift, axis=1)
                y0 = i * bh
                canvas[y0:y0 + bh] = shifted
            return canvas

        base_clip = VideoClip(par_frame, duration=duration).with_fps(FPS)

    else:
        # Ken Burns on portrait canvas
        img = Image.open(image_path).convert("RGB").resize((canvas_w, canvas_h), Image.LANCZOS)
        arr = np.array(img)

        def kb_frame(t):
            progress = t / max(duration, 0.001)
            scale = {
                "zoom_in":   1.0 + 0.10 * progress,
                "zoom_out":  1.10 - 0.10 * progress,
                "pan_right": 1.08,
                "pan_left":  1.08,
            }[effect]
            cw2 = int(canvas_w / scale)
            ch2 = int(canvas_h / scale)
            if effect == "pan_right":
                ox = int((canvas_w - cw2) * progress)
                oy = (canvas_h - ch2) // 2
            elif effect == "pan_left":
                ox = int((canvas_w - cw2) * (1 - progress))
                oy = (canvas_h - ch2) // 2
            else:
                ox = (canvas_w - cw2) // 2
                oy = (canvas_h - ch2) // 2
            ox = max(0, min(ox, canvas_w - cw2))
            oy = max(0, min(oy, canvas_h - ch2))
            cropped = arr[oy:oy + ch2, ox:ox + cw2]
            return np.array(Image.fromarray(cropped).resize((canvas_w, canvas_h), Image.LANCZOS))

        base_clip = VideoClip(kb_frame, duration=duration).with_fps(FPS)

    # Compose overlays
    shake = (scene_index % 2 == 1)   # camera shake on odd scenes

    def compose_frame(gf, t):
        frame = gf(t)
        if shake:
            dx = random.randint(-3, 3)
            dy = random.randint(-2, 2)
            pil = Image.fromarray(frame)
            pil = pil.transform((canvas_w, canvas_h), Image.AFFINE,
                                 (1, 0, dx, 0, 1, dy), fillcolor=(0, 0, 0))
            frame = np.array(pil)
        frame = scanline_overlay(frame, canvas_w, canvas_h)
        frame = red_alert_overlay(frame, t, canvas_w, canvas_h)
        if headline:
            frame = ticker_bar(frame, t, headline, canvas_w, canvas_h)
        return frame

    return base_clip.transform(compose_frame)


# ── Apply motion by name ────────────────────────────────────────────────────

def apply_motion(image_path: str, duration: float, effect: str) -> VideoClip:
    """Route to the correct motion effect by name."""
    if effect == "zoom_burst":
        return zoom_burst_clip(image_path, duration)
    elif effect == "parallax":
        return parallax_clip(image_path, duration)
    elif effect in ("ken_burns_zoom_in", "ken_burns_zoom_out", "pan_left", "pan_right"):
        eff = effect.replace("ken_burns_", "")
        return ken_burns_clip(image_path, duration, effect=eff)
    else:
        return ken_burns_clip(image_path, duration)
