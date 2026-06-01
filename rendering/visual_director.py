"""
Visual Director — Space Fact Check.
Tier 1: Imagen 3 via Google AI (same API key as Gemini — no extra cost)
Tier 2: Pollinations fallback
Tier 3: Gradient fallback
"""
import os
import time
import base64
import logging
import urllib.parse
import requests
from config.settings import IMAGES_DIR, GEMINI_API_KEY, IMAGE_TIER

logger = logging.getLogger(__name__)

# ── Space visual prompts ──────────────────────────────────────────────────

COSMIC_BASE = (
    "ultra photorealistic space photography, NASA hubble james webb telescope aesthetic, "
    "deep field cosmic imagery, dramatic nebula colors, infinite depth of field, "
    "cinematic space documentary, 8k UHD, volumetric light rays through gas clouds, "
    "award-winning astrophotography, BBC cosmos documentary production quality, "
    "dark void of space with brilliant star clusters, "
    "scientifically accurate astronomical imagery"
)

COSMIC_NEGATIVE = (
    "cartoon, anime, illustration, painting, flat design, low quality, blurry, "
    "human face, person, people, astronaut visible, alien creature, monster, "
    "fake, CGI obvious, plastic, toy, watermark, logo, text errors, "
    "cheerful bright colors, overly saturated rainbow, cheap render"
)

SCENE_MOODS = [
    # Scene 1 — the viral claim (dramatic, mysterious)
    "mysterious ominous cosmic phenomenon, deep purple and red nebula, unknown signal source, "
    "sense of mystery and discovery, dramatic chiaroscuro lighting",
    # Scene 2 — the reality (scientific, precise)
    "precise scientific astronomical data, cool blue telescope imagery, star charts overlaid, "
    "mission control aesthetic, data-driven clinical precision, scientific truth",
    # Scene 3 — scale (awe-inspiring)
    "incomprehensible cosmic scale, galaxy clusters stretching to infinity, "
    "pale blue dot perspective, humbling enormity of the universe, deep awe",
    # Scene 4 — the verdict (mind-blowing)
    "stunning revelation visual, the most beautiful real space image ever captured, "
    "reality more magnificent than fiction, jaw-dropping cosmic truth",
    # Scene 5 — ancient light (deep time)
    "ancient light from 13 billion years ago, primordial cosmic dawn, first stars igniting, "
    "deep time visual metaphor, red-shifted early universe glow, origin of everything",
    # Scene 6 — violent stellar event
    "violent stellar explosion, supernova shockwave expanding outward, catastrophic cosmic scale, "
    "brilliant white core surrounded by expanding plasma rings, elemental birth from destruction",
    # Scene 7 — alien world
    "exotic exoplanet surface, alien sky with multiple moons, otherworldly terrain and rock formations, "
    "harsh alien atmosphere, distant star casting strange colored light, eerie desolate beauty",
    # Scene 8 — black hole
    "black hole event horizon with gravitational lensing, extreme space curvature visible, "
    "accretion disk glowing orange and white, point of no return, bending light dramatically",
    # Scene 9 — comet / solar system
    "comet tail of ice and rock trailing across dark void, solar wind pushing debris, "
    "brilliant icy nucleus with twin tails, solar system history frozen in ice",
    # Scene 10 — solar flare / star surface
    "solar flare eruption from star surface, massive plasma arc rising thousands of kilometers, "
    "magnetic field lines glowing, stellar surface texture visible, raw star energy unleashed",
]

COMPOSITIONS = [
    "VERTICAL 9:16 portrait, tall narrow frame, cosmic subject centered, "
    "optimized for mobile full screen, dramatic vertical composition",
]


def _build_space_prompt(scene: dict, portrait: bool = True) -> str:
    scene_num = scene.get("scene_number", 1)
    desc = scene.get("storyboard_description", scene.get("narration_segment", ""))
    mood = SCENE_MOODS[(scene_num - 1) % len(SCENE_MOODS)]
    comp = COMPOSITIONS[0] if portrait else ""

    return (
        f"{COSMIC_BASE}, "
        f"{comp}, "
        f"scene depicting: {desc}, "
        f"mood: {mood}, "
        f"NO human figures, NO text overlays, NO logos, "
        f"photorealistic deep space environment only"
    )


# ── Tier 1: Imagen 3 ──────────────────────────────────────────────────────

def _imagen3_generate(prompt: str, path: str) -> bool:
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_images(
            model="imagen-4.0-fast-generate-001",
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="9:16",
                person_generation="dont_allow",
            ),
        )
        for generated_image in response.generated_images:
            image_bytes = generated_image.image.image_bytes
            with open(path, "wb") as f:
                f.write(image_bytes)
            logger.info(f"Imagen 3: saved {path}")
            return True
        return False
    except Exception as e:
        logger.warning(f"Imagen 3 failed: {e}")
        return False


# ── Tier 2: Pollinations fallback ─────────────────────────────────────────

def _pollinations_generate(prompt: str, path: str, seed: int) -> bool:
    encoded = urllib.parse.quote(prompt)
    neg     = urllib.parse.quote(COSMIC_NEGATIVE)
    url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width=1080&height=1920&nologo=true&model=flux&seed={seed}&negative={neg}"
    )
    for attempt in range(3):
        try:
            r = requests.get(url, timeout=120)
            r.raise_for_status()
            if len(r.content) < 5000:
                raise ValueError(f"Too small: {len(r.content)} bytes")
            with open(path, "wb") as f:
                f.write(r.content)
            return True
        except Exception as e:
            wait = [30, 60, 90][attempt]
            logger.warning(f"Pollinations attempt {attempt+1}/3: {e} — waiting {wait}s")
            if attempt < 2:
                time.sleep(wait)
    return False


# ── Tier 3: Gradient fallback ─────────────────────────────────────────────

def _gradient_fallback(path: str, scene_num: int):
    from PIL import Image, ImageDraw
    colors = [(5, 5, 20), (10, 5, 30), (5, 10, 25), (8, 3, 22)]
    bg = colors[(scene_num - 1) % len(colors)]
    img = Image.new("RGB", (1080, 1920), bg)
    draw = ImageDraw.Draw(img)
    # Simple star field
    import random
    rng = random.Random(scene_num * 42)
    for _ in range(300):
        x = rng.randint(0, 1080)
        y = rng.randint(0, 1920)
        r = rng.choice([1, 1, 1, 2])
        brightness = rng.randint(150, 255)
        draw.ellipse([x-r, y-r, x+r, y+r], fill=(brightness, brightness, brightness))
    img.save(path)
    logger.warning(f"Used starfield fallback for scene {scene_num}")


# ── Public API ─────────────────────────────────────────────────────────────

def generate_scene_image(scene: dict, run_id: str) -> str:
    os.makedirs(IMAGES_DIR, exist_ok=True)
    scene_num = scene["scene_number"]
    path = os.path.join(IMAGES_DIR, f"{run_id}_scene_{scene_num:02d}.png")

    prompt = _build_space_prompt(scene, portrait=True)
    seed   = scene_num * 137

    logger.info(f"Scene {scene_num}: generating space image")

    success = False

    if IMAGE_TIER == "imagen3":
        success = _imagen3_generate(prompt, path)

    if not success:
        success = _pollinations_generate(prompt, path, seed)

    if not success:
        _gradient_fallback(path, scene_num)

    return path


def generate_all_images(story: dict, run_id: str, **kwargs) -> list[str]:
    image_paths = []
    for scene in story["scenes"]:
        path = generate_scene_image(scene, run_id)
        image_paths.append(path)
        time.sleep(3)   # brief pause between Imagen 3 calls

    story["image_paths"] = image_paths
    logger.info(f"Generated {len(image_paths)} images")
    return image_paths
