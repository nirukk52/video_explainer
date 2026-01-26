---
name: avatar-generation
description: Generate lip-synced avatar videos using HeyGen API with external audio for Remotion video templates. Use when creating talking head videos for SplitProof, FullAvatar, or other templates that require avatar clips. Requires pre-generated audio (from voiceover-generation skill), uploads to Supabase, then HeyGen lip-syncs avatar to audio. Always read project config.json for avatar_id.
---

# Avatar Generation

Generate lip-synced avatar videos using HeyGen API with external audio, cropped to fit Remotion template layouts.

## End-to-End Workflow

```
Audio file → Upload to Supabase → HeyGen Lip-sync (1280x720) → FFmpeg Crop → Update script.json
```

**Key insight:** Audio is generated separately (ElevenLabs via voiceover-generation skill). HeyGen only does lip-sync to that audio.

## Prerequisites

1. **Audio file must exist** - Generate with voiceover-generation skill first
2. **Read project config.json** - Get `avatar.avatar_id` from `projects/{id}/config.json`

## Quick Reference

```bash
# Full workflow for a scene
cd /path/to/video_explainer

# 1. Generate audio first (use voiceover-generation skill)
# 2. Then run avatar generation:
python -c "
from dotenv import load_dotenv
load_dotenv('.env')
# ... see full workflow below
"
```

## Complete Workflow (Proven Pattern)

### Step 1: Upload Audio to Supabase

```python
from dotenv import load_dotenv
load_dotenv('.env')
import os, httpx
from pathlib import Path

supabase_url = os.environ.get('SUPABASE_PROJECT_URL')
supabase_key = os.environ.get('SUPABASE_ANON_KEY')

audio_path = Path('projects/first-draft/avatar/scene_004_audio.mp3')
file_name = 'first-draft_scene_004.mp3'

headers = {
    'Authorization': f'Bearer {supabase_key}',
    'apikey': supabase_key,
    'Content-Type': 'audio/mpeg',
}

with httpx.Client(timeout=60.0) as client:
    resp = client.post(
        f'{supabase_url}/storage/v1/object/audio/{file_name}',
        headers=headers,
        content=audio_path.read_bytes()
    )
    if resp.status_code not in (200, 201):
        resp = client.put(f'{supabase_url}/storage/v1/object/audio/{file_name}',
                          headers=headers, content=audio_path.read_bytes())

public_url = f'{supabase_url}/storage/v1/object/public/audio/{file_name}'
```

### Step 2: Generate HeyGen Avatar with Audio

```python
import time, json

# Load avatar_id from project config
with open('projects/first-draft/config.json') as f:
    config = json.load(f)
avatar_id = config['avatar']['avatar_id']

api_key = os.environ.get('HEYGEN_API_KEY')
motion_prompt = 'Talking Naturally: Subject talks animatedly while maintaining direct eye contact with the camera. Background elements subtly move to enhance realism. Camera remains absolutely static.'

payload = {
    'video_inputs': [{
        'character': {
            'type': 'avatar',
            'avatar_id': avatar_id,
            'avatar_style': 'normal',
            'motion_prompt': motion_prompt
        },
        'voice': {
            'type': 'audio',
            'audio_url': public_url  # From Step 1
        }
    }],
    'dimension': {'width': 1280, 'height': 720}
}

headers = {'X-Api-Key': api_key, 'Content-Type': 'application/json'}

with httpx.Client(timeout=60.0) as client:
    resp = client.post('https://api.heygen.com/v2/video/generate', headers=headers, json=payload)
    video_id = resp.json()['data']['video_id']
    
    # Poll for completion (~30-60s)
    while True:
        status = client.get(f'https://api.heygen.com/v1/video_status.get?video_id={video_id}', headers=headers).json()
        if status['data']['status'] == 'completed':
            video_url = status['data']['video_url']
            video_data = client.get(video_url).content
            Path('projects/first-draft/avatar/scene_004_16x9.mp4').write_bytes(video_data)
            break
        elif status['data']['status'] == 'failed':
            raise RuntimeError(status['data']['error'])
        time.sleep(5)
```

### Step 3: Crop for Template

```bash
# SplitProof (bottom 40%)
ffmpeg -y -i projects/first-draft/avatar/scene_004_16x9.mp4 \
  -vf "crop=1012:720:134:0" -c:a copy \
  projects/first-draft/avatar/scene_004_bottom.mp4
```

## Template Crop Reference

| Template | Aspect Ratio | Crop Command |
|----------|--------------|--------------|
| SplitProof | 1.406:1 | `crop=1012:720:134:0` |
| FullAvatar | 9:16 | `crop=405:720:437:0` |
| PiP Corner | 9:16 | `crop=405:720:437:0` |

## Environment Variables

Required in `.env`:
- `HEYGEN_API_KEY` - HeyGen API key
- `SUPABASE_PROJECT_URL` - Supabase project URL (e.g., `https://xxx.supabase.co`)
- `SUPABASE_ANON_KEY` - Supabase anon key

## Project Config

**ALWAYS read from `projects/{id}/config.json`:**

```json
{
  "avatar": {
    "provider": "heygen",
    "avatar_id": "a247c0b271f0447088bac6043903cf16"
  },
  "tts": {
    "provider": "elevenlabs",
    "voice_id": "s3TPKV1kjDlVtZbl4Ksh"
  }
}
```

## Output Files

```
avatar/
  scene_XXX_16x9.mp4    # Original HeyGen output (1280x720)
  scene_XXX_bottom.mp4  # Cropped for SplitProof template
  scene_XXX_audio.mp3   # Audio file (from voiceover skill)
```

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| RESOLUTION_NOT_ALLOWED | Plan limits | Use 1280x720, not 1920x1080 |
| Bucket not found | Supabase bucket missing | Create "audio" bucket in Supabase dashboard |
| RLS policy error | Upload blocked | Add INSERT policy for anon role on storage.objects |
| Wrong voice | Using HeyGen TTS | Use external audio from ElevenLabs instead |

## Verified Success

### scene_005 (first-draft project) - Jan 2026
1. Audio: `projects/first-draft/avatar/scene_005_audio.mp3` (pre-generated via voiceover-generation skill)
2. Supabase upload: `https://dnqfwenrekswrnlziqem.supabase.co/storage/v1/object/public/audio/first-draft_scene_005.mp3`
3. HeyGen video_id: `29353d56d035464ebfebc7100ae0b445`
4. Generation time: ~55s with avatar `a247c0b271f0447088bac6043903cf16`
5. Output files:
   - `scene_005_16x9.mp4` - Original HeyGen output
   - `scene_005_bottom.mp4` - Cropped for SplitProof

### scene_004 (first-draft project)
1. ElevenLabs audio: 4.92s with voice `s3TPKV1kjDlVtZbl4Ksh`
2. Supabase upload: `https://dnqfwenrekswrnlziqem.supabase.co/storage/v1/object/public/audio/first-draft_scene_004.mp3`
3. HeyGen generation: ~30s with avatar `a247c0b271f0447088bac6043903cf16`
4. Crop: `crop=1012:720:134:0` for SplitProof

## Pipeline Integration

This skill is **Step 2** of the scene generation pipeline:

```
1. voiceover-generation → Audio + timestamps (REQUIRED FIRST)
2. avatar-generation (this) → Lip-synced video using audio
3. background-video-generation → AI background video (can run in parallel)
4. Update script.json with all paths and timestamps
```

**Prerequisites:** Audio file must exist (run voiceover-generation first)
**After generating avatar, update script.json with avatar src path.**

## Important Notes

- **Always activate venv first**: `source .venv/bin/activate` before running Python commands
- **HeyGen timeout**: Use `timeout=120.0` on httpx client for longer generation times
- **POST vs PUT for Supabase**: POST creates new, PUT updates existing - try POST first, fallback to PUT

## Verified Success

### scene_006 (first-draft project) - Jan 2026
1. Audio: `projects/first-draft/avatar/scene_006_audio.mp3` (pre-generated via voiceover-generation skill)
2. Supabase upload: `https://dnqfwenrekswrnlziqem.supabase.co/storage/v1/object/public/audio/first-draft_scene_006.mp3`
3. HeyGen video_id: `4c69baec437043e38a3733772dcd1016`
4. Generation time: ~84s with avatar `a247c0b271f0447088bac6043903cf16`
5. Output files:
   - `scene_006_16x9.mp4` - Original HeyGen output
   - `scene_006_bottom.mp4` - Cropped for SplitProof
