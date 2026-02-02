# Agent Guide: UGC Ad Factory (Shorts Factory)

This document guides AI agents working on the UGC Ad Factory system. Follow these patterns for consistent, high-quality video production.

## Product Verticals

The system supports two primary verticals:

| Vertical | Description | Style Reference |
|----------|-------------|-----------------|
| **UGC Ads** (Primary) | High-production ads for products/services with company research, hook angles, testimonials | Ali Abdaal, Varun Mayya |
| **Content Shorts** | News commentary, explainer shorts with evidence screenshots | Varun Mayya, Johnny Harris |

Both share: avatar talking heads, evidence screenshots, word-by-word captions, 9:16 vertical format.

**UGC Ads add:**
- Company research phase (Exa.ai)
- Hook angles for ads
- Testimonial themes
- Value propositions
- Target audience analysis

## Core Principle: JSON First

Everything is JSON. Templates, scenes, evidence - all JSON.

Why? So agents can:
1. **Read** existing scenes and understand structure
2. **Generate** new scenes that match the schema
3. **Validate** outputs against known patterns
4. **Learn** from rated examples

## Project Workflow

### Stage 1: Research → Evidence

**Input:** `projects/{id}/input/`
- `prompt.md` - Topic and angle
- `urls.json` - Sources to investigate
- `research/` - Any provided docs/screenshots

**Output:** `projects/{id}/evidence/`
- Captured screenshots with manifest

**Agent:** Witness (Browserbase stealth browser)

```json
// evidence/manifest.json
{
  "captures": [
    {
      "id": "techspot_001",
      "url": "https://techspot.com/article",
      "description": "Peptides article headline",
      "files": {
        "element": "techspot_001_element.png",
        "context": "techspot_001_context.png",
        "fullpage": "techspot_001_fullpage.png"
      },
      "anchor_text": "Chinese Peptides Are Taking Over"
    }
  ]
}
```

## CLI Architecture

The system is driven by the CLI at `src/cli/main.py`. Two primary workflows exist:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         CLI COMMAND STRUCTURE                                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  VARUN MAYYA SHORTS (Primary)              EXPLAINER VIDEOS (Secondary)         │
│  ─────────────────────────────             ────────────────────────────         │
│                                                                                 │
│  python -m src.cli director <project>      python -m src.cli generate <project>│
│    ├── research    (Exa.ai)                  ├── script                         │
│    ├── summarize   (LLM insights)            ├── narration                      │
│    ├── draft       (LLM → script.json)       ├── scenes                         │
│    ├── voiceover   (ElevenLabs)              ├── voiceover                      │
│    ├── avatar      (HeyGen)                  ├── storyboard                     │
│    ├── background  (fal.ai)                  └── render                         │
│    ├── assemble    (update paths)                                               │
│    ├── status      (show state)            UTILITIES                            │
│    ├── review      (approve assets)        ─────────                            │
│    └── finalize    (render-ready)          feedback, factcheck, sound, music    │
│                                                                                 │
│  python -m src.cli render <project> --varun                                     │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Director Workflow (Varun Mayya Shorts)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    DIRECTOR PIPELINE: projects/{id}/                            │
└─────────────────────────────────────────────────────────────────────────────────┘

PHASE 0: RESEARCH                              PHASE 0.1: SUMMARIZE
┌─────────────────────────┐                    ┌─────────────────────────┐
│ director research       │                    │ director summarize      │
│ --company "exa.ai"      │                    │                         │
├─────────────────────────┤                    ├─────────────────────────┤
│ Tool: Exa.ai API        │                    │ Tool: OpenAI LLM        │
│ Output:                 │──────────────────▶ │ Input: research.json    │
│   input/research.json   │                    │ Output:                 │
│   • company info        │                    │   input/research-       │
│   • founders            │                    │   display.json          │
│   • competitors         │                    │   • hook_angles[]       │
│   • news articles       │                    │   • testimonial_themes[]│
│   • social profiles     │                    │   • unique_value_props[]│
└─────────────────────────┘                    └──────────┬──────────────┘
                                                          │
                                                          ▼
PHASE 1: DRAFTING                              ┌─────────────────────────┐
┌─────────────────────────┐                    │ director draft          │
│ config.json (created)   │                    │ --topic "..." --dur 30  │
│   • id, title, type     │◄───────────────────├─────────────────────────┤
│   • video: 1080x1920    │                    │ Tool: OpenAI LLM        │
│   • tts.voice_id        │                    │ Model: gpt-4o-mini      │
│   • avatar.avatar_id    │                    │ Prompts:                │
└─────────────────────────┘                    │   SHORT_SYSTEM_PROMPT   │
                                               │   SHORT_USER_PROMPT_    │
┌─────────────────────────┐                    │   TEMPLATE              │
│ .director_state.json    │◄───────────────────│ Output:                 │
│   • phase tracking      │                    │   script/script.json    │
│   • asset status        │                    │   • scenes[].template   │
│   • history             │                    │   • scenes[].audio.text │
└─────────────────────────┘                    │   • assets_needed{}     │
                                               └──────────┬──────────────┘
                                                          │
            ┌─────────────────────────────────────────────┼─────────────────┐
            │                                             │                 │
            ▼                                             ▼                 ▼
PHASE 2: VOICEOVER                   PHASE 3: AVATAR                PHASE 4: BACKGROUND
┌─────────────────────────┐          ┌─────────────────────────┐    ┌─────────────────────────┐
│ director voiceover      │          │ director avatar         │    │ director background     │
├─────────────────────────┤          ├─────────────────────────┤    ├─────────────────────────┤
│ Tool: ElevenLabs TTS    │          │ Tools:                  │    │ Tool: fal.ai API        │
│ Input:                  │          │   Supabase (upload)     │    │ Models:                 │
│   script.json scenes    │          │   HeyGen API (lipsync)  │    │   Kling 1.5 Pro         │
│   config.tts.voice_id   │──────────│   ffmpeg (crop)         │    │   Google Veo3           │
│ Output:                 │          │ Input:                  │    │ Input:                  │
│   avatar/               │          │   avatar/*_audio.mp3    │    │   scene descriptions    │
│     scene_001_audio.mp3 │          │   config.avatar_id      │    │   from script.json      │
│     scene_002_audio.mp3 │          │ Output:                 │    │ Output:                 │
│   voiceover/            │          │   avatar/               │    │   backgrounds/          │
│     manifest.json       │          │     scene_001_16x9.mp4  │    │     scene_001.mp4       │
│     (word_timestamps)   │          │     scene_001_bottom.mp4│    │     scene_002.mp4       │
└─────────────────────────┘          └─────────────────────────┘    └─────────────────────────┘
            │                                    │                           │
            └────────────────────────────────────┼───────────────────────────┘
                                                 │
                                                 ▼
                              PHASE 5: ASSEMBLE + RENDER
                              ┌─────────────────────────────────────────────┐
                              │ director assemble                           │
                              ├─────────────────────────────────────────────┤
                              │ Updates script.json with actual asset paths │
                              │   • scenes[].audio.file                     │
                              │   • scenes[].audio.word_timestamps          │
                              │   • scenes[].background.src                 │
                              │   • scenes[].avatar.src                     │
                              └──────────────────────┬──────────────────────┘
                                                     │
                                                     ▼
                              ┌─────────────────────────────────────────────┐
                              │ render <project> --varun                    │
                              ├─────────────────────────────────────────────┤
                              │ Tool: Remotion                              │
                              │ Input: script/script.json                   │
                              │ Output: output/short.mp4                    │
                              └─────────────────────────────────────────────┘
```

## Project Directory Structure

```
projects/{id}/
├── config.json              # Project settings (dimensions, fps, voice_id, avatar_id)
├── .director_state.json     # State machine tracking phases and assets (lean - no script duplication)
├── input/
│   ├── research.json        # Company research from Exa.ai
│   └── research-display.json # LLM-summarized insights for ads
├── script/
│   └── script.json          # Main scene definitions (template, audio, background, avatar) - SINGLE SOURCE OF TRUTH
├── voiceover/
│   └── manifest.json        # Word timestamps per scene
├── avatar/
│   ├── scene_001_audio.mp3  # Audio for lip-sync
│   ├── scene_001_16x9.mp4   # HeyGen output (16:9)
│   └── scene_001_bottom.mp4 # Cropped for SplitProof template
├── backgrounds/
│   └── scene_001.mp4        # AI-generated or stock video
├── evidence/
│   ├── manifest.json        # Screenshot metadata
│   └── screenshots/         # Captured web screenshots
└── output/
    └── short.mp4            # Final rendered video
```

### Director State File (Lean Design)

`.director_state.json` tracks **only** state - no content duplication:

```json
{
  "project_id": "ad-for-chronic-life",
  "project_dir": "projects/ad-for-chronic-life",
  "phase": "awaiting_capture",
  "phase_started_at": "2026-01-25T21:31:02",
  "topic": "Clue - Track chronic illness symptoms...",
  "duration_seconds": 30,
  "evidence_urls": [],
  "assets": [
    { "id": "chronic_illness_intro.mp4", "asset_type": "background", "status": "pending", "file_path": null, "error": null },
    { "id": "scene_001.mp4", "asset_type": "avatar", "status": "complete", "file_path": "avatar/scene_001.mp4", "error": null }
  ],
  "audio_file": null,
  "error_message": null,
  "history": [
    { "from": "idle", "to": "drafting", "reason": "Topic: ...", "timestamp": "..." },
    { "from": "drafting", "to": "awaiting_capture", "reason": "Script drafted", "timestamp": "..." }
  ],
  "created_at": "...",
  "updated_at": "..."
}
```

**Key design principles:**
- Script content lives in `script/script.json` only (use `state.get_script()` to load)
- Asset metadata (description, prompts) lives in `script/script.json.assets_needed`
- State file only tracks asset **status** (pending/captured/approved/failed + file_path)

## State Machine Phases

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DIRECTOR STATE MACHINE                              │
│                      .director_state.json                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   DRAFTING ──▶ AWAITING_CAPTURE ──▶ REVIEWING ──▶ AWAITING_AUDIO           │
│       │              │                  │              │                    │
│       │              │                  │              ▼                    │
│       │              │                  │         AWAITING_AVATAR           │
│       │              │                  │              │                    │
│       │              │                  │              ▼                    │
│       │              │                  │         READY_FOR_RENDER          │
│       │              │                  │              │                    │
│       ▼              ▼                  ▼              ▼                    │
│   [ERROR STATE - can occur at any phase]                                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```




### Stage 2: Evidence → Script

**Input:** Evidence manifest + prompt
**Output:** `projects/{id}/script/script.json`

**Agent:** Director

The script MUST reference existing evidence files. Never hallucinate evidence.

```json
// script/script.json
{
  "id": "peptides",
  "scenes": [
    {
      "id": "scene_001",
      "template": "SplitProof",
      "evidence_ref": "techspot_001",  // References manifest
      "voiceover": "Chinese peptides are taking over Silicon Valley"
    }
  ]
}
```

### Stage 3: Script → Audio

**Input:** script.json
**Output:** `projects/{id}/audio/`
- `voiceover.mp3`
- `timestamps.json` (word-level timing)

**Tool:** ElevenLabs API

### Stage 4: Audio → Avatar

**Input:** Audio file + timestamps
**Output:** `projects/{id}/avatar/`
- Per-scene lip-synced clips

**Tool:** HeyGen API

### Stage 5: All Assets → Render

**Input:** script.json + audio + avatar + evidence
**Output:** `projects/{id}/output/short.mp4`

**Tool:** Remotion

## Template Selection Guide

When generating script.json, choose templates based on content:

| Content Type | Template | When to Use |
|-------------|----------|-------------|
| Claim + Proof | `SplitProof` | Showing evidence while avatar explains |
| Key Quote | `TextOverProof` | Highlighting text from source |
| Pure Talking | `FullAvatar` | Opinion, transitions, no evidence needed |
| Document/Tweet | `ProofOnly` | Evidence speaks for itself |
| Statement | `TextCard` | Dramatic pause, no visual needed |

### Template Decision Tree

```
Does this scene show evidence?
├─ YES: Is avatar needed?
│   ├─ YES → SplitProof (evidence top, avatar bottom)
│   └─ NO: Is there key text to highlight?
│       ├─ YES → TextOverProof (headline over image)
│       └─ NO → ProofOnly (full screenshot)
└─ NO: Is avatar talking?
    ├─ YES → FullAvatar (talking head)
    └─ NO → TextCard (text on gradient)
```

## Schema Reference

### Scene Object (Minimal)

```json
{
  "id": "scene_001",           // Unique identifier
  "template": "SplitProof",    // One of 5 templates
  "start_seconds": 0,          // Start time in video
  "end_seconds": 4.5,          // End time
  "audio": {
    "text": "Voiceover text",
    "file": "audio/voiceover.mp3",
    "start_seconds": 0,        // Audio offset
    "word_timestamps": []      // Generated by TTS
  },
  "background": {
    "type": "screenshot",      // screenshot | ai_video | gradient
    "src": "evidence/file.png"
  },
  "avatar": {
    "visible": true,
    "position": "bottom",      // full | bottom | pip_corner | off
    "src": "avatar/scene_001.mp4"
  },
  "text": {
    "headline": "Optional headline",
    "caption_style": "word_by_word"  // or "sentence"
  }
}
```

### Background Types

```json
// Screenshot from evidence
{ "type": "screenshot", "src": "evidence/file.png" }

// AI-generated video
{ "type": "ai_video", "src": "backgrounds/scene_001.mp4" }

// Gradient (no image)
{ "type": "gradient", "colors": ["#0a0a0f", "#1a1a2e"] }

// Stock footage
{ "type": "stock", "src": "backgrounds/tech_bg.mp4" }
```

### Avatar Positions

```json
// Full screen talking head
{ "visible": true, "position": "full" }

// Bottom 40% of screen (for SplitProof)
{ "visible": true, "position": "bottom" }

// Small corner picture-in-picture
{ "visible": true, "position": "pip_corner" }

// No avatar
{ "visible": false }
```

## Human-in-the-Loop Checkpoints

**ALWAYS** pause for human review at these stages:

1. **After Evidence Capture** - Did we get the right screenshots?
2. **After Script Generation** - Is the narrative correct?
3. **After Audio Generation** - Does it sound right?
4. **After First Scene Render** - Is the vibe correct?
5. **After Full Render** - Final approval

## Scene-by-Scene Iteration

The workflow is iterative:

```
Scene 1: Perfect it
    ↓
Templates/styles locked
    ↓
Scene 2: Faster (reuse learnings)
    ↓
Scene 3: Even faster
    ↓
...
    ↓
Full video assembled
```

Benefits:
- Scene 1 catches template bugs
- Style/vibe consistency enforced early
- Each scene benefits from prior learnings

## File Naming Conventions

```
evidence/
  {source}_{number}.png           # techspot_001.png
  {source}_{number}_element.png   # Cropped element
  {source}_{number}_context.png   # With context
  {source}_{number}_fullpage.png  # Full page

avatar/
  scene_{number}.mp4              # scene_001.mp4

backgrounds/
  scene_{number}.mp4              # AI/stock video

audio/
  voiceover.mp3                   # Full audio
  timestamps.json                 # Word timing
```

## Quality Checklist

Before marking a scene complete:

- [ ] Evidence file exists and is referenced correctly
- [ ] Template matches content type
- [ ] Avatar position makes sense for template
- [ ] Text is readable (not too small)
- [ ] Timing feels natural (1-10 seconds per scene)
- [ ] Captions sync with audio

## Ratings Schema

After render, create `output/ratings.json`:

```json
{
  "project_id": "peptides",
  "overall_rating": 7,
  "scenes": [
    {
      "id": "scene_001",
      "rating": 8,
      "template_worked": true,
      "notes": "Strong hook, good evidence"
    },
    {
      "id": "scene_002",
      "rating": 5,
      "template_worked": false,
      "notes": "TextOverProof - text overlapped image badly"
    }
  ],
  "learnings": [
    "SplitProof works best for article screenshots",
    "Avoid TextOverProof for busy images"
  ]
}
```

## Debugging

### Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| Evidence not found | Wrong path in script | Check manifest.json paths |
| Avatar not syncing | Timing mismatch | Regenerate with correct timestamps |
| Text unreadable | Wrong template | Switch to SplitProof or TextCard |
| Scene too short | Audio too fast | Adjust TTS speed or add pause |

### Validation

Before render, validate script.json:

1. All `evidence_ref` values exist in manifest
2. All `src` paths point to real files
3. `start_seconds` < `end_seconds` for each scene
4. No gaps between scenes
5. Total duration matches config

## API Keys Required

```
ELEVENLABS_API_KEY   - TTS generation
HEYGEN_API_KEY       - Avatar lip-sync
BROWSERBASE_API_KEY  - Stealth screenshot capture
EXA_API_KEY          - URL research/discovery
OPENAI_API_KEY       - Script generation LLM
ANTHROPIC_API_KEY    - Vision analysis, ClaudeCode provider
```

## LLM Pipeline Architecture

This section documents all LLM calls in the video generation pipeline.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         LLM CALLS IN DIRECTOR WORKFLOW                          │
└─────────────────────────────────────────────────────────────────────────────────┘

PHASE 0.1: RESEARCH SUMMARIZATION              PHASE 1: SCRIPT DRAFTING
┌──────────────────────────────────────┐       ┌──────────────────────────────────────┐
│ LLM CALL: Research Summarizer        │       │ LLM CALL: Script Generator (Draft)   │
│ ─────────────────────────────────────│       │ ─────────────────────────────────────│
│ Provider: OpenAI API (direct)        │       │ Provider: OpenAI API (direct)        │
│ Model: gpt-4o                        │       │ Model: gpt-4o-mini (default)         │
│ File: src/company_researcher/        │       │ File: src/cli/main.py                │
│       summarizer.py                  │       │       _director_draft()              │
│ Context:                             │       │ Prompts:                             │
│   • research.json (full company)     │       │   • SHORT_SYSTEM_PROMPT              │
│ Output: research-display.json        │       │   • SHORT_USER_PROMPT_TEMPLATE       │
│   • hook_angles[]                    │       │   (from src/prompts/director_short)  │
│   • testimonial_themes[]             │       │ Context:                             │
│   • unique_value_props[]             │       │   • topic, duration, evidence_urls   │
└──────────────────────────────────────┘       │ Output: script/script.json           │
                                               │   • scenes[].template                │
                                               │   • scenes[].audio.text              │
                                               │   • assets_needed{}                  │
                                               │ Response format: JSON                │
                                               └──────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                      LLM CALLS IN EVIDENCE CAPTURE                              │
└─────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────┐    ┌──────────────────────────────────┐
│ LLM CALL: Anchor Picker (Witness)    │    │ LLM CALL: Vision Analysis        │
│ ─────────────────────────────────────│    │ ─────────────────────────────────│
│ Provider: OpenAI API (AsyncOpenAI)   │    │ Provider: Anthropic API (direct) │
│ Model: gpt-4o-mini                   │    │ Model: claude-sonnet-4-20250514  │
│ File: src/agents/witness.py          │    │ File: src/evidence/vision.py     │
│ Prompt: ANCHOR_PICKER_PROMPT         │    │ Context:                         │
│   (from src/prompts/anchor_picker)   │    │   • Base64 screenshot image      │
│ Context:                             │    │   • Anchor text to find          │
│   • Element description from script  │    │   • Expected content description │
│   • Real text candidates from page   │    │ Output: VariantReview            │
│ Output:                              │    │   • score (0-10)                 │
│   • selected_anchors[] (2-4 texts)   │    │   • is_blank, text_readable      │
│   • reasoning                        │    │   • crop coordinates             │
└──────────────────────────────────────┘    └──────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                  LLM CALLS IN EXPLAINER WORKFLOW (Secondary)                    │
└─────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────┐    ┌──────────────────────────────────┐
│ LLM CALL: Content Analyzer           │    │ LLM CALL: Script Generator       │
│ ─────────────────────────────────────│    │ ─────────────────────────────────│
│ Provider: ClaudeCodeLLMProvider      │    │ Provider: ClaudeCodeLLMProvider  │
│ Model: claude-sonnet-4-20250514      │    │ Model: claude-sonnet-4-20250514  │
│ File: src/understanding/analyzer.py  │    │ File: src/script/generator.py    │
│ Prompt: ANALYSIS_SYSTEM_PROMPT       │    │ Prompts:                         │
│ Context:                             │    │   • EXPLAINER_SYSTEM_PROMPT or   │
│   • Document sections (15K chars)    │    │   • SHORT_SYSTEM_PROMPT          │
│   • Title, metadata                  │    │ Context:                         │
│ Output: ContentAnalysis              │    │   • ContentAnalysis              │
│   • core_thesis                      │    │   • Topic, duration              │
│   • key_concepts[]                   │    │ Output: script/script.json       │
│   • complexity_score                 │    └──────────────────────────────────┘
└──────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                       LLM CALLS IN REFINEMENT WORKFLOW                          │
└─────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────┐    ┌──────────────────────────────────┐
│ LLM CALL: Delivery Tags              │    │ LLM CALL: Feedback Parser        │
│ ─────────────────────────────────────│    │ ─────────────────────────────────│
│ Provider: ClaudeCodeLLMProvider      │    │ Provider: ClaudeCodeLLMProvider  │
│ Model: claude-sonnet-4-20250514      │    │ Model: claude-sonnet-4-20250514  │
│ File: src/voiceover/delivery_tags.py │    │ File: src/refine/feedback/       │
│ Context:                             │    │       parser.py                  │
│   • Raw narration text               │    │ Context:                         │
│ Output:                              │    │   • User feedback text           │
│   • Tagged text [thoughtful], etc.   │    │   • Current scenes list          │
│ Timeout: 60s                         │    │ Output: ParsedFeedback           │
└──────────────────────────────────────┘    │ Timeout: 120s                    │
                                            └──────────┬───────────────────────┘
                                                       │
                                                       ▼
                                            ┌──────────────────────────────────┐
                                            │ LLM CALL: Patch Generator        │
                                            │ ─────────────────────────────────│
                                            │ Provider: ClaudeCodeLLMProvider  │
                                            │ Model: claude-sonnet-4-20250514  │
                                            │ File: src/refine/feedback/       │
                                            │       generator.py               │
                                            │ Context:                         │
                                            │   • Parsed feedback              │
                                            │   • Current script.json          │
                                            │ Output: JSON patches             │
                                            │ Timeout: 180s                    │
                                            └──────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                          LLM CALL: FACT CHECKER                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────┐
│ Provider: ClaudeCodeLLMProvider     │
│ Model: claude-opus-4-5-20251101     │
│ File: src/factcheck/checker.py      │
│ Prompt: FACT_CHECK_SYSTEM_PROMPT    │
│ Tools: Read, Glob, Grep, WebSearch, │
│        WebFetch (file access mode)  │
│ Context:                            │
│   • Source documents from input/    │
│   • Script content                  │
│   • Narrations                      │
│ Output: FactCheckReport             │
│   • issues[] with severity          │
│   • summary scores                  │
│ Timeout: 600s (10 minutes)          │
└─────────────────────────────────────┘
```

### LLM Provider Abstraction

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         LLM PROVIDER ARCHITECTURE                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  DIRECTOR WORKFLOW (Shorts)         EXPLAINER WORKFLOW + REFINEMENT         │
│  ──────────────────────────         ───────────────────────────────         │
│                                                                             │
│  ┌─────────────────────┐            ┌─────────────────────────────┐         │
│  │ OpenAI API (direct) │            │ ClaudeCodeLLMProvider       │         │
│  │ openai.OpenAI()     │            │ (src/understanding/         │         │
│  │                     │            │  llm_provider.py)           │         │
│  │ Used by:            │            │                             │         │
│  │ • director draft    │            │ Uses: subprocess → `claude` │         │
│  │ • director          │            │       CLI tool              │         │
│  │   summarize         │            │                             │         │
│  │ • Witness agent     │            │ Methods:                    │         │
│  │   (anchor picking)  │            │ • generate() - text         │         │
│  │ • MCP skills        │            │ • generate_json() - JSON    │         │
│  │                     │            │ • generate_with_file_       │         │
│  │ Model: gpt-4o-mini  │            │   access() - with tools:    │         │
│  │        gpt-4o       │            │   Read/Write/Edit/Bash/     │         │
│  └─────────────────────┘            │   Glob/Grep                 │         │
│                                     │                             │         │
│  ┌─────────────────────┐            │ Used by:                    │         │
│  │ Anthropic API       │            │ • Content Analyzer          │         │
│  │ (direct)            │            │ • Script Generator          │         │
│  │                     │            │ • Delivery Tags             │         │
│  │ Used by:            │            │ • Feedback Parser           │         │
│  │ • VisionLLM         │            │ • Patch Generator           │         │
│  │   (screenshot       │            │ • Fact Checker              │         │
│  │    analysis)        │            │                             │         │
│  │                     │            │ Model: claude-sonnet-4      │         │
│  │ Model: claude-      │            │        claude-opus-4.5      │         │
│  │   sonnet-4          │            └─────────────────────────────┘         │
│  └─────────────────────┘                                                    │
│                                                                             │
│  ┌─────────────────────┐                                                    │
│  │ MockLLMProvider     │  For testing without API calls                     │
│  │ (src/understanding/ │  Returns canned JSON responses                     │
│  │  llm_provider.py)   │                                                    │
│  └─────────────────────┘                                                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### LLM Call Summary Table

| Workflow | LLM Call | Provider | Model | Timeout |
|----------|----------|----------|-------|---------|
| **Director** | Research Summarizer | OpenAI | gpt-4o | - |
| **Director** | Script Drafter | OpenAI | gpt-4o-mini | - |
| **Evidence** | Anchor Picker | OpenAI (async) | gpt-4o-mini | - |
| **Evidence** | Vision Analysis | Anthropic | claude-sonnet-4 | - |
| **Explainer** | Content Analyzer | ClaudeCode | claude-sonnet-4 | 300s |
| **Explainer** | Script Generator | ClaudeCode | claude-sonnet-4 | 300s |
| **Refinement** | Delivery Tags | ClaudeCode | claude-sonnet-4 | 60s |
| **Refinement** | Feedback Parser | ClaudeCode | claude-sonnet-4 | 120s |
| **Refinement** | Patch Generator | ClaudeCode | claude-sonnet-4 | 180s |
| **Quality** | Fact Checker | ClaudeCode | claude-opus-4.5 | 600s |

### System Prompt Locations

| Purpose | File | Key Prompts |
|---------|------|-------------|
| Short-form video | `src/prompts/director_short.py` | `SHORT_SYSTEM_PROMPT`, `SHORT_USER_PROMPT_TEMPLATE` |
| Explainer video | `src/prompts/director_explainer.py` | `EXPLAINER_SYSTEM_PROMPT` |
| Anchor picking | `src/prompts/anchor_picker.py` | `ANCHOR_PICKER_PROMPT` |
| Feedback parsing | `src/refine/feedback/prompts.py` | `PARSE_FEEDBACK_SYSTEM_PROMPT`, `GENERATE_*_PATCH_PROMPT` |
| Fact checking | `src/factcheck/prompts.py` | `FACT_CHECK_SYSTEM_PROMPT` |
| Delivery tags | `src/voiceover/delivery_tags.py` | `SYSTEM_PROMPT` (inline) |
| Content analysis | `src/understanding/analyzer.py` | `ANALYSIS_SYSTEM_PROMPT` (inline) |
| Visual inspection | `src/refine/visual/inspector.py` | `VISUAL_ANALYSIS_SYSTEM_PROMPT` (inline) |

### Context Scope Per LLM Call

Each LLM call receives only the context it needs (not full project):

| LLM Call | Context Provided | Full Project? |
|----------|------------------|---------------|
| Research Summarizer | research.json (full company data) | ⚠️ Partial |
| Script Drafter | topic, duration, evidence_urls | ❌ |
| Anchor Picker | Element description, text candidates from page | ❌ |
| Vision Analysis | Base64 image, anchor text | ❌ |
| Content Analyzer | Document content (15K chars), title | ❌ |
| Delivery Tags | Raw narration text only | ❌ |
| Feedback Parser | User feedback, scene list | ❌ |
| Patch Generator | Parsed feedback, current script.json | ❌ |
| Fact Checker | Script, narrations, source docs + web tools | ⚠️ Partial |

**Note:** Only `generate_with_file_access()` can read project files, and only what the prompt explicitly requests.

## Director Chat Frontend

The web UI at `director-chat/` provides a visual interface for the UGC Ad Factory pipeline.

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       DIRECTOR CHAT ARCHITECTURE                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  FRONTEND (Next.js)                    BACKEND (director-mcp)               │
│  ─────────────────                     ──────────────────────               │
│                                                                              │
│  director-chat/                        director-mcp/src/server.py           │
│  ├── app/(chat)/                       ├── factory_create_project           │
│  │   ├── projects/                     ├── factory_research_company         │
│  │   │   ├── new/page.tsx              ├── factory_summarize_research       │
│  │   │   └── [id]/                     ├── factory_get_status               │
│  │   │       ├── page.tsx              ├── factory_approve_stage            │
│  │   │       └── research/page.tsx     └── factory_get_artifacts            │
│  │   └── api/projects/                                                       │
│  │       ├── route.ts                                                        │
│  │       └── [id]/upload/route.ts                                           │
│  └── lib/director/client.ts            HTTP (port 8001)                     │
│          │                                    │                              │
│          └────────────────────────────────────┘                              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### UGC Ad Creation Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         UGC AD CREATION FLOW                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. INPUT (/projects/new)                                                    │
│  ┌────────────────────────────────┐                                         │
│  │ • Company URL                  │                                         │
│  │ • Assets (file drop)           │ ──▶ POST /api/projects                  │
│  │ • Topic/Angle                  │                                         │
│  │ • Voice/Avatar settings        │                                         │
│  └────────────────────────────────┘                                         │
│                    │                                                         │
│                    ▼                                                         │
│  2. RESEARCH (MCP Backend)                                                   │
│  ┌────────────────────────────────┐                                         │
│  │ factory_create_project         │ Creates project folder                  │
│  │         │                      │                                         │
│  │         ▼                      │                                         │
│  │ factory_research_company       │ Exa.ai → research.json                  │
│  │         │                      │                                         │
│  │         ▼                      │                                         │
│  │ factory_summarize_research     │ LLM → research-display.json             │
│  └────────────────────────────────┘                                         │
│                    │                                                         │
│                    ▼                                                         │
│  3. REVIEW (/projects/[id]/research)                                        │
│  ┌────────────────────────────────┐                                         │
│  │ Editable Cards UI:             │                                         │
│  │ • Hook Angles (select/edit)    │                                         │
│  │ • Testimonial Themes           │                                         │
│  │ • Value Propositions           │                                         │
│  │ • Target Audience              │                                         │
│  └────────────────────────────────┘                                         │
│                    │                                                         │
│                    ▼ (approve selections)                                    │
│  4. SCRIPT GENERATION → 5. VOICEOVER → 6. AVATAR → 7. RENDER                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Frontend Routes

| Route | Purpose |
|-------|---------|
| `/projects/new` | Input form + file drop for new UGC ad project |
| `/projects/[id]` | Project overview and status |
| `/projects/[id]/research` | Review research-display.json as editable cards |
| `/chat/[id]` | Chat interface for project refinement |

### API Routes

| Route | Method | Purpose |
|-------|--------|---------|
| `/api/projects` | POST | Create project → research → summarize |
| `/api/projects` | GET | List all projects |
| `/api/projects/[id]/upload` | POST | Upload assets to projects/{id}/input/ |

### MCP Client (lib/director/client.ts)

TypeScript functions for calling director-mcp tools:

```typescript
// Research pipeline
researchCompany(projectId, companyUrl)    // → research.json
summarizeResearch(projectId)               // → research-display.json

// Project lifecycle
createProject(params)                      // → project folder
getProjectStatus(projectId)                // → status + gates
approveStage(projectId, gateId, userId)   // → unlock next stage
getArtifacts(projectId, type?)            // → artifacts array
```

## Reference Videos

Style reference: Varun Mayya (@VarunMayya), Ali Abdaal
- Bold typography
- Evidence screenshots with highlights
- Avatar in various positions
- Word-by-word captions
- 30-60 second shorts
- 9:16 vertical format
