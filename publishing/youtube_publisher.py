"""YouTube Publisher — Space Fact Check channel."""
import re
import os
import pickle
import logging
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from config.settings import YOUTUBE_CLIENT_SECRETS, YOUTUBE_TOKEN_PATH

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.readonly",
]

CHANNEL_TAGS = [
    "space", "science", "factcheck", "nasa", "astronomy", "physics",
    "universe", "cosmos", "sciencefacts", "didyouknow", "myth", "debunked",
]
SHORTS_TAGS = ["shorts", "youtubeshorts", "spaceshorts", "scienceshorts", "factcheckshorts"]


def _trim_tags(tags: list) -> list:
    result, total = [], 0
    for t in tags:
        t = re.sub(r"[^a-zA-Z0-9 ._-]", "", t.replace("#", "")).strip()
        if not t or len(t) > 30:
            continue
        if total + len(t) + 1 <= 498:
            result.append(t)
            total += len(t) + 1
    return result


def _get_service():
    creds = None
    if os.path.exists(YOUTUBE_TOKEN_PATH):
        with open(YOUTUBE_TOKEN_PATH, "rb") as f:
            creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            creds = InstalledAppFlow.from_client_secrets_file(
                YOUTUBE_CLIENT_SECRETS, SCOPES
            ).run_local_server(port=0)
        with open(YOUTUBE_TOKEN_PATH, "wb") as f:
            pickle.dump(creds, f)
    return build("youtube", "v3", credentials=creds)


def _upload_video(youtube, path: str, body: dict) -> str:
    media = MediaFileUpload(path, mimetype="video/mp4", resumable=True, chunksize=10*1024*1024)
    req   = youtube.videos().insert(part=",".join(body.keys()), body=body, media_body=media)
    resp  = None
    while resp is None:
        st, resp = req.next_chunk()
        if st:
            logger.info(f"Upload: {int(st.progress()*100)}%")
    return resp["id"]


def _build_chapters(story: dict, pre_roll: float = 3.0) -> str:
    """Generate YouTube chapter timestamps for longform videos."""
    scenes    = story.get("scenes", [])
    narration = story.get("narration", "")
    if len(scenes) < 3 or not narration:
        return ""
    total_words = max(len(narration.split()), 1)
    total_dur   = total_words / 2.5   # ~2.5 words/sec TTS
    lines = ["0:00 Introduction"]
    t = pre_roll
    for i, scene in enumerate(scenes):
        seg   = scene.get("narration_segment", "")
        words = len(seg.split()) if seg else (total_words // len(scenes))
        mm, ss = int(t) // 60, int(t) % 60
        label = f"Claim {i + 1}" if i < len(scenes) - 1 else "Verdict"
        # Append first 4 words of the scene for context
        snippet = " ".join(seg.split()[:4]).rstrip(".,!?") if seg else ""
        lines.append(f"{mm}:{ss:02d} {label}: {snippet}...")
        t += (words / total_words) * total_dur
    return "\n".join(lines)


def _build_description(story: dict, is_shorts: bool = False) -> str:
    hook    = story.get("description_hook", story.get("hook", ""))
    claim   = story.get("claim_statement", "")
    reality = story.get("reality_statement", "")
    verdict = story.get("verdict", "")
    url     = story.get("url", "")
    source  = story.get("source", "")

    sections = []
    # Hook always first — this is what YouTube shows before "Show more"
    if hook:
        sections.append(hook)
    if claim:
        sections.append(f"\nTHE CLAIM: {claim}")
    if reality:
        sections.append(f"THE REALITY: {reality}")
    if verdict:
        sections.append(f"THE VERDICT: {verdict}")

    # Chapter markers for longform only
    if not is_shorts:
        chapters = _build_chapters(story)
        if chapters:
            sections.append(f"\n{chapters}")

    if url:
        sections.append(f"\nSource: {source}\n{url}")

    sections.append(
        "\n---\n"
        "Space Fact Check — we fact-check viral space and AI claims daily.\n"
        "Subscribe so you always get the real story.\n\n"
        "#SpaceFactCheck #ScienceFacts #NASA #Space #FactCheck "
        "#Astronomy #Science #DidYouKnow #SpaceScience #AIFacts"
    )
    return "\n".join(sections)


def publish_shorts(story: dict, run_id: str) -> str | None:
    sp = story.get("shorts_path")
    if not sp or not os.path.exists(sp):
        logger.warning("No Shorts file — skipping upload")
        return None

    youtube = _get_service()
    title   = f"{story.get('youtube_title', story['title'])[:90]} #Shorts"
    tags    = _trim_tags(story.get("tags", []) + CHANNEL_TAGS + SHORTS_TAGS)

    body = {
        "snippet": {
            "title":           title,
            "description":     _build_description(story, is_shorts=True),
            "tags":            tags,
            "categoryId":      "28",   # Science & Technology
            "defaultLanguage": "en",
        },
        "status": {
            "privacyStatus":           "public",
            "madeForKids":             False,
            "selfDeclaredMadeForKids": False,
        },
    }

    logger.info(f"Uploading: {title}")
    vid = _upload_video(youtube, sp, body)
    logger.info(f"Uploaded: https://www.youtube.com/shorts/{vid}")

    story["shorts_video_id"]  = vid
    story["shorts_video_url"] = f"https://www.youtube.com/shorts/{vid}"

    thumb = story.get("thumbnail_path")
    if thumb and os.path.exists(thumb):
        try:
            youtube.thumbnails().set(
                videoId=vid,
                media_body=MediaFileUpload(thumb, mimetype="image/jpeg"),
            ).execute()
        except Exception as e:
            logger.error(f"Thumbnail failed: {e}")

    return vid


def publish_main(story: dict, run_id: str) -> str | None:
    """Upload long-form main video. Returns YouTube video ID."""
    video_path = story.get("video_path")
    if not video_path or not os.path.exists(video_path):
        logger.error("No main video file found — skipping upload")
        return None

    youtube = _get_service()
    title   = story.get("youtube_title", story["title"])[:100]
    tags    = _trim_tags(story.get("tags", []) + CHANNEL_TAGS)

    body = {
        "snippet": {
            "title":           title,
            "description":     _build_description(story),
            "tags":            tags,
            "categoryId":      "28",   # Science & Technology
            "defaultLanguage": "en",
        },
        "status": {
            "privacyStatus":           "public",
            "madeForKids":             False,
            "selfDeclaredMadeForKids": False,
        },
    }

    logger.info(f"Uploading long-form: {title}")
    vid = _upload_video(youtube, video_path, body)
    logger.info(f"Uploaded: https://www.youtube.com/watch?v={vid}")

    thumb = story.get("thumbnail_path")
    if thumb and os.path.exists(thumb):
        try:
            youtube.thumbnails().set(
                videoId=vid,
                media_body=MediaFileUpload(thumb, mimetype="image/jpeg"),
            ).execute()
            logger.info(f"Thumbnail set for {vid}")
        except Exception as e:
            logger.warning(f"Thumbnail upload skipped: {e}")

    story["youtube_video_id"]  = vid
    story["youtube_video_url"] = f"https://www.youtube.com/watch?v={vid}"
    return vid
