"""
Narrative Generator — Space Fact Check.
Uses Gemini 2.5 Pro for scripts (better creative quality than Flash).
"""
import json
import logging
from google import genai
from config.settings import (
    GEMINI_API_KEY, GEMINI_PRO_MODEL, GEMINI_MODEL,
    DEFAULT_STYLE, MAX_SHORTS_WORDS, LONGFORM_ONLY, LONGFORM_WORD_COUNT, SCENES_PER_VIDEO,
)
from ai.prompt_templates import STYLE_SYSTEM_PROMPTS, SHORTS_SCRIPT_PROMPT, LONGFORM_SCRIPT_PROMPT

logger = logging.getLogger(__name__)
client = genai.Client(api_key=GEMINI_API_KEY)


def _parse_response(resp) -> dict:
    raw = resp.text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def generate_script(story: dict, style: str = None) -> dict:
    style = style or DEFAULT_STYLE
    if style not in STYLE_SYSTEM_PROMPTS:
        style = "investigative"

    logger.info(f"Generating {style} fact-check script for: {story['title'][:70]}")

    if LONGFORM_ONLY:
        return _generate_full_script(story, style)

    prompt = SHORTS_SCRIPT_PROMPT.format(
        system_prompt=STYLE_SYSTEM_PROMPTS[style],
        title=story["title"],
        summary=story.get("summary", story["title"]),
        url=story.get("url", ""),
        style=style,
    )

    # Use Pro for better script quality — this is the most important step
    try:
        resp = client.models.generate_content(model=GEMINI_PRO_MODEL, contents=prompt)
    except Exception as e:
        logger.warning(f"Pro model failed ({e}), falling back to Flash")
        resp = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)

    data = _parse_response(resp)

    narration = data["narration"]
    word_count = len(narration.split())
    if word_count > MAX_SHORTS_WORDS:
        logger.warning(f"Narration {word_count} words — trimming to {MAX_SHORTS_WORDS}")
        narration = " ".join(narration.split()[:MAX_SHORTS_WORDS])

    story["youtube_title"]       = data["youtube_title"]
    story["hook"]                = data["hook"]
    story["narration"]           = narration
    story["shorts_narration"]    = narration
    story["claim_statement"]     = data.get("claim_statement", "")
    story["reality_statement"]   = data.get("reality_statement", "")
    story["verdict"]             = data.get("verdict", "")
    story["title_variants"]      = data.get("title_variants", [data["youtube_title"]])
    story["characters"]          = data.get("characters", "space imagery, no people")
    story["scenes"]              = data["scenes"]
    story["shorts_scenes"]       = data["scenes"]
    story["tags"]                = data.get("tags", [])
    story["description_hook"]    = data.get("description_hook", "")
    story["narrator_style"]      = style
    story["shorts_only"]         = True
    story["visual_style"]        = "cosmic"

    logger.info(f"Script ready [{style}]: 4 scenes | {len(narration.split())} words")
    return story


def _generate_full_script(story: dict, style: str) -> dict:
    """Long-form: 5 claims debunked, ~10 scenes, 750-900 words."""
    prompt = LONGFORM_SCRIPT_PROMPT.format(
        system_prompt=STYLE_SYSTEM_PROMPTS[style],
        title=story["title"],
        summary=story.get("summary", story["title"]),
        url=story.get("url", ""),
        style=style,
        word_count=LONGFORM_WORD_COUNT,
        num_scenes=SCENES_PER_VIDEO,
    )

    try:
        resp = client.models.generate_content(model=GEMINI_PRO_MODEL, contents=prompt)
    except Exception as e:
        logger.warning(f"Pro model failed ({e}), falling back to Flash")
        resp = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)

    data = _parse_response(resp)

    story["youtube_title"]     = data["youtube_title"]
    story["hook"]              = data["hook"]
    story["narration"]         = data["narration"]
    story["shorts_narration"]  = data.get("shorts_narration", "")
    story["claim_statement"]   = data.get("claim_statement", "")
    story["reality_statement"] = data.get("reality_statement", "")
    story["verdict"]           = data.get("verdict", "")
    story["title_variants"]    = data.get("title_variants", [data["youtube_title"]])
    story["characters"]        = data.get("characters", "space imagery, no faces")
    story["scenes"]            = data["scenes"]
    story["shorts_scenes"]     = data.get("shorts_scenes", data["scenes"][:4])
    story["tags"]              = data.get("tags", [])
    story["description_hook"]  = data.get("description_hook", "")
    story["narrator_style"]    = style
    story["visual_style"]      = "cosmic"

    logger.info(f"Longform script ready [{style}]: {len(story['scenes'])} scenes | {len(story['narration'].split())} words")
    return story
