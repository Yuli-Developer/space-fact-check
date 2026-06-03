# Space Fact Check (@CosmosChecked) — YouTube Automation

Fully automated YouTube Shorts + long-form channel debunking viral space and AI claims with a calm investigative narrator.

**Content mode**: Live discovery — finds trending claims daily, AI-writes scripts each run.

---

## What It Does

Twice a day (10am + 9pm), the pipeline:
1. Discovers trending space/AI claims from Reddit + NewsAPI
2. Scores them for virality
3. Generates a fact-check script (Gemini 2.5 Pro)
4. Creates 4 AI images matching each scene
5. Records voiceover (Gemini TTS — Charon voice)
6. Composes a 9:16 Shorts video
7. Uploads to YouTube

Long-form (every 3rd day at 11am): produces a "5 Claims Debunked" deep-dive video (~750-900 words, 10 scenes, 16:9).

---

## Pipeline Architecture

```
Discovery (Reddit + NewsAPI)
    └── discovery/space_source.py
            │
            ▼
    Viral Scoring   ── keyword-based, offline
    Script Gen      ── Gemini 2.5 Pro (Shorts) / 2.5 Flash (fallback)
    Images          ── Imagen 3 (cosmic/space aesthetic)
    Voiceover       ── Gemini TTS (Charon voice)
    Video           ── FFmpeg (4 scenes for Shorts, 10 for long-form)
    Upload          ── YouTube Data API v3
```

---

## Cron Schedule

```
0 10 * * *   run_batch.py 1              → 10:00 AM Short
0 21 * * *   run_batch.py 1              → 9:00 PM Short
0 11 * * *   run_longform_rotation.py    → 11:00 AM long-form (Day 0 of 3-day rotation)
```

---

## Tech Stack

| Component | Tool |
|-----------|------|
| Discovery | Reddit API + NewsAPI |
| Script gen | Gemini 2.5 Pro (primary) / 2.5 Flash (fallback) |
| TTS voice | Gemini TTS — **Charon** (calm, authoritative) |
| Fallback TTS | Edge TTS |
| Images | Google Imagen 3 (`imagen3` tier) |
| Visual style | Cosmic / deep space aesthetic |
| Video | MoviePy + FFmpeg |
| Upload | YouTube Data API v3 |

---

## Discovery Queries

Searches for viral claims about:
- NASA discoveries 2026
- James Webb telescope findings
- AI sentience / consciousness
- Alien life
- Space tourism
- Mars missions
- Black hole discoveries

---

## Key Config (.env)

```env
GEMINI_API_KEY=...
YOUTUBE_TOKEN_PATH=token_space.pickle
IMAGE_TIER=imagen3
NARRATOR_STYLE=investigative
MIN_VIRAL_SCORE=2.5
LONGFORM_WORD_COUNT=750-900
```

---

## File Structure

```
space-fact-check/
├── pipeline/
│   └── orchestrator.py        # discover → score → generate → render → publish
├── discovery/
│   └── space_source.py        # Reddit + NewsAPI claim discovery
├── ai/
│   ├── narrative_generator.py # Gemini script generation
│   └── prompt_templates.py    # fact-check style prompts
├── rendering/
│   ├── visual_director.py     # Imagen 3 image generation
│   ├── caption_engine.py      # Gemini TTS + animated captions
│   └── video_composer.py      # final video assembly
├── publishing/
│   └── youtube_publisher.py   # upload + CTR title selection
├── run_batch.py               # cron entry (Shorts)
├── run_longform.py            # cron entry (long-form)
└── .env
```

---

**Repo**: `Yuli-Developer/space-fact-check`
