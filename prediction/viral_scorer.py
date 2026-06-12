"""Viral scorer for Space Fact Check — space/AI claims with misinformation potential."""
import re
import logging
from config.settings import MIN_VIRAL_SCORE, VIRAL_WEIGHTS

logger = logging.getLogger(__name__)

CURIOSITY_KEYWORDS = [
    # Space discovery hooks
    "alien", "extraterrestrial", "life on mars", "life on", "habitable",
    "signal", "contact", "ufo", "uap", "unexplained",
    # NASA / missions
    "nasa", "james webb", "webb telescope", "hubble", "voyager", "perseverance",
    "artemis", "spacex", "starship", "mars", "moon", "asteroid", "comet",
    # AI claims
    "sentient", "conscious", "ai thinks", "ai feels", "artificial general",
    "agi", "superintelligence", "ai surpasses", "ai beats", "chatgpt",
    "gemini", "gpt", "ai discovers", "robot",
    # Physics clickbait
    "black hole", "warp drive", "faster than light", "time travel",
    "parallel universe", "dark matter", "dark energy", "quantum",
    "big bang", "multiverse", "simulation",
    # Discovery language
    "discovered", "found", "detected", "confirmed", "evidence", "proof",
    "breakthrough", "revolutionary", "first ever", "never before",
]

THUMBNAIL_KEYWORDS = [
    "nasa found", "scientists discover", "proof of alien",
    "ai is now", "we found life", "this changes everything",
    "shocking discovery", "they were wrong", "actually happened",
    "the truth about", "what nasa", "what scientists",
    "real reason", "never told", "hidden truth",
]

RAGEBAIT_KEYWORDS = [
    "they lied", "cover up", "suppressed", "hidden", "secret",
    "they don't want", "government hiding", "big pharma", "conspiracy",
    "fake", "hoax", "psyop",
]

RETENTION_KEYWORDS = [
    "what really happened", "the real story", "actually means",
    "scientists explain", "debunked", "fact check", "myth vs reality",
    "here is what", "the truth is", "turns out",
    "you won't believe", "wait for it", "the twist",
]

COMMENT_KEYWORDS = [
    "elon musk", "nasa", "spacex", "china", "russia", "iss",
    "chatgpt", "openai", "google", "apple", "meta",
    "flat earth", "moon landing", "climate", "evolution",
]

SHAREABILITY_KEYWORDS = [
    "mind blowing", "actually", "reality is", "turns out",
    "the real number", "correcting", "scientists say",
    "study shows", "peer reviewed", "the paper says",
]

REJECT_KEYWORDS = [
    "cooking", "recipe", "sports", "football", "basketball",
    "celebrity gossip", "fashion", "makeup",
]


def _keyword_score(text: str, keywords: list, cap: float = 10.0) -> float:
    hits = sum(1 for k in keywords if k.lower() in text.lower())
    return min(cap, round(hits * 2.0, 1))


def _clickbait_boost(text: str) -> float:
    """Bonus for stories that are clearly making a big claim."""
    patterns = [
        r"found (life|aliens|proof|evidence)",
        r"(discover|detect|confirm).{0,20}(alien|life|signal)",
        r"ai (is now|has become|surpass|beat|think|feel)",
        r"(proof|evidence) of (alien|extraterrestrial|life)",
        r"(first|never).{0,10}(human history|ever recorded|in space)",
    ]
    return sum(0.5 for p in patterns if re.search(p, text, re.I))


def score_story(story: dict) -> dict:
    text = story.get("title", "") + " " + story.get("summary", "")

    if any(r in text.lower() for r in REJECT_KEYWORDS):
        story["viral_score"] = 0.0
        return story

    scores = {
        "curiosity":           _keyword_score(text, CURIOSITY_KEYWORDS),
        "thumbnail_strength":  _keyword_score(text, THUMBNAIL_KEYWORDS),
        "ragebait":            _keyword_score(text, RAGEBAIT_KEYWORDS),
        "retention_potential": _keyword_score(text, RETENTION_KEYWORDS),
        "comment_potential":   _keyword_score(text, COMMENT_KEYWORDS),
        "shareability":        _keyword_score(text, SHAREABILITY_KEYWORDS),
    }

    total = sum(scores.get(k, 0) * w for k, w in VIRAL_WEIGHTS.items())
    total = min(10.0, round(total + _clickbait_boost(text), 1))

    story["viral_score"] = total
    story["scores"] = scores
    return story


def score_and_rank(stories: list, top_n: int = 5) -> list:
    scored = [score_story(s) for s in stories]
    passed = [s for s in scored if s["viral_score"] >= MIN_VIRAL_SCORE]
    ranked = sorted(passed, key=lambda x: x["viral_score"], reverse=True)
    logger.info(f"Scored {len(stories)} → {len(passed)} passed → top {min(top_n, len(ranked))} selected")
    if not passed and scored:
        top_misses = sorted(scored, key=lambda x: x["viral_score"], reverse=True)[:5]
        logger.warning(f"No stories above threshold {MIN_VIRAL_SCORE}. Top 5 scores:")
        for s in top_misses:
            logger.warning(f"  {s['viral_score']:.1f}  {s.get('title', '')[:80]}")
    return ranked[:top_n]
