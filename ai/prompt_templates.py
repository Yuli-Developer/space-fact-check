"""Prompt templates for Space Fact Check — viral claim → real science."""

STYLE_SYSTEM_PROMPTS = {
    "investigative": """You are a science journalist who fact-checks viral space and AI claims.
Tone: Calm authority. You've read the actual papers. You correct the record without being condescending.
Think: a Neil deGrasse Tyson who also has a journalism degree and a YouTube channel.""",

    "deadpan": """You are a deadpan scientist reacting to viral space misinformation.
Tone: Completely calm about absurd headlines. The facts are more interesting than the hype anyway.
Think: a PhD astronomer reading a Daily Mail headline aloud.""",

    "cosmic_wonder": """You are a science communicator who shows that reality is more mind-blowing than the clickbait.
Tone: Enthusiastic but precise. The actual science is better than the myth.
Think: Carl Sagan energy meets MrBeast pacing.""",

    "skeptic": """You are a professional scientific skeptic who tears apart viral space and AI claims.
Tone: Methodical, slightly exasperated, but fair. Follow the evidence.
Think: a science-based fact-checker who has seen every "alien discovered" headline for 20 years.""",

    "breaking_news": """You are a breaking news anchor covering science corrections in real-time.
Tone: Urgent, clear, punchy. The correction IS the news.
Think: a CNN anchor who actually understands astrophysics.""",
}

SHORTS_SCRIPT_PROMPT = """
{system_prompt}

Fact-check this viral space or AI claim for a YouTube Shorts video.
Structure: CLAIM (what everyone thinks) → REALITY (what's actually true) → VERDICT (the surprising twist).
Max 55 seconds. Max 120 words. Hook in first 3 words. Make the REALITY more mind-blowing than the CLAIM.

Story headline: {title}
Details: {summary}
Source: {url}
Narrator style: {style}

Return ONLY valid JSON (no markdown):
{{
  "youtube_title": "<punchy title under 55 chars — e.g. 'NASA Found Life? The REAL Story' or 'This AI Claim Is Totally Wrong'>",
  "hook": "<first sentence, 10 words max — MUST open with a shocking specific fact or number. Example: 'This galaxy is 13 billion years old — and it shouldn't exist.' or 'NASA just found something that breaks physics.' NEVER start with 'So', 'Did you know', 'Today', or 'Have you heard'.>",
  "narration": "<STRICT max 120 words. FIRST WORDS must be a mind-blowing specific fact/number/discovery. Structure: 1) shocking specific fact (10-15 words) 2) 'But here is what actually happened' (50-60 words of real science) 3) 'The verdict:' (20-30 words of surprising truth more mind-blowing than the claim). Fast pace. Short sentences. No filler intros.>",
  "claim_statement": "<the viral/wrong version in one sentence>",
  "reality_statement": "<the actual scientific truth in one sentence>",
  "verdict": "<why the truth is more interesting than the myth>",
  "title_variants": [
    "<title 1 — 'They Said X. The Truth Is Wilder'>",
    "<title 2 — 'The [X] Claim Is Wrong. Here Is Why'>",
    "<title 3 — 'NASA/Scientists Actually Found THIS'>",
    "<title 4 — curiosity/mystery angle>"
  ],
  "characters": "<visual: space imagery, scientists, telescopes, data screens — no human faces>",
  "scenes": [
    {{
      "scene_number": 1,
      "narration_segment": "<words for scene 1 — the viral claim>",
      "storyboard_description": "<VERTICAL 9:16 portrait. Dark space aesthetic. Show: dramatic space imagery representing the viral claim. Deep blacks, nebula colors. Cinematic cosmic scale.>",
      "motion_effect": "<ken_burns_zoom_in|ken_burns_zoom_out|pan_left|pan_right>",
      "search_keywords": ["space", "science", "cosmos"]
    }},
    {{
      "scene_number": 2,
      "narration_segment": "<words for scene 2 — the reality>",
      "storyboard_description": "<VERTICAL 9:16. Scientific reality visual. Telescope data, star charts, mission control. Same dark cosmic aesthetic. More clinical/precise than scene 1.>",
      "motion_effect": "pan_right",
      "search_keywords": ["science", "telescope", "data"]
    }},
    {{
      "scene_number": 3,
      "narration_segment": "<words for scene 3 — more reality / context>",
      "storyboard_description": "<VERTICAL 9:16. Scale of universe or AI concept. Dramatic depth of field. Make the real thing look bigger and more awe-inspiring than the myth.>",
      "motion_effect": "ken_burns_zoom_out",
      "search_keywords": ["universe", "cosmos", "reality"]
    }},
    {{
      "scene_number": 4,
      "narration_segment": "<words for scene 4 — the verdict>",
      "storyboard_description": "<VERTICAL 9:16. The mind-blowing real image or concept. Deepest space or most dramatic AI visualization. Leave the viewer with genuine awe.>",
      "motion_effect": "ken_burns_zoom_in",
      "search_keywords": ["discovery", "truth", "science"]
    }}
  ],
  "tags": ["space", "science", "factcheck", "nasa", "astronomy", "sciencefacts", "didyouknow"],
  "description_hook": "<2 lines that make people need to watch: line 1 = the wrong claim, line 2 = tease the real truth>"
}}

Requirements:
- Exactly 4 scenes
- Total narration MUST be under 120 words
- The REALITY must be more interesting than the CLAIM — reality always wins
- Never mock believers — treat the claim respectfully, let the science do the work
- Tags must include: space, factcheck, nasa, science, shorts
"""

LONGFORM_SCRIPT_PROMPT = """
{system_prompt}

Create a 8-10 minute YouTube video: "5 Viral Space & AI Claims — Fact Checked"
Use this story as the anchor/first claim: {title}
Details: {summary}
Source: {url}
Narrator style: {style}

Structure: Hook intro (~70 words) + 5 fact-check segments (~130-150 words each) + Outro (~60 words)
Total: {word_count} words. {num_scenes} scenes for the main video (HORIZONTAL 16:9).

Return ONLY valid JSON (no markdown):
{{
  "youtube_title": "<punchy title under 60 chars — e.g. '5 Space Claims Scientists Just Debunked'>",
  "hook": "<first 2 sentences — MUST open with a specific mind-blowing number or fact. Example: '5 things you believe about space are completely wrong. And number 3 will break your brain.' NEVER start with 'Today', 'Welcome', 'So', or 'Have you ever'.>",
  "narration": "<full {word_count} word narration. Intro → Claim 1 (anchor story) → Claim 2 → Claim 3 → Claim 4 → Claim 5 → Outro. Each claim: state it → debunk it → verdict twist.>",
  "shorts_narration": "<60-second version under 120 words — just the most shocking single claim>",
  "claim_statement": "<the most shocking claim in one sentence>",
  "reality_statement": "<the most surprising real truth in one sentence>",
  "verdict": "<the most mind-blowing verdict>",
  "title_variants": [
    "<variant 1 — '5 Space Lies You Still Believe'>",
    "<variant 2 — 'NASA Never Said That. Here Is What They Said'>",
    "<variant 3 — 'Scientists Are Tired of These Space Myths'>",
    "<variant 4 — curiosity angle>"
  ],
  "characters": "space imagery, telescopes, data screens, spacecraft — no human faces",
  "scenes": [
    {{
      "scene_number": 1,
      "narration_segment": "<intro narration for this scene>",
      "storyboard_description": "<HORIZONTAL 16:9 landscape. Deep space documentary aesthetic. Wide cinematic shot of cosmos or spacecraft. Dark space, nebula colors. Epic scale.>",
      "motion_effect": "ken_burns_zoom_in",
      "search_keywords": ["space", "cosmos", "universe"]
    }}
  ],
  "shorts_scenes": [
    {{
      "scene_number": 1,
      "narration_segment": "<words for shorts scene 1>",
      "storyboard_description": "<VERTICAL 9:16 portrait. Dark space aesthetic.>",
      "motion_effect": "ken_burns_zoom_in",
      "search_keywords": ["space", "science"]
    }}
  ],
  "tags": ["space", "science", "factcheck", "nasa", "astronomy", "debunked", "spacemyths", "sciencefacts"],
  "description_hook": "<2 lines: line 1 = the shocking claim, line 2 = tease the truth>"
}}

Requirements:
- Exactly {num_scenes} scenes (HORIZONTAL 16:9 landscape framing for main video)
- Exactly 4 shorts_scenes (VERTICAL 9:16 portrait framing)
- Total narration must be {word_count} words
- Reality must always be more mind-blowing than the claim
- Never mock believers — let the science do the work
"""

FEEDBACK_PROMPT = """
You are analyzing YouTube Shorts performance data for a space fact-check channel.
Based on this analytics data, suggest improvements to maximize views and retention.

Recent video analytics:
{analytics_data}

Historical averages:
{historical_summary}

Return ONLY valid JSON (no markdown):
{{
  "best_style": "<which narrator style is performing best: investigative|deadpan|cosmic_wonder|skeptic|breaking_news>",
  "style_reasoning": "<why this style works>",
  "thumbnail_insights": ["<insight 1>", "<insight 2>"],
  "title_patterns": ["<pattern that works>", "<pattern to avoid>"],
  "next_content_focus": "<what type of claims to focus on: alien|ai|mars|physics|nasa>",
  "prompt_improvements": {{
    "narration_tweak": "<specific tweak to improve retention>",
    "title_tweak": "<specific title format that gets more clicks>"
  }}
}}
"""
