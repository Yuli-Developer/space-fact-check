"""
Analytics Feedback Loop — analyzes performance data and self-improves
prompts, style selection, and thumbnail strategies using Gemini.
"""

import json
import logging
from google import genai
from config.settings import GEMINI_API_KEY, GEMINI_MODEL, DEFAULT_STYLE
from ai.prompt_templates import FEEDBACK_PROMPT
from analytics.collector import get_performance_summary
from storage.database import save_feedback, get_recent_analytics

logger = logging.getLogger(__name__)
client = genai.Client(api_key=GEMINI_API_KEY)

# In-memory store for current session improvements
_current_overrides: dict = {}


def analyze_and_improve() -> dict:
    """
    Pull analytics, ask Gemini for insights, update prompt overrides.
    Returns dict of improvements made.
    """
    summary = get_performance_summary(limit=30)

    if not summary or summary.get("total_videos", 0) < 2:
        logger.info("Not enough data for feedback loop (need at least 2 videos)")
        return {}

    analytics_text = json.dumps(summary["recent_data"][:5], indent=2)
    historical     = (
        f"Average CTR: {summary['avg_ctr']*100:.2f}%\n"
        f"Average Retention: {summary['avg_retention']:.1f}%\n"
        f"Average Views: {summary['avg_views']:.0f}\n"
        f"Videos analyzed: {summary['total_videos']}"
    )

    prompt = FEEDBACK_PROMPT.format(
        analytics_data=analytics_text,
        historical_summary=historical,
    )

    try:
        resp = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        raw  = resp.text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        insights = json.loads(raw.strip())

        improvements = insights.get("prompt_improvements", {})

        # Apply to in-memory overrides for next run
        global _current_overrides
        if insights.get("best_style"):
            _current_overrides["narrator_style"] = insights["best_style"]
            logger.info(f"Feedback: switching to {insights['best_style']} narrator style")

        if improvements.get("narration_tweak"):
            _current_overrides["narration_hint"] = improvements["narration_tweak"]

        if improvements.get("title_tweak"):
            _current_overrides["title_hint"] = improvements["title_tweak"]

        # Save to DB
        for key, insight in {
            "best_style":         insights.get("style_reasoning", ""),
            "thumbnail_insights": str(insights.get("thumbnail_insights", [])),
            "title_patterns":     str(insights.get("title_patterns", [])),
            "content_focus":      insights.get("next_content_focus", ""),
        }.items():
            if insight:
                save_feedback(
                    insight=insight,
                    applied_to=key,
                    improvement=improvements.get(f"{key}_tweak", ""),
                )

        logger.info(f"Feedback loop applied {len(_current_overrides)} improvements")
        return _current_overrides

    except Exception as e:
        logger.warning(f"Feedback loop failed: {e}")
        return {}


def get_optimized_style() -> str:
    """Return the current best narrator style based on analytics."""
    return _current_overrides.get("narrator_style", DEFAULT_STYLE)


def get_narration_hint() -> str:
    """Return any narration improvement hints from the feedback loop."""
    return _current_overrides.get("narration_hint", "")


def get_title_hint() -> str:
    """Return any title improvement hints from the feedback loop."""
    return _current_overrides.get("title_hint", "")


def reset_overrides():
    """Clear all feedback loop overrides (for testing)."""
    global _current_overrides
    _current_overrides = {}
