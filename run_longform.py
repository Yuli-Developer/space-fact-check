#!/usr/bin/env python3
"""
Long-form runner for space-fact-check.
Produces a ~8-10 min 16:9 "5 Claims Debunked" video — no Shorts.
Run by run_longform_rotation.py on a rotating schedule.
"""
import os
import sys
import logging

# Must be set BEFORE any project imports so settings.py picks them up
os.environ["SHORTS_ONLY"]           = "false"
os.environ["LONGFORM_ONLY"]         = "true"
os.environ["SCENES_PER_VIDEO"]      = "10"
os.environ["LONGFORM_WORD_COUNT"]   = "750-900"

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("longform.space-fact-check")

from pipeline.orchestrator import run_full_pipeline

logger.info("=" * 60)
logger.info("Space Fact Check — LONG-FORM run")
logger.info("=" * 60)

result = run_full_pipeline(upload=True)

if result.get("youtube_url"):
    logger.info(f"✓ Long-form uploaded: {result['youtube_url']}")
elif result.get("error"):
    logger.error(f"✗ Failed: {result['error']}")
    sys.exit(1)
