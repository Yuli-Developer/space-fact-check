"""
Space Fact Check — Pipeline Orchestrator.
discover → score → fact-check script → images → voice → compose → thumbnails → publish
"""
import logging
import os
import time
from datetime import datetime

from discovery.engine          import run_discovery
from prediction.viral_scorer   import score_and_rank
from ai.narrative_generator    import generate_script
from rendering.visual_director import generate_all_images
from rendering.kling_engine    import generate_all_kling_videos
from rendering.caption_engine  import prepare_voiceover
from rendering.audio_engine    import get_music_track
from rendering.video_composer  import compose_shorts, compose_main_video
from thumbnails.thumbnail_engine import generate_thumbnails
from publishing.youtube_publisher import publish_shorts, publish_main
from publishing.platform_adapter  import publish_all_platforms
from analytics.collector          import collect_and_store
from analytics.feedback_loop      import analyze_and_improve, get_optimized_style
from storage.database             import init_db, save_story, mark_used, save_run, update_run
from config.settings              import STORIES_PER_RUN, LONGFORM_ONLY

logger = logging.getLogger(__name__)


def _cleanup_old_output(keep_days: int = 2) -> None:
    """Delete output files older than keep_days after successful upload."""
    cutoff = time.time() - keep_days * 86400
    removed = 0
    for subdir in ("shorts", "videos", "audio", "images", "thumbnails"):
        folder = os.path.join("output", subdir)
        if not os.path.isdir(folder):
            continue
        for fname in os.listdir(folder):
            fpath = os.path.join(folder, fname)
            if os.path.isfile(fpath) and os.path.getmtime(fpath) < cutoff:
                os.remove(fpath)
                removed += 1
    if removed:
        logger.info(f"Cleanup: removed {removed} output files older than {keep_days} days")


def run_full_pipeline(
    upload: bool = True,
    narrator_style: str = None,
    skip_tiktok: bool = True,
    skip_instagram: bool = True,
) -> dict:
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    logger.info("=" * 60)
    logger.info(f"Space Fact Check — Pipeline run: {run_id}")
    logger.info("=" * 60)

    init_db()

    # ── 0. Feedback loop ──────────────────────────────────────────────────
    logger.info("Step 0: Checking analytics feedback loop...")
    analyze_and_improve()
    style = narrator_style or get_optimized_style()
    logger.info(f"Using narrator style: {style}")

    # ── 1. Discover stories ───────────────────────────────────────────────
    logger.info("Step 1: Discovering space/AI claims...")
    stories = run_discovery(limit_per_source=10)
    if not stories:
        logger.error("No stories discovered. Aborting.")
        return {"error": "no_stories"}

    # ── 2. Score for virality ─────────────────────────────────────────────
    logger.info(f"Step 2: Scoring {len(stories)} stories...")
    top_stories = score_and_rank(stories, top_n=STORIES_PER_RUN)
    if not top_stories:
        logger.error("No stories passed threshold. Aborting.")
        return {"error": "no_scored_stories"}

    story = top_stories[0]
    save_story(story)
    save_run(run_id,
             story_title=story["title"],
             narrator_style=style,
             viral_score=story.get("viral_score", 0),
             status="running")
    logger.info(f"Selected: [{story['viral_score']:.1f}/10] {story['title'][:80]}")

    try:
        # ── 3. Generate fact-check script ─────────────────────────────────
        logger.info(f"Step 3: Generating {style} fact-check script...")
        story = generate_script(story, style=style)

        # ── 4. Generate space images ──────────────────────────────────────
        logger.info("Step 4: Generating space images (Imagen 3)...")
        generate_all_images(story, run_id)
        generate_all_kling_videos(story, run_id)

        # ── 5. Voiceover + captions ───────────────────────────────────────
        if LONGFORM_ONLY:
            logger.info("Step 5: Generating long-form voiceover (Gemini TTS)...")
            audio_path, _, caption_chunks = prepare_voiceover(story["narration"], run_id)
            story["audio_path"]     = audio_path
            story["caption_chunks"] = caption_chunks
            if story.get("shorts_narration"):
                s_audio, _, s_chunks = prepare_voiceover(story["shorts_narration"], run_id, suffix="_shorts")
                story["shorts_audio_path"]     = s_audio
                story["shorts_caption_chunks"] = s_chunks
        else:
            logger.info("Step 5: Generating voiceover (Gemini TTS)...")
            s_audio, _, s_chunks = prepare_voiceover(story["narration"], run_id, suffix="_shorts")
            story["shorts_audio_path"]     = s_audio
            story["shorts_caption_chunks"] = s_chunks

        # ── 6. Music ──────────────────────────────────────────────────────
        logger.info("Step 6: Getting background music...")
        music_path = get_music_track()

        # ── 7. Compose video ──────────────────────────────────────────────
        if LONGFORM_ONLY:
            logger.info("Step 7: Composing 16:9 long-form video...")
            compose_main_video(story, story["audio_path"], music_path, run_id)
        else:
            logger.info("Step 7: Composing Shorts video...")
            compose_shorts(story, story["shorts_audio_path"], music_path, run_id)

        # ── 8. Thumbnails ─────────────────────────────────────────────────
        logger.info("Step 8: Generating thumbnails...")
        generate_thumbnails(story, run_id)

        # ── 9. Publish ────────────────────────────────────────────────────
        result = {
            "run_id":      run_id,
            "title":       story.get("youtube_title", story["title"]),
            "viral_score": story.get("viral_score", 0),
            "style":       style,
        }

        if upload:
            if LONGFORM_ONLY:
                logger.info("Step 9: Publishing long-form video to YouTube...")
                yt_id = publish_main(story, run_id)
                if yt_id:
                    result["youtube_url"]      = story.get("youtube_video_url")
                    result["youtube_video_id"] = yt_id
            else:
                logger.info("Step 9: Publishing Shorts to YouTube...")
                yt_id = publish_shorts(story, run_id)
                if yt_id:
                    result["shorts_url"]      = story.get("shorts_video_url")
                    result["shorts_video_id"] = yt_id

            mark_used(story["url"])

            # ── 10. Analytics ─────────────────────────────────────────────
            if yt_id:
                logger.info("Step 10: Collecting baseline analytics...")
                collect_and_store(run_id, yt_id, "youtube")

        update_run(run_id,
                   youtube_url=result.get("youtube_url", ""),
                   shorts_url=result.get("shorts_url", ""),
                   finished_at=datetime.utcnow().isoformat(),
                   status="done")

        logger.info("=" * 60)
        logger.info(f"Pipeline complete: {run_id}")
        if result.get("shorts_url"):
            logger.info(f"Shorts: {result['shorts_url']}")
        logger.info("=" * 60)

        _cleanup_old_output()
        return result

    except Exception as e:
        import traceback
        logger.error(f"Pipeline failed: {e}\n{traceback.format_exc()}")
        update_run(run_id, status="failed", error=str(e),
                   finished_at=datetime.utcnow().isoformat())
        raise
