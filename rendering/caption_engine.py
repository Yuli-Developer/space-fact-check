"""
Caption Engine — Gemini TTS (primary) + Edge TTS fallback.
Animated word-by-word captions for Shorts.
"""
import re
import os
import wave
import struct
import base64
import asyncio
import logging
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import AudioFileClip
from config.settings import AUDIO_DIR, GEMINI_API_KEY, GEMINI_TTS_MODEL
from config.settings import SHORTS_WIDTH as W, SHORTS_HEIGHT as H

logger = logging.getLogger(__name__)

VOICE_EDGE  = "en-US-GuyNeural"       # Edge TTS fallback — authoritative male
VOICE_GEMINI = "Charon"               # Gemini TTS — deep, authoritative space voice
CAPTION_Y_RATIO = 0.78
FONT_SIZE       = 72
GAP             = 20


def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in [
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


# ── Gemini TTS ─────────────────────────────────────────────────────────────

def _generate_gemini_tts(text: str, wav_path: str) -> bool:
    """Generate voiceover using Gemini TTS. Returns True on success."""
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model=GEMINI_TTS_MODEL,
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=VOICE_GEMINI,
                        )
                    )
                ),
            ),
        )

        # Extract PCM audio bytes
        part = response.candidates[0].content.parts[0]
        audio_data = part.inline_data.data

        # inline_data.data may be bytes or base64 string depending on SDK version
        if isinstance(audio_data, str):
            pcm_bytes = base64.b64decode(audio_data)
        else:
            pcm_bytes = audio_data

        # Save as WAV (Gemini TTS outputs 16-bit PCM at 24kHz mono)
        with wave.open(wav_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(24000)
            wf.writeframes(pcm_bytes)

        size = os.path.getsize(wav_path)
        if size < 1000:
            logger.warning(f"Gemini TTS output too small: {size} bytes")
            return False

        logger.info(f"Gemini TTS: saved {wav_path} ({size//1024}KB)")
        return True

    except Exception as e:
        logger.warning(f"Gemini TTS failed: {e}")
        return False


# ── Edge TTS fallback ──────────────────────────────────────────────────────

async def _edge_tts_async(text: str, mp3_path: str):
    import edge_tts
    comm = edge_tts.Communicate(text, voice=VOICE_EDGE)
    with open(mp3_path, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])


def _generate_edge_tts(text: str, path: str) -> str:
    asyncio.run(_edge_tts_async(text, path))
    return path


# ── Public voiceover generator ─────────────────────────────────────────────

def generate_voiceover(narration: str, run_id: str, suffix: str = "") -> str:
    os.makedirs(AUDIO_DIR, exist_ok=True)

    wav_path = os.path.join(AUDIO_DIR, f"{run_id}_narration{suffix}.wav")
    mp3_path = os.path.join(AUDIO_DIR, f"{run_id}_narration{suffix}.mp3")

    logger.info(f"Generating voiceover{suffix}...")

    # Try Gemini TTS first
    if _generate_gemini_tts(narration, wav_path):
        return wav_path

    # Fallback to Edge TTS
    logger.info("Falling back to Edge TTS")
    return _generate_edge_tts(narration, mp3_path)


# ── Word timings ───────────────────────────────────────────────────────────

def _word_weight(w: str) -> float:
    base = max(len(w.rstrip(".,!?;:")), 1)
    if w.rstrip().endswith((".", "!", "?")):
        base += 3
    elif w.rstrip().endswith((",", ";")):
        base += 1.5
    return float(base)


def estimate_timings(text: str, total_duration: float) -> list[dict]:
    words   = [w for w in re.split(r"\s+", text.strip()) if w]
    weights = [_word_weight(w) for w in words]
    total_w = sum(weights)
    timings = []
    t = 0.2
    for word, weight in zip(words, weights):
        dur = (weight / total_w) * (total_duration - 0.4)
        timings.append({
            "word":  word.rstrip(".,!?;:"),
            "start": round(t, 3),
            "end":   round(t + dur, 3),
        })
        t += dur
    return timings


def build_caption_chunks(timings: list[dict], words_per_chunk: int = 3) -> list[dict]:
    chunks = []
    i = 0
    while i < len(timings):
        chunk = timings[i: i + words_per_chunk]
        chunks.append({
            "words":        [w["word"] for w in chunk],
            "chunk_start":  chunk[0]["start"],
            "chunk_end":    chunk[-1]["end"],
            "word_timings": chunk,
        })
        i += words_per_chunk
    return chunks


# ── Caption rendering ──────────────────────────────────────────────────────

def draw_captions(frame: np.ndarray, t: float,
                   chunks: list[dict],
                   canvas_w: int = W, canvas_h: int = H,
                   font_size: int = FONT_SIZE) -> np.ndarray:
    img = Image.fromarray(frame)
    active_chunk, active_word_idx = None, 0

    for chunk in chunks:
        if chunk["chunk_start"] <= t <= chunk["chunk_end"] + 0.25:
            active_chunk = chunk
            for wi, wt in enumerate(chunk["word_timings"]):
                if wt["start"] <= t <= wt["end"] + 0.12:
                    active_word_idx = wi
                    break
            else:
                active_word_idx = len(chunk["words"]) - 1
            break

    if not active_chunk:
        return np.array(img)

    overlay = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    grad_y = int(canvas_h * 0.62)
    for row in range(grad_y, canvas_h):
        alpha = int(190 * (row - grad_y) / (canvas_h - grad_y))
        od.rectangle([0, row, canvas_w, row + 1], fill=(0, 0, 10, alpha))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    words  = active_chunk["words"]
    cf     = _font(font_size)
    sizes  = [draw.textbbox((0, 0), w, font=cf) for w in words]
    widths = [b[2] - b[0] for b in sizes]
    total_w = sum(widths) + GAP * (len(words) - 1)
    x = (canvas_w - total_w) // 2
    y = int(canvas_h * CAPTION_Y_RATIO)

    stroke = 5
    for wi, (word, ww) in enumerate(zip(words, widths)):
        # Active word: bright cyan (space theme). Others: white.
        color = "#00E5FF" if wi == active_word_idx else "#FFFFFF"
        for dx in (-stroke, 0, stroke):
            for dy in (-stroke, 0, stroke):
                if dx or dy:
                    draw.text((x + dx, y + dy), word, font=cf, fill="#000010")
        draw.text((x, y), word, font=cf, fill=color)
        x += ww + GAP

    return np.array(img)


# ── Full voiceover pipeline ────────────────────────────────────────────────

def prepare_voiceover(narration: str, run_id: str,
                       suffix: str = "") -> tuple[str, list[dict], list[dict]]:
    audio_path = generate_voiceover(narration, run_id, suffix)
    clip       = AudioFileClip(audio_path)
    duration   = clip.duration
    clip.close()
    logger.info(f"Audio duration: {duration:.1f}s")

    timings = estimate_timings(narration, duration)
    chunks  = build_caption_chunks(timings, words_per_chunk=3)
    return audio_path, timings, chunks
