# Agent Guide: Shorts Factory

This document guides AI agents working on the Shorts Factory system. Follow these patterns for consistent, high-quality video production.

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

┌─────────────────────────────────────────────────────────────────────────────┐
│                    CURRENT STATE: first-draft                                │
│                    Phase: awaiting_capture (stale - voiceover done)          │
└─────────────────────────────────────────────────────────────────────────────┘

                           DEPENDENCY CHAIN
┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│   ┌────────────────┐                                                         │
│   │ config.json    │  Project settings (dimensions, fps, providers)          │
│   └───────┬────────┘                                                         │
│           │                                                                  │
│           ▼                                                                  │
│   ┌────────────────┐      ┌──────────────────┐                              │
│   │ User Topic     │ ──▶  │ .director_state  │  State machine tracking       │
│   │ "China drone   │      │    .json         │  phase transitions            │
│   │  swarm tech"   │      └────────┬─────────┘                              │
│   └────────────────┘               │                                         │
│                                    ▼                                         │
│                    ┌───────────────────────────────┐                         │
│                    │        narration.json         │ ◄── LLM generates       │
│                    │  • title                      │     scene breakdown      │
│                    │  • scenes[].narration text    │                         │
│                    │  • scenes[].duration estimate │                         │
│                    └───────────────┬───────────────┘                         │
│                                    │                                         │
│           ┌────────────────────────┼────────────────────────┐               │
│           │                        │                        │               │
│           ▼                        ▼                        ▼               │
│   ┌───────────────┐   ┌────────────────────┐   ┌─────────────────┐          │
│   │ backgrounds/  │   │ voiceover/         │   │ avatar/ (TODO)  │          │
│   │ drone_swarm   │   │ manifest.json      │   │ scene_001.mp4   │          │
│   │   .mp4 ✓      │   │ scene_001.mp3 ✓    │   │ scene_002.mp4   │          │
│   │ (manual)      │   │ scene_002.mp3 ✓    │   │ (HeyGen)        │          │
│   └───────┬───────┘   └─────────┬──────────┘   └────────┬────────┘          │
│           │                     │                       │                    │
│           │                     │ word_timestamps       │                    │
│           │                     │ duration_seconds      │                    │
│           │                     ▼                       │                    │
│           │         ┌────────────────────────────────┐  │                    │
│           └────────▶│     script/script.json         │◄─┘                    │
│                     │  • scenes[].audio.file         │                       │
│                     │  • scenes[].audio.word_timestamps                      │
│                     │  • scenes[].background.src     │                       │
│                     │  • scenes[].avatar.src (TODO)  │                       │
│                     │  • scenes[].start/end_seconds  │                       │
│                     └───────────────┬────────────────┘                       │
│                                     │                                        │
│                                     ▼                                        │
│                     ┌────────────────────────────────┐                       │
│                     │     REMOTION RENDER            │                       │
│                     │  VarunPlayer reads script.json │                       │
│                     │  + resolves all asset paths    │                       │
│                     └───────────────┬────────────────┘                       │
│                                     │                                        │
│                                     ▼                                        │
│                     ┌────────────────────────────────┐                       │
│                     │     output/short.mp4           │                       │
│                     │     (final video)              │                       │
│                     └────────────────────────────────┘                       │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

                           CURRENT ASSET STATUS
┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│   ASSET                  STATUS        SOURCE           NEXT STEP            │
│   ─────────────────────────────────────────────────────────────────────────  │
│   backgrounds/           ✅ READY      Manual upload    -                    │
│     drone_swarm.mp4                                                          │
│                                                                              │
│   voiceover/             ✅ READY      ElevenLabs       -                    │
│     scene_001.mp3                      TTS API                               │
│     scene_002.mp3                                                            │
│     manifest.json                                                            │
│                                                                              │
│   avatar/                ❌ MISSING    HeyGen API       Generate clips       │
│     scene_001.mp4                                       with lip-sync        │
│     scene_002.mp4                                                            │
│                                                                              │
│   script/script.json     ✅ READY      Generated        Has all timing       │
│                          (partial)                      but avatar.src       │
│                                                         paths missing        │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

                           PIPELINE FLOW
┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  STAGE 1        STAGE 2         STAGE 3         STAGE 4         STAGE 5     │
│  ────────       ────────        ────────        ────────        ────────    │
│                                                                              │
│  ┌─────────┐   ┌───────────┐   ┌───────────┐   ┌───────────┐   ┌─────────┐ │
│  │ Topic   │──▶│ Narration │──▶│ Voiceover │──▶│  Avatar   │──▶│ Render  │ │
│  │ + Config│   │ Generator │   │ Generator │   │ Generator │   │ Remotion│ │
│  └─────────┘   └───────────┘   └───────────┘   └───────────┘   └─────────┘ │
│       │              │               │               │               │       │
│       ▼              ▼               ▼               ▼               ▼       │
│  config.json   narration.json  voiceover/       avatar/         output/     │
│                                manifest.json    scene_*.mp4     short.mp4   │
│                                scene_*.mp3                                   │
│                                      │                                       │
│                                      ▼                                       │
│                               script/script.json ◄─────────────────────────  │
│                               (updated with timing)                          │
│                                                                              │
│  ──────────────────────────────────────────────────────────────────────────  │
│  YOU ARE HERE:           ✅ ✅ ✅             ───▶  ❌              ❌       │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘




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
```

## Reference Videos

Style reference: Varun Mayya (@VarunMayya)
- Bold typography
- Evidence screenshots with highlights
- Avatar in various positions
- Word-by-word captions
- 30-60 second shorts
- 9:16 vertical format
