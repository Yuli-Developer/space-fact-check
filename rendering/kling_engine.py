"""
Kling AI Engine — image-to-video generation via aimlapi.com.
Converts each scene's still image into a 5-second cinematic video clip.

Requires: AIMLAPI_KEY in .env
Free tier: limited generations. Set USE_KLING=true to enable.
"""

import os
import time
import logging
import requests

logger = logging.getLogger(__name__)

AIMLAPI_KEY  = os.getenv("AIMLAPI_KEY", "")
USE_KLING    = os.getenv("USE_KLING", "false").lower() == "true"
KLING_MODEL  = "kling-video/v1/standard/image-to-video"
BASE_URL     = "https://api.aimlapi.com/v2"
VIDEO_DIR    = os.getenv("OUTPUT_DIR", "output")


def _upload_image_as_base64(image_path: str) -> str:
    """Convert local image to base64 data URI for Kling API."""
    import base64
    with open(image_path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    ext = os.path.splitext(image_path)[1].lstrip(".").lower()
    mime = "image/jpeg" if ext in ("jpg", "jpeg") else "image/png"
    return f"data:{mime};base64,{data}"


def generate_video_from_image(image_path: str, prompt: str,
                               scene_index: int, run_id: str) -> str | None:
    """
    Submit image to Kling, poll for completion, download video.
    Returns local mp4 path or None on failure.
    """
    if not AIMLAPI_KEY:
        logger.warning("AIMLAPI_KEY not set — skipping Kling generation")
        return None

    headers = {
        "Authorization": f"Bearer {AIMLAPI_KEY}",
        "Content-Type":  "application/json",
    }

    # Encode image
    image_data = _upload_image_as_base64(image_path)

    payload = {
        "model":           KLING_MODEL,
        "image_url":       image_data,
        "prompt":          prompt,
        "negative_prompt": "static, boring, blurry, low quality, shaky",
        "duration":        "5",
        "cfg_scale":       0.5,
    }

    logger.info(f"Kling: submitting scene {scene_index + 1}...")
    try:
        r = requests.post(f"{BASE_URL}/video/generations",
                          json=payload, headers=headers, timeout=30)
        r.raise_for_status()
        gen_id = r.json().get("id")
        if not gen_id:
            logger.warning(f"Kling: no generation id in response: {r.text[:200]}")
            return None
    except Exception as e:
        logger.warning(f"Kling submit failed: {e}")
        return None

    logger.info(f"Kling: generation {gen_id} queued, polling...")

    # Poll up to 5 minutes
    for attempt in range(60):
        time.sleep(5)
        try:
            r = requests.get(f"{BASE_URL}/video/generations",
                             params={"generation_id": gen_id},
                             headers=headers, timeout=15)
            r.raise_for_status()
            data   = r.json()
            status = data.get("status", "")

            if status == "completed":
                video_url = data.get("video", {}).get("url")
                if not video_url:
                    logger.warning("Kling: completed but no video URL")
                    return None

                # Download video
                out_dir  = os.path.join(VIDEO_DIR, "kling")
                os.makedirs(out_dir, exist_ok=True)
                out_path = os.path.join(out_dir, f"{run_id}_scene_{scene_index + 1:02d}.mp4")
                vr = requests.get(video_url, timeout=120, stream=True)
                vr.raise_for_status()
                with open(out_path, "wb") as f:
                    for chunk in vr.iter_content(65536):
                        f.write(chunk)

                size = os.path.getsize(out_path)
                logger.info(f"Kling scene {scene_index + 1}: downloaded {size // 1024}KB → {out_path}")
                return out_path

            elif status == "error":
                logger.warning(f"Kling generation error: {data}")
                return None
            else:
                logger.debug(f"Kling poll {attempt + 1}/60: {status}")

        except Exception as e:
            logger.warning(f"Kling poll error: {e}")

    logger.warning(f"Kling: timeout after 5 minutes for scene {scene_index + 1}")
    return None


def generate_all_kling_videos(story: dict, run_id: str) -> dict:
    """
    Generate Kling video clips for all scenes.
    Returns dict mapping scene index (str) → local mp4 path.
    Skips scenes that fail — they fall back to animated portrait.
    """
    if not USE_KLING:
        logger.info("Kling disabled (USE_KLING=false) — using animated portraits")
        return {}

    image_paths = story.get("image_paths", [])
    scenes      = story.get("shorts_scenes", story.get("scenes", []))
    kling_paths = {}

    for i, scene in enumerate(scenes):
        idx = scene.get("scene_number", i + 1) - 1
        if idx >= len(image_paths) or not os.path.exists(image_paths[idx]):
            logger.warning(f"Kling: no image for scene {i + 1}, skipping")
            continue

        # Build a motion prompt from the scene description
        desc    = scene.get("storyboard_description", scene.get("narration_segment", ""))
        prompt  = (
            f"Cinematic breaking news broadcast, {desc}, "
            "dramatic camera movement, photorealistic, high detail, "
            "Bloomberg/CNBC news style, professional lighting"
        )

        path = generate_video_from_image(image_paths[idx], prompt, i, run_id)
        if path:
            kling_paths[str(idx)] = path

    logger.info(f"Kling: generated {len(kling_paths)}/{len(scenes)} scene videos")
    story["kling_video_paths"] = kling_paths
    return kling_paths
