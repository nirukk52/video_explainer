# Shorts Factory

Create Varun Mayya / Johnny Harris style vertical shorts (30-60 seconds) with AI-powered research, evidence capture, and video generation.

## Philosophy

**Evidence-First Production:** Gather proof screenshots BEFORE writing the script. The script references real evidence, not hallucinated claims.

**JSON-Driven Templates:** Everything is JSON. Templates, scenes, timing - all defined in JSON so agents can read, understand, and generate.

**Human-in-the-Loop:** Approve at each stage. Perfect Scene 1 before Scene 2. Each iteration improves the templates and vibe.

## Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                        SHORTS FACTORY                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. RESEARCH        2. EVIDENCE         3. SCRIPT               │
│  ┌──────────┐      ┌──────────┐       ┌──────────┐             │
│  │ URLs     │ ──▶  │ Witness  │ ──▶   │ Director │             │
│  │ Articles │      │ Agent    │       │ Agent    │             │
│  │ Prompts  │      │          │       │          │             │
│  └──────────┘      └──────────┘       └──────────┘             │
│       │                 │                   │                   │
│       ▼                 ▼                   ▼                   │
│  input/            evidence/           script.json              │
│                                                                  │
│  4. AUDIO           5. AVATAR          6. RENDER                │
│  ┌──────────┐      ┌──────────┐       ┌──────────┐             │
│  │ Eleven   │ ──▶  │ HeyGen   │ ──▶   │ Remotion │             │
│  │ Labs     │      │ Lip-sync │       │          │             │
│  └──────────┘      └──────────┘       └──────────┘             │
│       │                 │                   │                   │
│       ▼                 ▼                   ▼                   │
│  audio/            avatar/             output/                  │
│                                                                  │
│  ✓ Human Review     ✓ Human Review     ✓ Human Review          │
│    after each         after each         final render          │
│    stage              stage                                     │
└─────────────────────────────────────────────────────────────────┘
```

## Project Structure

Each project is self-contained with all inputs, intermediates, and outputs:

```
projects/
└── my-short/
    ├── config.json              # Project settings
    │
    ├── input/                   # Research materials
    │   ├── prompt.md            # Topic + angle
    │   ├── urls.json            # Source URLs to capture
    │   └── research/            # PDFs, screenshots, docs
    │
    ├── evidence/                # Captured proof (Witness Agent)
    │   ├── manifest.json        # Evidence index
    │   ├── techspot_001.png     # Screenshot captures
    │   ├── twitter_002.png
    │   └── ...
    │
    ├── script/
    │   └── script.json          # Scene-by-scene script
    │
    ├── audio/
    │   ├── voiceover.mp3        # ElevenLabs audio
    │   └── timestamps.json      # Word-level timing
    │
    ├── avatar/
    │   ├── scene_001.mp4        # HeyGen lip-sync clips
    │   ├── scene_002.mp4
    │   └── ...
    │
    ├── backgrounds/             # AI-generated or stock
    │   ├── scene_001.mp4        # Veo 3 / stock footage
    │   └── ...
    │
    └── output/
        ├── short.mp4            # Final render
        └── ratings.json         # Per-scene 1-10 ratings
```

## Templates

5 JSON-driven templates for any Varun Mayya style scene:

### 1. TextOverProof
Bold headline text over a cropped evidence screenshot.

```json
{
  "template": "TextOverProof",
  "background": {
    "type": "screenshot",
    "src": "evidence/techspot_001.png",
    "crop": { "x": 0, "y": 100, "width": 1080, "height": 800 }
  },
  "avatar": { "visible": false },
  "text": {
    "headline": "motion sensing glove",
    "position": "top",
    "highlight_words": ["glove"]
  }
}
```

### 2. SplitProof
Evidence on top, avatar talking on bottom.

```json
{
  "template": "SplitProof",
  "background": {
    "type": "screenshot",
    "src": "evidence/article_002.png",
    "highlight_box": { "x": 50, "y": 200, "width": 400, "height": 80 }
  },
  "avatar": {
    "visible": true,
    "position": "bottom",
    "src": "avatar/scene_002.mp4"
  },
  "text": {
    "caption": "blocks of protein"
  }
}
```

### 3. FullAvatar
Avatar fills the screen, text overlay optional.

```json
{
  "template": "FullAvatar",
  "background": {
    "type": "gradient",
    "colors": ["#0a0a0f", "#1a1a2e"]
  },
  "avatar": {
    "visible": true,
    "position": "full",
    "src": "avatar/scene_003.mp4"
  },
  "text": {
    "headline": "are taking over",
    "position": "top"
  }
}
```

### 4. ProofOnly
Screenshot fills the entire frame with highlight and caption.

```json
{
  "template": "ProofOnly",
  "background": {
    "type": "screenshot",
    "src": "evidence/twitter_004.png"
  },
  "avatar": { "visible": false },
  "text": {
    "caption": "Ozempic for autism",
    "highlight_box": { "x": 100, "y": 300, "width": 600, "height": 100 }
  }
}
```

### 5. TextCard
Bold statement on gradient background, no image.

```json
{
  "template": "TextCard",
  "background": {
    "type": "gradient",
    "colors": ["#1a1a2e", "#0a0a0f"]
  },
  "avatar": { "visible": false },
  "text": {
    "headline": "about tech workers",
    "style": "dramatic"
  }
}
```

## Script Schema

The script.json defines the entire video:

```json
{
  "id": "peptides-short",
  "title": "Chinese Peptides Taking Over Silicon Valley",
  "duration_seconds": 45,
  "scenes": [
    {
      "id": "scene_001",
      "template": "SplitProof",
      "start_seconds": 0,
      "end_seconds": 4.5,
      "audio": {
        "text": "Chinese peptides are taking over Silicon Valley",
        "file": "audio/voiceover.mp3",
        "word_timestamps": [
          { "word": "Chinese", "start": 0.0, "end": 0.4 },
          { "word": "peptides", "start": 0.4, "end": 0.9 }
        ]
      },
      "background": {
        "type": "screenshot",
        "src": "evidence/techspot_001.png"
      },
      "avatar": {
        "visible": true,
        "position": "bottom",
        "src": "avatar/scene_001.mp4"
      },
      "text": {
        "caption_style": "word_by_word"
      }
    }
  ]
}
```

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 20+
- FFmpeg
- API Keys: ElevenLabs, HeyGen, Browserbase (for evidence capture)

### Installation

```bash
cd video_explainer

# Python environment
python -m venv .venv
source .venv/bin/activate
pip install -e .

# Remotion dependencies
cd remotion && npm install && cd ..
```

### Create a Short (Manual First)

```bash
# 1. Create project
python -m src.cli create my-short --type short

# 2. Add research to projects/my-short/input/
#    - prompt.md: Your topic and angle
#    - urls.json: Sources to capture

# 3. Capture evidence
python -m src.cli evidence my-short

# 4. Generate script (references evidence)
python -m src.cli script my-short

# 5. Generate audio
python -m src.cli audio my-short

# 6. Generate avatar clips
python -m src.cli avatar my-short

# 7. Preview in Remotion
cd remotion && npm run dev

# 8. Render
python -m src.cli render my-short
```

## Configuration

### Project Config (projects/*/config.json)

```json
{
  "id": "my-short",
  "type": "short",
  "video": {
    "width": 1080,
    "height": 1920,
    "fps": 30,
    "duration_seconds": 45
  },
  "tts": {
    "provider": "elevenlabs",
    "voice_id": "your-voice-id"
  },
  "avatar": {
    "provider": "heygen",
    "avatar_id": "your-avatar-id"
  },
  "style": {
    "background": "#0a0a0f",
    "text_color": "#ffffff",
    "accent_color": "#00d9ff"
  }
}
```

### Environment Variables

```bash
ELEVENLABS_API_KEY=xxx      # Text-to-speech
HEYGEN_API_KEY=xxx          # Avatar generation
BROWSERBASE_API_KEY=xxx     # Evidence capture
EXA_API_KEY=xxx             # URL research
OPENAI_API_KEY=xxx          # LLM for script
```

## Self-Improvement

After each video, rate scenes 1-10 in `output/ratings.json`:

```json
{
  "overall": 7,
  "scenes": [
    { "id": "scene_001", "rating": 8, "notes": "Good hook" },
    { "id": "scene_002", "rating": 5, "notes": "Text too small" }
  ]
}
```

Patterns emerge over time:
- Which templates score highest?
- What pacing works best?
- Which evidence types are most compelling?

## Architecture

```
src/
├── agents/                  # AI agents
│   ├── witness.py           # Evidence capture (Browserbase)
│   ├── investigator.py      # URL discovery (Exa)
│   ├── director.py          # Script generation
│   └── editor.py            # Render manifest
│
├── audio/                   # ElevenLabs TTS
├── avatar/                  # HeyGen integration
│
└── cli/                     # Command interface

remotion/
├── src/
│   ├── templates/           # 5 JSON-driven templates
│   │   ├── TextOverProof.tsx
│   │   ├── SplitProof.tsx
│   │   ├── FullAvatar.tsx
│   │   ├── ProofOnly.tsx
│   │   └── TextCard.tsx
│   │
│   └── ShortsPlayer.tsx     # Main composition
```

## Reference

- Style: Varun Mayya, Johnny Harris, Fever
- Format: 9:16 vertical (1080x1920)
- Length: 30-60 seconds
- Scene duration: 1-10 seconds each
- Platforms: YouTube Shorts, Instagram Reels, TikTok
