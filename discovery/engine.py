"""Space Fact Check Discovery Engine."""
import logging
from datetime import datetime
from storage.database import is_duplicate

logger = logging.getLogger(__name__)


def _normalize(s: dict) -> dict:
    return {
        "title":      s.get("title", "").strip(),
        "url":        s.get("url", "").strip(),
        "summary":    s.get("summary", s.get("title", "")).strip(),
        "source":     s.get("source", "unknown"),
        "upvotes":    s.get("upvotes", 0),
        "category":   s.get("category", "space_factcheck"),
        "fetched_at": datetime.utcnow().isoformat(),
    }


def run_discovery(limit_per_source: int = 10) -> list[dict]:
    from discovery.space_source import fetch_space_stories

    raw = fetch_space_stories(limit=limit_per_source)

    seen_urls, stories = set(), []
    for s in raw:
        url = s.get("url", "")
        if not url or url in seen_urls or is_duplicate(url):
            continue
        seen_urls.add(url)
        stories.append(_normalize(s))

    logger.info(f"Space Fact Check discovery: {len(stories)} unique stories")
    return stories
