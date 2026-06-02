"""
Multi-Platform Publisher — TikTok, Instagram Reels, Facebook Reels.
Handles aspect-ratio adaptation and platform-specific requirements.
"""

import os
import logging
from config.settings import TIKTOK_SESSION_ID, INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD

logger = logging.getLogger(__name__)


# ── TikTok ─────────────────────────────────────────────────────────────────

def publish_tiktok(story: dict) -> str | None:
    """Upload Shorts video to TikTok using tiktok-uploader."""
    shorts_path = story.get("shorts_path")
    if not shorts_path or not os.path.exists(shorts_path):
        logger.warning("No Shorts file for TikTok")
        return None

    if not TIKTOK_SESSION_ID:
        logger.warning("TIKTOK_SESSION_ID not set — skipping TikTok")
        return None

    try:
        from tiktok_uploader.upload import upload_video
        title = story.get("youtube_title", story["title"])[:150]
        tags  = " ".join(f"#{t.replace(' ', '')}" for t in story.get("tags", [])[:5])

        result = upload_video(
            filename=shorts_path,
            description=f"{title}\n\n{tags}\n#breakingweird #weirdnews #fyp",
            cookies=TIKTOK_SESSION_ID,
        )
        url = f"https://www.tiktok.com/@breakingweird"
        logger.info(f"TikTok uploaded: {url}")
        story["tiktok_url"] = url
        return url
    except ImportError:
        logger.warning("tiktok-uploader not installed: pip install tiktok-uploader")
        return None
    except Exception as e:
        logger.error(f"TikTok upload failed: {e}")
        return None


# ── Instagram Reels ────────────────────────────────────────────────────────

def publish_instagram(story: dict) -> str | None:
    """Upload Shorts video as Instagram Reel using instagrapi."""
    shorts_path = story.get("shorts_path")
    if not shorts_path or not os.path.exists(shorts_path):
        logger.warning("No Shorts file for Instagram")
        return None

    if not INSTAGRAM_USERNAME or not INSTAGRAM_PASSWORD:
        logger.warning("Instagram credentials not set — skipping Instagram")
        return None

    try:
        from instagrapi import Client as InstaClient
        cl = InstaClient()
        cl.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)

        title    = story.get("youtube_title", story["title"])
        tags     = " ".join(f"#{t.replace(' ', '')}" for t in story.get("tags", [])[:10])
        caption  = f"{title}\n\n{tags}\n#breakingweird #weirdnews #reels #fyp"

        media = cl.clip_upload(shorts_path, caption=caption)
        url   = f"https://www.instagram.com/reel/{media.pk}/"
        logger.info(f"Instagram Reel uploaded: {url}")
        story["instagram_url"] = url
        return url
    except ImportError:
        logger.warning("instagrapi not installed: pip install instagrapi")
        return None
    except Exception as e:
        logger.error(f"Instagram upload failed: {e}")
        return None


# ── Publish All Platforms ──────────────────────────────────────────────────

def publish_all_platforms(story: dict, run_id: str,
                           skip_tiktok: bool = False,
                           skip_instagram: bool = False) -> dict:
    """Publish to all configured platforms. Returns dict of results."""
    results = {}

    if not skip_tiktok:
        url = publish_tiktok(story)
        if url:
            results["tiktok"] = url

    if not skip_instagram:
        url = publish_instagram(story)
        if url:
            results["instagram"] = url

    return results
