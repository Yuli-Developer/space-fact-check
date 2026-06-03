#!/usr/bin/env python3
"""
Long-form runner for space-fact-check.
Produces a ~8-10 min 16:9 "5 Claims Debunked" video — no Shorts.
Run by run_longform_rotation.py on a rotating schedule.
"""
import os
import sys
import time
import logging
import fcntl

# Must be set BEFORE any project imports so settings.py picks them up
os.environ["SHORTS_ONLY"]           = "false"
os.environ["LONGFORM_ONLY"]         = "true"
os.environ["SCENES_PER_VIDEO"]      = "10"
os.environ["LONGFORM_WORD_COUNT"]   = "750-900"

_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(_DIR)
sys.path.insert(0, _DIR)

# Prevent concurrent runs — shared lock with run_batch.py
_LOCK_FILE = open(os.path.join(_DIR, ".batch.lock"), "w")
try:
    fcntl.flock(_LOCK_FILE, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    print("space-fact-check: another job is already running — exiting.")
    sys.exit(0)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("longform.space-fact-check")

from pipeline.orchestrator import run_full_pipeline

logger.info("=" * 60)
logger.info("Space Fact Check — LONG-FORM run")
logger.info("=" * 60)

delays = [60, 120, 180]
result = None
for attempt in range(4):
    try:
        result = run_full_pipeline(upload=True)
        break
    except Exception as e:
        is_transient = (
            any(x in str(e) for x in ("503", "UNAVAILABLE", "429", "Resource has been exhausted"))
            or type(e).__name__ == "JSONDecodeError"
        )
        if attempt < 3 and is_transient:
            wait = delays[min(attempt, len(delays) - 1)]
            logger.warning(f"Transient API error (attempt {attempt + 1}/3), retrying in {wait}s: {e}")
            time.sleep(wait)
        else:
            logger.error(f"✗ Failed after retries: {e}")
            sys.exit(1)

if result and result.get("youtube_url"):
    logger.info(f"✓ Long-form uploaded: {result['youtube_url']}")
elif result and result.get("error"):
    logger.error(f"✗ Failed: {result['error']}")
    sys.exit(1)
