---
name: background-video-generation
description: Generate AI background videos for Remotion video templates using fal.ai API (Kling 1.5 Pro, Google Veo3). Use when creating background videos, b-roll footage, or visual content for scenes in video shorts. Triggers on requests to create/generate videos for scenes, backgrounds, or when updating script.json video sources.
---

# Background Video Generation

Generate AI videos for scene backgrounds using fal.ai's text-to-video API.

## Workflow

```
1. Add scene to ai_video_config.json → 2. Run generate_ai_video.py → 3. Update script.json paths
```

**Typical generation time:** 2-4 minutes for Kling 1.5 Pro 5s video

## Step 1: Create Configuration

Create `projects/{project}/backgrounds/ai_video_config.json`:

```json
{
  "scene_001": {
    "narration": "The voiceover text for context",
    "timing": {
      "start_seconds": 0,
      "end_seconds": 3.5
    },
    "prompt": {
      "main": "Detailed visual description. Include: subject, action, setting, lighting, camera movement, atmosphere.",
      "context": "Optional context about the scene"
    },
    "generation": {
      "model": "fal-ai/kling-video/v1.5/pro/text-to-video",
      "aspect_ratio": "9:16",
      "duration": "5",
      "resolution": "1080p",
      "generate_audio": false,
      "negative_prompt": "blurry, low quality, distorted, text, watermark"
    },
    "output": {
      "filename": "scene_001_description.mp4"
    }
  }
}
```

## Step 2: Generate Video

```bash
# Load environment and generate
cd /path/to/video_explainer
export $(grep -v '^#' .env | xargs)
python scripts/generate_ai_video.py projects/first-draft --scene scene_004

# Dry run first to verify config
python scripts/generate_ai_video.py projects/first-draft --scene scene_004 --dry-run
```

**Required**: `FAL_KEY` environment variable (get from https://fal.ai/dashboard/keys)

**Example output:**
```
Scene: scene_004
🎬 Generating video with Kling 1.5 Pro...
   This may take 2-6 minutes...
  Status: IN_PROGRESS | Queue position: ?
  ...
✅ Video generated successfully!
   Path: projects/first-draft/backgrounds/scene_004_ducted_fans.mp4
   Duration: 5s
   Generation time: 188.0s
```

## Step 3: Update script.json

Update the scene's background or video_inset source:

```json
{
  "background": {
    "type": "ai_video",
    "src": "backgrounds/scene_001_description.mp4"
  }
}
```

Or for VideoCard template:

```json
{
  "video_inset": {
    "src": "backgrounds/scene_001_description.mp4"
  }
}
```

## Model Selection

| Model | Cost | Duration | Aspect Ratios | Best For |
|-------|------|----------|---------------|----------|
| `fal-ai/kling-video/v1.5/pro/text-to-video` | $0.10/sec | 5s, 10s | 16:9, 9:16, 1:1 | Cost-effective shorts |
| `fal-ai/veo3/fast` | $0.25/sec | 4s, 6s, 8s | 16:9 only | Quality + speed balance |
| `fal-ai/veo3` | $0.50/sec | 4s, 6s, 8s | 16:9 only | Highest quality |

**Default**: Use Kling 1.5 Pro for 9:16 portrait shorts (supports native vertical).

## Prompt Best Practices

1. **Be specific**: "Massive drone swarm forming geometric patterns" not "drones flying"
2. **Include atmosphere**: "futuristic sci-fi atmosphere, dramatic lighting"
3. **Specify camera**: "smooth sweeping aerial camera movement"
4. **Add setting**: "night sky above Chinese city skyline"
5. **Use negative prompts**: Always exclude "blurry, low quality, text, watermark"

Example effective prompt:
```
Massive swarm of thousands of glowing drones forming intricate geometric patterns 
in night sky above Chinese city skyline. Military precision choreography, 
synchronized light displays, futuristic sci-fi atmosphere. Cinematic aerial view, 
smooth sweeping camera movement.
```

## Duration Guidelines

| Scene Duration | Video Duration | Model Duration Setting |
|----------------|----------------|----------------------|
| < 4 seconds | 5 seconds | `"5"` (Kling) or `"4s"` (Veo3) |
| 4-6 seconds | 5-6 seconds | `"5"` or `"6s"` |
| 6-10 seconds | 8-10 seconds | `"8s"` or `"10"` |

Generate slightly longer than scene duration - Remotion handles trimming.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| FAL_KEY not set | `export $(grep -v '^#' .env | xargs)` before running |
| Wrong aspect ratio | Use Kling for 9:16 shorts; Veo3 only supports 16:9 |
| Video too short | Increase duration setting in config |
| Poor quality | Add more detail to prompt; use negative_prompt |
| Queue stuck | Normal - Kling can take 2-4 min, shows IN_PROGRESS |

## Pipeline Integration

This skill is **Step 3** of the scene generation pipeline:

```
1. voiceover-generation → Audio + timestamps
2. avatar-generation → Lip-synced video
3. background-video-generation (this) → AI background video
4. Update script.json with all paths and timestamps
```

**Can run in parallel with avatar-generation** - no dependency on audio.
**After generating background, update script.json with background src path.**

## Verified Success: first-draft

Generated backgrounds for drone swarm short:
- scene_006: `scene_006_glove_control.mp4` - Motion sensing glove controlling swarm (Jan 2026)
- scene_005: `scene_005_swarm_organism.mp4` - Synchronized swarm movement like organism
- scene_004: `scene_004_ducted_fans.mp4` - Ducted fan propulsion detail
- scene_003: `scene_003_blade_drones.mp4` - Close-up blade-shaped drones
- scene_002: `scene_002_scifi_drones.mp4` - Drone swarm forming patterns

All generated with Kling 1.5 Pro at 9:16 aspect ratio, 5s duration, ~$0.50/video.

### Effective Prompt Examples

**scene_004 (technical detail):**
```
Extreme close-up of sleek sword-shaped drone revealing hidden ducted fan propulsion 
system inside the blade fuselage. Cross-section view showing internal mechanics - 
ducted fans spinning inside enclosed channels, no visible external propellers. 
Clean aerodynamic sword silhouette maintained, matte black surface with subtle 
blue LED accents. Technical diagram aesthetic with cinematic lighting, slow 
revealing camera pan along the drone body.
```

**Key elements:** Subject detail, internal mechanics, surface materials, lighting style, camera movement

**scene_006 (wuxia gesture control):**
```
Close-up of human hand wearing high-tech motion sensing glove with glowing sensor 
nodes and fiber optic traces. Hand makes dramatic wuxia sword gesture, orchestrating 
thousands of blade-drones in the sky responding to finger movements. Split composition 
showing glove hand in foreground with drone swarm reacting in background like obedient 
flying swords. Cinematic kung fu movie aesthetic, dramatic lighting, slow motion gesture 
capture. Night sky filled with synchronized drones following the hand's command.
```

**Key elements:** Split composition, wuxia aesthetic, glove tech details, gesture-drone connection

**scene_005 (swarm coordination):**
```
Mesmerizing aerial view of massive drone swarm moving in perfect synchronization 
like a murmuration of starlings. Thousands of blade-shaped drones maintaining 
precise equal spacing, flowing as unified living organism. Fluid wave-like motion 
through night sky, drones shifting formation seamlessly while keeping perfect 
geometric distances. Bioluminescent glow effect, organic flowing movement patterns. 
Cinematic sweeping camera following the swarm's graceful coordinated dance.
```

**Key elements:** Nature metaphor (starlings), unified motion, precise spacing, organic flow, cinematic camera
