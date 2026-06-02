"""
SQLite database layer.
Stores stories, runs, analytics, and feedback loop data.
"""

import sqlite3
import hashlib
import os
import json
from datetime import datetime
from config.settings import DB_PATH


def get_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS stories (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            url_hash    TEXT UNIQUE NOT NULL,
            title       TEXT NOT NULL,
            url         TEXT NOT NULL,
            source      TEXT NOT NULL,
            summary     TEXT,
            viral_score REAL,
            scores_json TEXT,
            used        INTEGER DEFAULT 0,
            fetched_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            used_at     TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS runs (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id           TEXT UNIQUE NOT NULL,
            started_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            finished_at      TIMESTAMP,
            story_title      TEXT,
            youtube_url      TEXT,
            shorts_url       TEXT,
            narrator_style   TEXT,
            viral_score      REAL,
            status           TEXT DEFAULT 'running',
            error            TEXT
        );

        CREATE TABLE IF NOT EXISTS analytics (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id       TEXT NOT NULL,
            video_id     TEXT NOT NULL,
            platform     TEXT NOT NULL,
            fetched_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            views        INTEGER DEFAULT 0,
            watch_time   REAL DEFAULT 0,
            ctr          REAL DEFAULT 0,
            avg_retention REAL DEFAULT 0,
            likes        INTEGER DEFAULT 0,
            comments     INTEGER DEFAULT 0,
            shares       INTEGER DEFAULT 0,
            revenue_usd  REAL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS feedback_log (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            insight      TEXT NOT NULL,
            applied_to   TEXT,
            improvement  TEXT
        );

        CREATE TABLE IF NOT EXISTS prompt_history (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            prompt_type  TEXT NOT NULL,
            style        TEXT,
            prompt_text  TEXT NOT NULL,
            result_score REAL,
            notes        TEXT
        );

        CREATE TABLE IF NOT EXISTS thumbnails (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id       TEXT NOT NULL,
            variant      INTEGER NOT NULL,
            path         TEXT NOT NULL,
            title        TEXT,
            ctr_score    REAL,
            emotion_score REAL,
            readability  REAL,
            mobile_score REAL,
            total_score  REAL,
            selected     INTEGER DEFAULT 0
        );
    """)
    conn.commit()
    conn.close()


def url_hash(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()


def is_duplicate(url: str) -> bool:
    conn = get_conn()
    row = conn.execute(
        "SELECT 1 FROM stories WHERE url_hash = ?", (url_hash(url),)
    ).fetchone()
    conn.close()
    return row is not None


def save_story(story: dict):
    conn = get_conn()
    try:
        conn.execute(
            """INSERT OR IGNORE INTO stories
               (url_hash, title, url, source, summary, viral_score, scores_json)
               VALUES (?,?,?,?,?,?,?)""",
            (
                url_hash(story["url"]),
                story["title"],
                story["url"],
                story.get("source", "unknown"),
                story.get("summary", ""),
                story.get("viral_score"),
                json.dumps(story.get("scores", {})),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def mark_used(url: str):
    conn = get_conn()
    conn.execute(
        "UPDATE stories SET used=1, used_at=CURRENT_TIMESTAMP WHERE url_hash=?",
        (url_hash(url),),
    )
    conn.commit()
    conn.close()


def save_run(run_id: str, **kwargs):
    conn = get_conn()
    conn.execute(
        """INSERT OR REPLACE INTO runs (run_id, story_title, narrator_style, viral_score, status)
           VALUES (?,?,?,?,?)""",
        (
            run_id,
            kwargs.get("story_title", ""),
            kwargs.get("narrator_style", "deadpan"),
            kwargs.get("viral_score", 0),
            kwargs.get("status", "running"),
        ),
    )
    conn.commit()
    conn.close()


def update_run(run_id: str, **kwargs):
    conn = get_conn()
    fields = ", ".join(f"{k}=?" for k in kwargs)
    values = list(kwargs.values()) + [run_id]
    conn.execute(f"UPDATE runs SET {fields} WHERE run_id=?", values)
    conn.commit()
    conn.close()


def save_analytics(run_id: str, video_id: str, platform: str, data: dict):
    conn = get_conn()
    conn.execute(
        """INSERT INTO analytics
           (run_id, video_id, platform, views, watch_time, ctr, avg_retention,
            likes, comments, shares, revenue_usd)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (
            run_id, video_id, platform,
            data.get("views", 0), data.get("watch_time", 0),
            data.get("ctr", 0), data.get("avg_retention", 0),
            data.get("likes", 0), data.get("comments", 0),
            data.get("shares", 0), data.get("revenue_usd", 0),
        ),
    )
    conn.commit()
    conn.close()


def save_thumbnail_scores(run_id: str, thumbnails: list[dict]):
    conn = get_conn()
    for t in thumbnails:
        conn.execute(
            """INSERT INTO thumbnails
               (run_id, variant, path, title, ctr_score, emotion_score,
                readability, mobile_score, total_score, selected)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                run_id, t["variant"], t["path"], t.get("title", ""),
                t.get("ctr_score", 0), t.get("emotion_score", 0),
                t.get("readability", 0), t.get("mobile_score", 0),
                t.get("total_score", 0), t.get("selected", 0),
            ),
        )
    conn.commit()
    conn.close()


def get_recent_analytics(limit: int = 20) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM analytics ORDER BY fetched_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_feedback(insight: str, applied_to: str = "", improvement: str = ""):
    conn = get_conn()
    conn.execute(
        "INSERT INTO feedback_log (insight, applied_to, improvement) VALUES (?,?,?)",
        (insight, applied_to, improvement),
    )
    conn.commit()
    conn.close()
