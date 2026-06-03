"""Space Fact Check channel configuration."""
import os
from dotenv import load_dotenv
load_dotenv()

GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL    = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_PRO_MODEL = "gemini-2.5-pro"      # used for script generation only
GEMINI_TTS_MODEL = "gemini-2.5-flash-preview-tts"

YOUTUBE_CLIENT_SECRETS = os.getenv("YOUTUBE_CLIENT_SECRETS", "client_secrets.json")
YOUTUBE_TOKEN_PATH     = os.getenv("YOUTUBE_TOKEN_PATH", "token_space.pickle")
YOUTUBE_CHANNEL_ID     = os.getenv("YOUTUBE_CHANNEL_ID", "")

TIKTOK_SESSION_ID  = os.getenv("TIKTOK_SESSION_ID", "")
INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME", "")
INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD", "")

IMAGE_TIER   = os.getenv("IMAGE_TIER", "imagen3")   # imagen3 | pollinations
AIMLAPI_KEY  = os.getenv("AIMLAPI_KEY", "")
USE_KLING    = False
USE_COMFYUI  = False
COMFYUI_URL  = os.getenv("COMFYUI_URL", "http://localhost:8188")

STORIES_PER_RUN  = int(os.getenv("STORIES_PER_RUN", "1"))
TOP_STORIES_POOL = int(os.getenv("TOP_STORIES_POOL", "30"))
MIN_VIRAL_SCORE  = float(os.getenv("MIN_VIRAL_SCORE", "3.0"))
SCENES_PER_VIDEO = int(os.getenv("SCENES_PER_VIDEO", "4"))
SHORTS_ONLY      = os.getenv("SHORTS_ONLY", "true").lower() == "true"
MAX_SHORTS_WORDS = int(os.getenv("MAX_SHORTS_WORDS", "120"))
LONGFORM_ONLY    = os.getenv("LONGFORM_ONLY", "false").lower() == "true"
LONGFORM_WORD_COUNT = os.getenv("LONGFORM_WORD_COUNT", "750-900")

VIDEO_WIDTH   = 1920;  VIDEO_HEIGHT  = 1080
SHORTS_WIDTH  = 1080;  SHORTS_HEIGHT = 1920
FPS           = 24;    VIDEO_BITRATE = "5000k";  AUDIO_BITRATE = "192k"

OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")
IMAGES_DIR = os.path.join(OUTPUT_DIR, "images")
AUDIO_DIR  = os.path.join(OUTPUT_DIR, "audio")
VIDEO_DIR  = os.path.join(OUTPUT_DIR, "videos")
SHORTS_DIR = os.path.join(OUTPUT_DIR, "shorts")
THUMB_DIR  = os.path.join(OUTPUT_DIR, "thumbnails")
DB_PATH    = os.getenv("DB_PATH", "data/space_factcheck.db")
MUSIC_DIR  = os.getenv("MUSIC_DIR", "assets/music")

NARRATOR_STYLES = ["investigative", "deadpan", "cosmic_wonder", "skeptic", "breaking_news"]
DEFAULT_STYLE   = os.getenv("NARRATOR_STYLE", "investigative")

VIRAL_WEIGHTS = {
    "curiosity":          0.30,
    "thumbnail_strength": 0.20,
    "ragebait":           0.10,
    "retention_potential":0.25,
    "comment_potential":  0.10,
    "shareability":       0.05,
}

NEWSAPI_KEY          = os.getenv("NEWSAPI_KEY", "")
REDDIT_CLIENT_ID     = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
REDDIT_USER_AGENT    = os.getenv("REDDIT_USER_AGENT", "SpaceFactCheck/1.0")
PEXELS_API_KEY       = os.getenv("PEXELS_API_KEY", "")
