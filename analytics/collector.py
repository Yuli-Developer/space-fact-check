"""
Analytics Collector — pulls performance data from YouTube Analytics API.
Stores CTR, watch time, retention, likes, comments, shares.
"""

import pickle
import os
import logging
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from config.settings import YOUTUBE_TOKEN_PATH
from storage.database import save_analytics, get_recent_analytics

logger = logging.getLogger(__name__)


def _get_analytics_service():
    with open(YOUTUBE_TOKEN_PATH, "rb") as f:
        creds = pickle.load(f)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("youtubeAnalytics", "v2", credentials=creds)


def _get_youtube_service():
    with open(YOUTUBE_TOKEN_PATH, "rb") as f:
        creds = pickle.load(f)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("youtube", "v3", credentials=creds)


def fetch_video_stats(video_id: str) -> dict:
    """Get basic video stats from YouTube Data API."""
    try:
        yt = _get_youtube_service()
        resp = yt.videos().list(
            part="statistics,contentDetails",
            id=video_id,
        ).execute()

        if not resp.get("items"):
            return {}

        stats = resp["items"][0]["statistics"]
        return {
            "views":    int(stats.get("viewCount", 0)),
            "likes":    int(stats.get("likeCount", 0)),
            "comments": int(stats.get("commentCount", 0)),
            "shares":   0,   # not available via Data API
        }
    except Exception as e:
        logger.warning(f"Failed to fetch stats for {video_id}: {e}")
        return {}


def fetch_analytics(video_id: str, days_back: int = 7) -> dict:
    """Get analytics data: CTR, watch time, retention."""
    if not os.path.exists(YOUTUBE_TOKEN_PATH):
        logger.warning("No YouTube token — cannot fetch analytics")
        return {}

    try:
        ya     = _get_analytics_service()
        end    = datetime.utcnow().date()
        start  = (datetime.utcnow() - timedelta(days=days_back)).date()

        resp = ya.reports().query(
            ids="channel==MINE",
            startDate=str(start),
            endDate=str(end),
            metrics="views,estimatedMinutesWatched,averageViewPercentage,clickThroughRate",
            filters=f"video=={video_id}",
        ).execute()

        rows = resp.get("rows", [])
        if not rows:
            return {}

        row         = rows[0]
        views       = int(row[0]) if row[0] else 0
        watch_mins  = float(row[1]) if row[1] else 0
        retention   = float(row[2]) if row[2] else 0
        ctr         = float(row[3]) if row[3] else 0

        return {
            "views":         views,
            "watch_time":    watch_mins,
            "avg_retention": retention,
            "ctr":           ctr,
        }
    except Exception as e:
        logger.warning(f"Analytics API error for {video_id}: {e}")
        # Fall back to basic stats only
        return fetch_video_stats(video_id)


def collect_and_store(run_id: str, video_id: str, platform: str = "youtube"):
    """Fetch analytics and store in DB."""
    logger.info(f"Collecting analytics for {video_id}...")

    data = fetch_analytics(video_id)
    if not data:
        data = fetch_video_stats(video_id)

    if data:
        save_analytics(run_id, video_id, platform, data)
        logger.info(
            f"Analytics stored: {data.get('views', 0)} views, "
            f"{data.get('ctr', 0)*100:.1f}% CTR, "
            f"{data.get('avg_retention', 0):.1f}% retention"
        )
    else:
        logger.warning(f"No analytics data available for {video_id}")

    return data


def get_performance_summary(limit: int = 20) -> dict:
    """Aggregate recent performance stats for feedback loop."""
    rows = get_recent_analytics(limit)
    if not rows:
        return {}

    total   = len(rows)
    avg_ctr = sum(r["ctr"] for r in rows) / total
    avg_ret = sum(r["avg_retention"] for r in rows) / total
    avg_views = sum(r["views"] for r in rows) / total

    return {
        "total_videos":    total,
        "avg_ctr":         round(avg_ctr, 4),
        "avg_retention":   round(avg_ret, 2),
        "avg_views":       round(avg_views, 0),
        "recent_data":     rows[:5],
    }
