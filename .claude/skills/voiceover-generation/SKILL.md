---
name: voiceover-generation
description: Generate voiceover audio with word-level timestamps using ElevenLabs TTS for Remotion video templates. Use when creating audio for scenes, generating word timestamps for captions, or preparing audio for avatar lip-sync. Always read project config.json for voice_id. Outputs audio file + word timestamps for script.json.
---

# Voiceover Generation

Generate voiceover audio with word-level timestamps using ElevenLabs TTS via `src/audio/tts.py`.

## End-to-End Workflow

```
Text + config.json → ElevenLabs TTS → Audio file + Word timestamps → Update script.json
```

## Prerequisites

1. **Read project config.json** - Get `tts.voice_id` from `projects/{id}/config.json`
2. **ELEVENLABS_API_KEY** in `.env`

## Quick Generation

**Run with `uv run python3 -c "..."` in the project root.**

```python
from dotenv import load_dotenv
load_dotenv('.env')

import json
from pathlib import Path
from src.audio.tts import ElevenLabsTTS
from src.config import TTSConfig

# Load voice_id from project config
with open('projects/first-draft/config.json') as f:
    config = json.load(f)
voice_id = config['tts']['voice_id']

# Generate audio with timestamps
tts_config = TTSConfig(provider='elevenlabs', voice_id=voice_id, model='eleven_multilingual_v2')
tts = ElevenLabsTTS(tts_config)

text = "Ducted fans hidden inside keep the sword silhouette clean no exposed propeller blades"
result = tts.generate_with_timestamps(text, 'projects/first-draft/avatar/scene_004_audio.mp3')

print(f'Duration: {result.duration_seconds:.2f}s')
print(f'Words: {len(result.word_timestamps)}')

# Format for script.json
timestamps = [
    {'word': w.word, 'start': round(w.start_seconds, 3), 'end': round(w.end_seconds, 3)}
    for w in result.word_timestamps
]
print(json.dumps(timestamps, indent=2))
```

## Output Format

The `generate_with_timestamps()` method returns a `TTSResult`:

```python
@dataclass
class TTSResult:
    audio_path: Path           # Path to generated MP3
    duration_seconds: float    # Total audio duration
    word_timestamps: list[WordTimestamp]  # Word-level timing

@dataclass
class WordTimestamp:
    word: str
    start_seconds: float
    end_seconds: float
```

## Update script.json

After generation, update the scene's audio section:

```json
{
  "audio": {
    "text": "Ducted fans hidden inside keep the sword silhouette clean no exposed propeller blades",
    "file": "avatar/scene_004_audio.mp3",
    "word_timestamps": [
      { "word": "Ducted", "start": 0.0, "end": 0.372 },
      { "word": "fans", "start": 0.406, "end": 0.673 },
      ...
    ]
  }
}
```

**Important:** Update scene timing based on audio duration:
- `end_seconds = start_seconds + result.duration_seconds`
- Cascade timing changes to subsequent scenes

## Project Config

**ALWAYS read from `projects/{id}/config.json`:**

```json
{
  "tts": {
    "provider": "elevenlabs",
    "voice_id": "s3TPKV1kjDlVtZbl4Ksh"
  }
}
```

## Environment Variables

Required in `.env`:
- `ELEVENLABS_API_KEY` - ElevenLabs API key

## Using src/voiceover/generator.py

For batch generation or more control, use the `VoiceoverGenerator` class:

```python
from src.voiceover.generator import VoiceoverGenerator
from src.voiceover.narration import SceneNarration
from src.config import load_config

config = load_config()
generator = VoiceoverGenerator(config, provider='elevenlabs')

narration = SceneNarration(
    scene_id='scene_004',
    title='Ducted Fans',
    narration='Ducted fans hidden inside keep the sword silhouette clean'
)

result = generator.generate_scene_voiceover(narration, output_dir=Path('projects/first-draft/voiceover'))
```

## Output Files

```
avatar/
  scene_XXX_audio.mp3   # Audio for avatar lip-sync (same audio)
  
voiceover/
  scene_XXX.mp3         # Alternative location for audio
  manifest.json         # Batch generation manifest
```

## Duration Guidelines

| Text Length | Approx Duration |
|-------------|-----------------|
| 10 words | ~3-4 seconds |
| 20 words | ~6-8 seconds |
| 30 words | ~10-12 seconds |

Shorts typically use 3-6 second scenes.

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| API key error | Missing env var | Set ELEVENLABS_API_KEY in .env |
| Wrong voice | Hardcoded voice_id | Read from config.json |
| No timestamps | Using wrong endpoint | Use `generate_with_timestamps()` not `generate()` |
| Audio too fast/slow | Voice settings | Adjust stability/similarity_boost in TTSConfig |

## Pipeline Integration

This skill is **Step 1** of the scene generation pipeline:

```
1. voiceover-generation (this) → Audio + timestamps
2. avatar-generation → Lip-synced video using audio from step 1
3. background-video-generation → AI background video
4. Update script.json with all paths and timestamps
```

**After generating voiceover, proceed immediately to avatar-generation skill.**

## Verified Success

scene_006 (first-draft project) - Jan 2026:
- Voice: `s3TPKV1kjDlVtZbl4Ksh` (from config.json)
- Text: "And the craziest part a motion sensing glove controls the entire swarm Wuxia fantasy made real"
- Duration: 4.923s
- Words: 16 with word-level timestamps from ElevenLabs API
- Output: `avatar/scene_006_audio.mp3`

scene_005 (first-draft project):
- Voice: `s3TPKV1kjDlVtZbl4Ksh` (from config.json)
- Text: "They're programmed to move as one maintaining perfect distance like a single organism"
- Duration: 4.365s
- Words: 13 with word-level timestamps from ElevenLabs API
- Output: `avatar/scene_005_audio.mp3`

scene_004 (first-draft project):
- Voice: `s3TPKV1kjDlVtZbl4Ksh` (from config.json)
- Text: "Ducted fans hidden inside keep the sword silhouette clean no exposed propeller blades"
- Duration: 4.92s
- Words: 13 with word-level timestamps from ElevenLabs API
