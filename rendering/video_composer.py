"""
Video Composer — Space Fact Check.
Assembles final Shorts video with cosmic branding.
"""
import os
import logging
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import (
    VideoClip, AudioFileClip, CompositeAudioClip,
    concatenate_videoclips, concatenate_audioclips,
)
from rendering.motion_engine import make_animated_portrait, apply_motion
from rendering.caption_engine import draw_captions
from config.settings import (
    SHORTS_DIR, VIDEO_DIR, FPS,
    SHORTS_WIDTH as SW, SHORTS_HEIGHT as SH,
    VIDEO_WIDTH as W, VIDEO_HEIGHT as H,
    VIDEO_BITRATE, AUDIO_BITRATE,
)

logger = logging.getLogger(__name__)

CHANNEL_NAME = "SPACE FACT CHECK"
ACCENT_COLOR = "#003366"    # deep space blue
TEXT_COLOR   = "#00E5FF"    # cyan


def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in [
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _wrap(text: str, max_chars: int = 26) -> list[str]:
    words, lines, line = text.split(), [], []
    for w in words:
        if len(" ".join(line + [w])) <= max_chars:
            line.append(w)
        else:
            if line:
                lines.append(" ".join(line))
            line = [w]
    if line:
        lines.append(" ".join(line))
    return lines


def make_intro_card(title: str, duration: float = 2.5) -> VideoClip:
    img  = Image.new("RGB", (SW, SH), "#000008")
    draw = ImageDraw.Draw(img)

    # Starfield background
    import random
    rng = random.Random(42)
    for _ in range(400):
        x = rng.randint(0, SW)
        y = rng.randint(0, SH)
        r = rng.choice([1, 1, 1, 2])
        b = rng.randint(100, 255)
        draw.ellipse([x-r, y-r, x+r, y+r], fill=(b, b, b))

    # Top bar
    draw.rectangle([0, 0, SW, 8], fill=ACCENT_COLOR)

    # Channel badge
    lf = _font(30)
    draw.rectangle([30, 25, 370, 68], fill=ACCENT_COLOR)
    draw.text((200, 46), CHANNEL_NAME, font=lf, fill=TEXT_COLOR, anchor="mm")

    # FACT CHECK badge
    draw.rectangle([SW - 200, 25, SW - 30, 68], fill="#CC0000")
    draw.text((SW - 115, 46), "FACT CHECK", font=_font(26), fill="white", anchor="mm")

    # Title
    hf    = _font(82)
    lines = _wrap(title.upper(), max_chars=22)
    lh    = 96
    total = len(lines) * lh
    y     = (SH - total) // 2 - 40
    for line in lines:
        for dx, dy in [(-3, 3), (3, 3)]:
            draw.text((SW // 2 + dx, y + dy), line, font=hf, fill="#000020", anchor="mt")
        draw.text((SW // 2, y), line, font=hf, fill="white", anchor="mt")
        y += lh

    # Bottom bar
    draw.rectangle([0, SH - 55, SW, SH], fill=ACCENT_COLOR)
    sf = _font(24)
    draw.text((SW // 2, SH - 28),
              "SUBSCRIBE  •  DAILY FACT CHECKS  •  SPACE FACT CHECK",
              font=sf, fill=TEXT_COLOR, anchor="mm")

    arr = np.array(img)
    return VideoClip(lambda t: arr, duration=duration).with_fps(FPS)


def compose_shorts(story: dict, shorts_audio_path: str,
                    music_path: str | None, run_id: str) -> str:
    os.makedirs(SHORTS_DIR, exist_ok=True)
    output = os.path.join(SHORTS_DIR, f"{run_id}_shorts.mp4")

    narration_audio = AudioFileClip(shorts_audio_path)
    total_dur       = narration_audio.duration
    shorts_scenes   = story.get("shorts_scenes", story.get("scenes", [])[:4])
    image_paths     = story.get("image_paths", [])
    caption_chunks  = story.get("shorts_caption_chunks", story.get("caption_chunks", []))
    n_scenes        = max(len(shorts_scenes), 1)
    scene_dur       = total_dur / n_scenes

    logger.info(f"Composing Shorts: {n_scenes} scenes × {scene_dur:.1f}s")

    narration = story.get("narration", "")
    headline  = narration.split(".")[0].strip() if narration else story.get("youtube_title", "")

    clips = []
    for i, scene in enumerate(shorts_scenes):
        idx = scene.get("scene_number", i + 1) - 1

        if idx < len(image_paths) and os.path.exists(image_paths[idx]):
            clip = make_animated_portrait(
                image_paths[idx], scene_dur,
                scene_index=i, headline=headline,
                canvas_w=SW, canvas_h=SH,
            )
            logger.info(f"Scene {i+1}: animated portrait")
        else:
            blank = np.zeros((SH, SW, 3), dtype=np.uint8)
            clip  = VideoClip(lambda t: blank, duration=scene_dur).with_fps(FPS)

        adj_chunks = []
        scene_start = i * scene_dur
        for c in caption_chunks:
            if c["chunk_end"] < scene_start or c["chunk_start"] > scene_start + scene_dur:
                continue
            adj_chunks.append({
                **c,
                "chunk_start": c["chunk_start"] - scene_start,
                "chunk_end":   c["chunk_end"] - scene_start,
                "word_timings": [
                    {**wt, "start": wt["start"] - scene_start,
                     "end": wt["end"] - scene_start}
                    for wt in c["word_timings"]
                ],
            })

        captioned = clip.transform(
            lambda gf, t, ch=adj_chunks:
                draw_captions(gf(t), t, ch, SW, SH, font_size=60)
        )
        clips.append(captioned)

    intro  = make_intro_card(story.get("youtube_title", story["title"]))
    shorts = concatenate_videoclips([intro] + clips, method="compose")
    full_dur = shorts.duration

    if music_path and os.path.exists(music_path):
        try:
            music = AudioFileClip(music_path)
            if music.duration < full_dur:
                reps  = int(full_dur / music.duration) + 2
                music = concatenate_audioclips([music] * reps).subclipped(0, full_dur)
            else:
                music = music.subclipped(0, full_dur)
            music       = music.with_volume_scaled(0.10)    # quieter for space ambience
            delayed     = narration_audio.with_start(2.5)
            final_audio = CompositeAudioClip([delayed, music])
        except Exception as e:
            logger.warning(f"Music mix failed: {e}")
            final_audio = narration_audio.with_start(2.5)
    else:
        final_audio = narration_audio.with_start(2.5)

    shorts = shorts.with_audio(final_audio)

    logger.info(f"Rendering Shorts → {output}")
    shorts.write_videofile(
        output, fps=FPS, codec="libx264",
        audio_codec="aac", bitrate="3000k",
        audio_bitrate="128k",
        threads=4, preset="fast", logger=None,
    )
    narration_audio.close()
    shorts.close()
    story["shorts_path"] = output
    logger.info(f"Shorts done: {output}")
    return output


def compose_main_video(story: dict, audio_path: str,
                        music_path: str | None, run_id: str) -> str:
    """Render 16:9 long-form video with space documentary branding."""

    os.makedirs(VIDEO_DIR, exist_ok=True)
    output = os.path.join(VIDEO_DIR, f"{run_id}_final.mp4")

    narration_audio = AudioFileClip(audio_path)
    total_dur       = narration_audio.duration
    caption_chunks  = story.get("caption_chunks", [])
    scenes          = story.get("scenes", [])
    image_paths     = story.get("image_paths", [])
    n_scenes        = max(len(scenes), 1)
    scene_dur       = total_dur / n_scenes

    logger.info(f"Composing 16:9 long-form: {n_scenes} scenes × {scene_dur:.1f}s = {total_dur:.1f}s")

    # Intro card (16:9 space theme)
    intro_img = Image.new("RGB", (W, H), "#000008")
    d = ImageDraw.Draw(intro_img)
    import random
    rng = random.Random(99)
    for _ in range(300):
        x, y = rng.randint(0, W), rng.randint(0, H)
        b = rng.randint(80, 220)
        intro_img.putpixel((x, y), (b, b, b))
    d.rectangle([0, 0, W, 8], fill=ACCENT_COLOR)
    d.rectangle([0, H - 60, W, H], fill=ACCENT_COLOR)
    lf = _font(36)
    d.rectangle([40, 20, 480, 68], fill=ACCENT_COLOR)
    d.text((260, 44), CHANNEL_NAME, font=lf, fill=TEXT_COLOR, anchor="mm")
    d.rectangle([W - 240, 20, W - 40, 68], fill="#CC0000")
    d.text((W - 140, 44), "FACT CHECK", font=_font(30), fill="white", anchor="mm")
    hf = _font(96)
    title = story.get("youtube_title", story.get("title", ""))
    lines = _wrap(title.upper(), max_chars=32)
    lh, y0 = 112, (H - len(lines) * 112) // 2 - 20
    for line in lines:
        for dx, dy in [(-3, 3), (3, 3)]:
            d.text((W // 2 + dx, y0 + dy), line, font=hf, fill="#000020", anchor="mt")
        d.text((W // 2, y0), line, font=hf, fill="white", anchor="mt")
        y0 += lh
    sf = _font(28)
    d.text((W // 2, H - 30), "SUBSCRIBE  •  DAILY FACT CHECKS  •  SPACE FACT CHECK",
           font=sf, fill=TEXT_COLOR, anchor="mm")
    intro_arr = np.array(intro_img)
    intro = VideoClip(lambda t: intro_arr, duration=3.0).with_fps(FPS)

    scene_clips = []
    for i, scene in enumerate(scenes):
        if i < len(image_paths) and os.path.exists(image_paths[i]):
            effect = scene.get("motion_effect", "ken_burns_zoom_in")
            clip   = apply_motion(image_paths[i], scene_dur, effect, canvas_w=W, canvas_h=H)
        else:
            blank = np.zeros((H, W, 3), dtype=np.uint8)
            clip  = VideoClip(lambda t: blank, duration=scene_dur).with_fps(FPS)

        adj_chunks = []
        scene_start = i * scene_dur
        for c in caption_chunks:
            if c["chunk_end"] < scene_start or c["chunk_start"] > scene_start + scene_dur:
                continue
            adj_chunks.append({
                **c,
                "chunk_start": c["chunk_start"] - scene_start,
                "chunk_end":   c["chunk_end"]   - scene_start,
                "word_timings": [
                    {**wt, "start": wt["start"] - scene_start, "end": wt["end"] - scene_start}
                    for wt in c["word_timings"]
                ],
            })
        captioned = clip.transform(
            lambda gf, t, ch=adj_chunks: draw_captions(gf(t), t, ch, W, H)
        )
        scene_clips.append(captioned)

    main_video = concatenate_videoclips(scene_clips, method="compose")
    full_video = concatenate_videoclips([intro, main_video], method="compose")
    full_dur   = intro.duration + total_dur

    if music_path and os.path.exists(music_path):
        try:
            music = AudioFileClip(music_path)
            if music.duration < full_dur:
                reps  = int(full_dur / music.duration) + 2
                music = concatenate_audioclips([music] * reps).subclipped(0, full_dur)
            else:
                music = music.subclipped(0, full_dur)
            music       = music.with_volume_scaled(0.10)
            delayed     = narration_audio.with_start(intro.duration)
            final_audio = CompositeAudioClip([delayed, music])
        except Exception as e:
            logger.warning(f"Music mix failed: {e}")
            final_audio = narration_audio.with_start(intro.duration)
    else:
        final_audio = narration_audio.with_start(intro.duration)

    full_video = full_video.with_audio(final_audio)
    logger.info(f"Rendering 16:9 → {output}")
    full_video.write_videofile(
        output, fps=FPS, codec="libx264",
        audio_codec="aac", bitrate=VIDEO_BITRATE,
        audio_bitrate=AUDIO_BITRATE,
        threads=4, preset="fast", logger=None,
    )
    narration_audio.close()
    full_video.close()
    story["video_path"] = output
    logger.info(f"Long-form done: {output}")
    return output
