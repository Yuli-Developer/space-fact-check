"""
Space Fact Check — Discovery Source.
Finds viral space/AI/science claims that are wrong or misleading.

Sources:
  - Google News RSS: trending space + AI claims
  - Science news RSS: Space.com, NASA, ScienceAlert, Ars Technica
  - Reddit: r/space, r/Futurology, r/singularity viral posts
"""
import logging
import feedparser
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

CLAIM_QUERIES = [
    "alien life discovered 2025",
    "NASA discovery space 2025",
    "scientists find proof extraterrestrial",
    "AI sentient consciousness 2025",
    "space breakthrough discovery",
    "mars life evidence found",
    "black hole mystery solved",
    "james webb telescope discovery",
    "SpaceX Mars colony timeline",
    "AI surpasses human intelligence",
]

RSS_FEEDS = [
    "https://www.nasa.gov/rss/dyn/breaking_news.rss",
    "https://www.space.com/feeds/all",
    "https://www.sciencealert.com/feed",
    "https://feeds.arstechnica.com/arstechnica/science",
    "https://hnrss.org/frontpage?q=space+AI+discovery+alien",
    "https://www.newscientist.com/subject/space/feed/",
    "https://phys.org/rss-feed/space-news/",
]

CLICKBAIT_KEYWORDS = [
    "discovered", "proven", "confirmed", "found", "breakthrough",
    "revolutionary", "game-changing", "shocking", "unprecedented",
    "scientists say", "study finds", "new evidence", "first ever",
    "could be", "might be", "suggests", "indicates", "reveals",
    "alien", "extraterrestrial", "life on mars", "sentient", "conscious",
    "warp drive", "time travel", "parallel universe", "simulation",
    "faster than light", "immortality", "cure", "secret",
]

FACT_CHECK_KEYWORDS = [
    "claim", "viral", "wrong", "debunked", "myth", "actually",
    "truth", "reality", "fact", "false", "misleading", "misunderstood",
    "not what", "more complicated", "scientists clarify",
]

VIRAL_SPACE_KEYWORDS = [
    "alien", "nasa", "mars", "moon", "space", "galaxy", "universe",
    "black hole", "asteroid", "comet", "telescope", "webb",
    "ai", "robot", "consciousness", "quantum", "fusion", "warp",
    "elon", "spacex", "starship", "iss", "astronaut",
]

BORING_KEYWORDS = [
    "weather report", "local news", "sports", "politics", "election",
    "stock market", "recipe", "fashion",
]


def _is_interesting(title: str, summary: str = "") -> bool:
    text = (title + " " + summary).lower()
    if any(b in text for b in BORING_KEYWORDS):
        return False
    has_clickbait = any(k in text for k in CLICKBAIT_KEYWORDS)
    has_space_ai  = any(k in text for k in VIRAL_SPACE_KEYWORDS)
    return has_clickbait or has_space_ai


def _to_story(title: str, summary: str, url: str, source: str) -> dict:
    return {
        "title":      title,
        "url":        url,
        "summary":    summary[:600],
        "source":     source,
        "upvotes":    0,
        "category":   "space_factcheck",
        "fetched_at": datetime.utcnow().isoformat(),
    }


def _fetch_gnews(query: str, limit: int = 6) -> list[dict]:
    url = f"https://news.google.com/rss/search?q={query.replace(' ', '+')}&hl=en-US&gl=US&ceid=US:en"
    stories = []
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:limit]:
            title   = entry.get("title", "")
            summary = getattr(entry, "summary", "") or ""
            link    = entry.get("link", "")
            if title and _is_interesting(title, summary):
                stories.append(_to_story(title, summary, link, "Google News"))
    except Exception as e:
        logger.debug(f"GNews '{query}': {e}")
    return stories


def _fetch_rss(url: str, limit: int = 8) -> list[dict]:
    stories = []
    try:
        feed = feedparser.parse(url)
        src  = feed.feed.get("title", url)
        for entry in feed.entries[:limit]:
            title   = entry.get("title", "")
            summary = getattr(entry, "summary", "") or ""
            link    = entry.get("link", "")
            if title and _is_interesting(title, summary):
                stories.append(_to_story(title, summary, link, src))
    except Exception as e:
        logger.debug(f"RSS {url}: {e}")
    return stories


def fetch_space_stories(limit: int = 10) -> list[dict]:
    tasks = (
        [(_fetch_gnews, q, 6) for q in CLAIM_QUERIES]
        + [(_fetch_rss, url, 8) for url in RSS_FEEDS]
    )

    stories = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fn, arg, lim): fn for fn, arg, lim in tasks}
        for future in as_completed(futures):
            try:
                stories.extend(future.result())
            except Exception as e:
                logger.debug(f"Task failed: {e}")

    logger.info(f"Space Fact Check: {len(stories)} stories found")
    return stories
