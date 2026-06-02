"""Audio Engine — space/cosmic background music."""
import os
import math
import wave
import struct
import logging
import requests

logger = logging.getLogger(__name__)

MUSIC_DIR = "assets/music"

TRACKS = [
    {"name": "space_ambient", "url": "https://archive.org/download/Kevin_MacLeod_Incompetech/Kevin_MacLeod_-_Cipher.mp3"},
    {"name": "cinematic",     "url": "https://archive.org/download/kevin-macleod-carefree/Carefree.mp3"},
]

DEFAULT_TRACK = "cinematic_tensions.mp3"


def _download(url: str, path: str) -> bool:
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"}, stream=True)
        r.raise_for_status()
        with open(path, "wb") as f:
            for chunk in r.iter_content(32768):
                f.write(chunk)
        return os.path.getsize(path) > 5000
    except Exception as e:
        logger.warning(f"Music download failed: {e}")
        if os.path.exists(path):
            os.remove(path)
        return False


def _generate_space_ambient(path: str, duration: float = 60.0) -> str:
    """Generate a minimal space ambient tone as WAV fallback."""
    sr    = 44100
    n     = int(duration * sr)
    audio = [0.0] * n

    # Low drone + gentle pulse
    freqs  = [55.0, 110.0, 165.0]
    amps   = [0.15, 0.06, 0.03]
    for i in range(n):
        t   = i / sr
        val = sum(a * math.sin(2 * math.pi * f * t) for f, a in zip(freqs, amps))
        # Slow pulse
        val *= 0.7 + 0.3 * math.sin(2 * math.pi * 0.08 * t)
        audio[i] = val

    wav_path = path.replace(".mp3", ".wav")
    with wave.open(wav_path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        for s in audio:
            wf.writeframes(struct.pack("<h", max(-32767, min(32767, int(s * 32767)))))

    logger.info(f"Generated space ambient: {wav_path}")
    return wav_path


def get_music_track() -> str | None:
    os.makedirs(MUSIC_DIR, exist_ok=True)

    default_path = os.path.join(MUSIC_DIR, DEFAULT_TRACK)
    if os.path.exists(default_path) and os.path.getsize(default_path) > 5000:
        logger.info(f"Using music: {DEFAULT_TRACK}")
        return default_path

    for track in TRACKS:
        path = os.path.join(MUSIC_DIR, f"{track['name']}.mp3")
        if os.path.exists(path) and os.path.getsize(path) > 5000:
            return path
        if _download(track["url"], path):
            return path

    fallback = os.path.join(MUSIC_DIR, "space_ambient.wav")
    return _generate_space_ambient(fallback)
