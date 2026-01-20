# Video Explainer System

A system for generating high-quality explainer videos from technical documents. Transform research papers, articles, and documentation into engaging video content with automated narration and programmatic animations.

## Example Videos Generated Using This System
- [How LLMs Actually Understand Images](https://youtu.be/PuodF4pq79g?si=4T0CV555qr89DSvY)
- [What Actually Happens When You Prompt AI?](https://youtu.be/nmBqcRl2tmM?si=FhCf4G5lKY3_rZ5I)
- [The Trick That Let AI See (Short)](https://www.youtube.com/shorts/vwI_gD4OG4I)

## Features

- **Project-Based Organization**: Self-contained projects with all files in one place
- **Multi-Format Input**: Parse Markdown, PDF documents, and web URLs with code blocks, equations, and images
- **Content Analysis**: Automatically extract key concepts and structure content for video
- **Script Generation**: Generate video scripts with visual cues and voiceover text
- **Text-to-Speech**: Integration with ElevenLabs and Edge TTS (with mock mode for development)
- **Manual Voiceover Support**: Import your own recordings with Whisper transcription
- **Sound Design**: Automated SFX planning, music layering, and audio mixing
- **AI Background Music**: Generate ambient background music using Meta's MusicGen model (MPS/CUDA/CPU)
- **Remotion Animations**: React-based programmatic video generation
- **Shorts Generation**: Create vertical shorts with TikTok-style captions and dark theme
- **CLI Pipeline**: Run each stage independently for easy iteration

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 20+
- FFmpeg

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd video_explainer

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install Python dependencies
pip install -e .

# Install Node.js dependencies for Remotion
cd remotion
npm install
cd ..
```

### CLI Usage

The CLI provides a complete pipeline for generating explainer videos:

```bash
# Project Management
python -m src.cli list                    # List all projects
python -m src.cli info <project>          # Show project info
python -m src.cli create <project_id>     # Create new project

# Content Generation Pipeline (run in order)
python -m src.cli script <project>        # 1. Generate script from input docs
python -m src.cli narration <project>     # 2. Generate narrations for scenes
python -m src.cli scenes <project>        # 3. Generate Remotion scene components
python -m src.cli voiceover <project>     # 4. Generate audio from narrations
python -m src.cli storyboard <project>    # 5. Create storyboard linking scenes + audio
python -m src.cli refine <project>        # 6. (Optional) AI-powered visual refinement
python -m src.cli render <project>        # 7. Render final video

# Or run the entire pipeline with a single command
python -m src.cli generate <project>      # Run all steps end-to-end

# Optional: Sound Design
python -m src.cli sound <project> plan    # Plan SFX for scenes
python -m src.cli sound <project> mix     # Mix voiceover + SFX + music
python -m src.cli music <project> generate  # Generate AI background music

# Iteration
python -m src.cli feedback <project> add "Make text larger in scene 1"
```

#### End-to-End Generation

Run the entire video generation pipeline with a single command:

```bash
python -m src.cli generate llm-inference           # Run all steps end-to-end
python -m src.cli generate llm-inference --force   # Regenerate everything
python -m src.cli generate llm-inference --mock    # Use mock LLM/TTS for testing
```

**Partial Pipeline Runs:**

```bash
# Resume from a specific step (skips earlier completed steps)
python -m src.cli generate llm-inference --from scenes

# Run only up to a specific step
python -m src.cli generate llm-inference --to voiceover

# Run a specific range of steps
python -m src.cli generate llm-inference --from narration --to storyboard
```

**Options:**

| Option | Description |
|--------|-------------|
| `--force` | Regenerate all steps, even if outputs exist |
| `--from STEP` | Start from this step (script, narration, scenes, voiceover, storyboard, render) |
| `--to STEP` | Stop after this step |
| `--resolution` | Output resolution: 4k, 1440p, 1080p (default), 720p, 480p |
| `--voice-provider` | TTS provider: elevenlabs, edge, mock |
| `--mock` | Use mock LLM and TTS (for testing without API calls) |
| `--timeout` | Timeout per scene generation in seconds (default: 300) |

The pipeline automatically:
- Skips steps that already have output files (use `--force` to override)
- Shows progress with step numbers and descriptions
- Stops gracefully if any step fails

#### Script Generation

Generate a video script from input documents. Supports multiple input formats:

**Supported Formats:**
- Markdown files (`.md`, `.markdown`)
- PDF documents (`.pdf`)
- Web URLs (`https://...`)

```bash
# From files in input/ directory (auto-detects .md and .pdf)
python -m src.cli script llm-inference           # Uses Claude Code LLM
python -m src.cli script llm-inference --mock    # Use mock for testing

# From a specific file (PDF or Markdown)
python -m src.cli script llm-inference --input /path/to/paper.pdf
python -m src.cli script llm-inference -i ~/docs/article.md

# From a web URL
python -m src.cli script llm-inference --url https://example.com/blog-post

# Additional options
python -m src.cli script llm-inference --duration 300  # Target 5 min video
python -m src.cli script llm-inference --continue-on-error  # Skip failed files
python -m src.cli script llm-inference -v        # Verbose output
```

Output: `projects/<project>/script/script.json`

#### Narration Generation

Generate scene narrations from the script:

```bash
python -m src.cli narration llm-inference        # Uses Claude Code LLM
python -m src.cli narration llm-inference --mock # Use mock for testing
python -m src.cli narration llm-inference --force  # Overwrite existing
python -m src.cli narration llm-inference --topic "Custom Topic"
```

Output: `projects/<project>/narration/narrations.json`

#### Scene Generation

Generate Remotion scene components (React/TypeScript) from the script:

```bash
python -m src.cli scenes llm-inference           # Generate all scenes
python -m src.cli scenes llm-inference --force   # Overwrite existing scenes
python -m src.cli scenes llm-inference --scene 6 # Regenerate just scene 6
python -m src.cli scenes llm-inference --scene HookScene.tsx  # Regenerate by filename
python -m src.cli scenes llm-inference --timeout 600  # 10 min per scene
python -m src.cli scenes llm-inference -v        # Verbose output
```

Output: `projects/<project>/scenes/*.tsx`, `styles.ts`, `index.ts`

This uses Claude Code to generate animated React components with:
- Remotion primitives (useCurrentFrame, interpolate, spring)
- Consistent styling from shared styles.ts
- Scene registry for dynamic loading
- **Automatic validation and self-correction**: The generator validates each scene and automatically retries with error feedback if validation fails

**Syncing Scenes to Updated Voiceover:**

If you re-record or modify the voiceover, use `--sync` to update scene timing without regenerating all visual content:

```bash
python -m src.cli scenes llm-inference --sync              # Sync all scenes
python -m src.cli scenes llm-inference --sync --scene HookScene.tsx  # Sync specific scene
```

This is much faster than full regeneration - it only updates timing values (frame numbers, animation triggers) while preserving all visual structure and animations.

#### Voiceover Generation

Generate audio files from narrations:

```bash
python -m src.cli voiceover llm-inference        # Use configured TTS
python -m src.cli voiceover llm-inference --mock # Mock audio for testing
python -m src.cli voiceover llm-inference --force  # Regenerate all
python -m src.cli voiceover llm-inference --scene scene1_hook  # Single scene
```

Output: `projects/<project>/voiceover/*.mp3`, `manifest.json`

#### Storyboard

Generate or view the storyboard that links scenes with audio:

```bash
python -m src.cli storyboard llm-inference         # Generate from narrations
python -m src.cli storyboard llm-inference --view  # View existing storyboard
python -m src.cli storyboard llm-inference --force # Regenerate storyboard
python -m src.cli storyboard llm-inference -v      # Verbose output
```

The storyboard combines:
- Scene metadata from narrations (titles, IDs)
- Audio durations from voiceover manifest
- Scene types from generated Remotion components

Output: `projects/<project>/storyboard/storyboard.json`

#### Refinement (3-Phase Process)

The refinement system helps elevate video quality to professional standards (3Blue1Brown / Veritasium level) through a 3-phase process:

1. **Phase 1: Analyze** - Gap analysis that generates patches to fix script issues
2. **Phase 2: Script** - Loads patches from Phase 1, adds storytelling refinements, applies changes
3. **Phase 3: Visual** - AI-powered visual inspection and fixes

**Key Design: Phases 1 and 2 are connected.** Phase 1 outputs patches that Phase 2 consumes and applies.

**Prerequisites:**
- For Phase 1: Input source material (`input/*.md` or `input/*.txt`) and narrations
- For Phase 2: Run Phase 1 first to generate patches
- For Phase 3: Scene components generated (`scenes` command) and storyboard created

```bash
# Phase 1: Gap Analysis (generates patches)
python -m src.cli refine llm-inference --phase analyze

# Phase 2: Apply patches + storytelling refinement
python -m src.cli refine llm-inference --phase script              # Interactive approval
python -m src.cli refine llm-inference --phase script --batch-approve  # Auto-approve all

# Phase 3: Visual Refinement (inspect and fix scenes)
python -m src.cli refine llm-inference --phase visual
python -m src.cli refine llm-inference --phase visual --scene 3  # Specific scene

# Default (no --phase): runs visual refinement
python -m src.cli refine llm-inference
```

**Options:**

| Option | Description |
|--------|-------------|
| `--phase` | Phase to run: `analyze`, `script`, or `visual` (default: visual) |
| `--scene N` | Refine only scene N (1-indexed, visual phase only) |
| `--batch-approve` | Auto-approve all suggested changes (script phase) |
| `--live` | Stream Claude Code output in real-time |
| `-v, --verbose` | Show detailed progress |

---

##### Phase 1: Gap Analysis (`--phase analyze`)

Compares source material against the generated script to identify gaps and **generates patches** to fix them:
- **Missing concepts**: Important topics from source not covered in script
- **Shallow coverage**: Concepts mentioned but not explained deeply enough
- **Narrative gaps**: Logical jumps between scenes that confuse viewers

```bash
python -m src.cli refine llm-inference --phase analyze
```

**How it works:**
1. Loads source material from `input/*.md` or `input/*.txt`
2. Extracts key concepts with importance ratings (critical, high, medium, low)
3. Analyzes script coverage depth (not_covered, mentioned, explained, deep_dive)
4. Identifies narrative gaps between scenes
5. **Generates patches** to fix identified gaps

**Patch Types:**

| Type | Description |
|------|-------------|
| `add_scene` | Insert a new scene to cover missing concepts |
| `modify_scene` | Update existing scene content |
| `expand_scene` | Add more detail to shallow coverage |
| `add_bridge` | Add transitional content between scenes |

**Output:** `projects/<project>/refine/gap_analysis.json` (includes `patches` array)

Returns exit code 1 if critical gaps are found (missing critical concepts or high-severity narrative gaps).

---

##### Phase 2: Script Refinement (`--phase script`)

Loads patches from Phase 1, generates additional storytelling refinements, and applies approved changes to the script:

```bash
python -m src.cli refine llm-inference --phase script              # Interactive approval
python -m src.cli refine llm-inference --phase script --batch-approve  # Auto-approve
```

**How it works:**
1. **Loads patches from Phase 1** (`gap_analysis.json`)
2. Analyzes each scene against 10 narration principles
3. Generates additional storytelling patches for quality issues
4. Combines Phase 1 patches + storytelling patches
5. **Interactive mode**: Presents each patch for approval (y/n/e to edit)
6. **Batch mode**: Auto-approves all patches
7. Applies approved patches to update `script.json` and `narrations.json`

**10 Narration Principles:**

1. **Hook in the first sentence** - Grab attention immediately with surprising facts, questions, or stakes
2. **Build tension before release** - Create anticipation before revealing solutions
3. **Seamless transitions** - Connect scenes with callback phrases that bridge ideas
4. **One insight per scene** - Focus each scene on a single memorable takeaway
5. **Concrete analogies** - Use familiar comparisons to explain abstract concepts
6. **Emotional beats** - Include moments that create wonder, surprise, or satisfaction
7. **Match length to complexity** - Simple ideas = short scenes, complex ideas = more time
8. **Rhetorical questions** - Plant questions in viewers' minds before answering
9. **Clear stakes** - Explain why the audience should care
10. **Strong scene endings** - End with memorable phrases or setup for next scene

**Scoring weights:**
- Hook strength: 15%
- Flow quality: 15%
- Tension/buildup: 15%
- Insight clarity: 20%
- Emotional engagement: 15%
- Factual accuracy: 10%
- Length appropriateness: 10%

**Output:** Updates `script/script.json` and `narration/narrations.json` with approved patches

---

##### Phase 3: Visual Refinement (`--phase visual`)

AI-powered visual inspection using Claude Code with browser access.

```bash
python -m src.cli refine llm-inference --phase visual
python -m src.cli refine llm-inference --phase visual --scene 3 --live
```

**How it works:**

1. **Beat Parsing**: Narration is analyzed to identify key visual moments (beats)
2. **Visual Inspection**: Claude Code opens the scene in Remotion Studio (SingleScenePlayer)
3. **Quality Assessment**: Screenshots are analyzed against 11 guiding principles:
   - Show Don't Tell - Use visuals, not just text
   - Animation Reveals - Animate elements in sync with narration
   - Progressive Disclosure - Show info as it's mentioned
   - Text Complements - Text supports visuals, doesn't replace
   - Visual Hierarchy - Guide viewer's eye
   - Breathing Room - Don't clutter
   - Purposeful Motion - Every animation has meaning
   - Emotional Resonance - Connect with viewer
   - Professional Polish - Clean, consistent
   - Sync with Narration - Timing matches speech
   - Screen Space Utilization - Use full canvas effectively
4. **Fix Application**: Claude Code edits the scene component to fix identified issues
5. **Verification**: New screenshots verify improvements

**Technical Details:**

The refine command uses a `SingleScenePlayer` Remotion composition that loads individual scenes starting at frame 0, eliminating the need to navigate through the entire video.

**Output:** Scene files are modified in place (`projects/<project>/scenes/*.tsx`)

#### Rendering

Render the final video:

```bash
python -m src.cli render llm-inference            # Default 1080p
python -m src.cli render llm-inference -r 4k      # 4K for YouTube
python -m src.cli render llm-inference -r 720p    # Quick preview
python -m src.cli render llm-inference --preview  # Fast preview
python -m src.cli render llm-inference --fast     # Faster encoding (lower quality)
python -m src.cli render llm-inference --concurrency 8  # Custom thread count
```

**Performance options:**
- `--fast` - Uses faster x264 preset and lower JPEG quality for quicker renders
- `--concurrency N` - Override auto-detected thread count (default: 75% of CPU cores)

Output: `projects/<project>/output/video.mp4`

#### Shorts Generation

Generate vertical shorts (1080x1920) optimized for YouTube Shorts, Instagram Reels, and TikTok.

**Prerequisites:** Run `script` and `narration` commands first.

**Full pipeline (recommended):**

```bash
# Generate everything end-to-end
python -m src.cli short generate llm-inference

# Then render
python -m src.cli render llm-inference --short
```

**Or run individual steps:**

```bash
# 1. Generate short script (hook analysis + condensed narration)
python -m src.cli short script llm-inference

# 2. Generate vertical scene components
python -m src.cli short scenes llm-inference

# 3. Generate voiceover (TTS)
python -m src.cli short voiceover llm-inference

# 4. Create storyboard with beat timing
python -m src.cli short storyboard llm-inference

# 5. (Optional) Generate punchy background music
python -m src.cli music llm-inference short

# 6. Render the short
python -m src.cli render llm-inference --short
```

**Manual voiceover workflow:**

```bash
# Export recording script for voice actor
python -m src.cli short voiceover llm-inference --export-script

# After recording, process with Whisper for word timestamps
python -m src.cli short voiceover llm-inference --audio recording.mp3

# Continue with storyboard and render
python -m src.cli short storyboard llm-inference
python -m src.cli render llm-inference --short
```

**Timing sync (when voiceover changes):**

When you re-record or modify the voiceover, scene animations need to sync with the new timing. The timing sync system automates this:

```bash
# 1. Process new voiceover (generates word timestamps)
python -m src.cli short voiceover llm-inference --audio new_recording.mp3

# 2. Regenerate storyboard (updates beat timing)
python -m src.cli short storyboard llm-inference --skip-custom-scenes

# 3. Regenerate timing.ts (syncs scene animations to new word timestamps)
python -m src.cli short timing llm-inference

# 4. Preview - animations are now synced!
cd remotion && npm run dev
```

**How it works:**

1. **Phase markers** in storyboard link animation phases to spoken words:
   ```json
   "phase_markers": [
     {"id": "gptAppear", "end_word": "GPT,", "description": "GPT logo appears"},
     {"id": "phase1End", "end_word": "insight.", "description": "End of intro"}
   ]
   ```

2. **Timing generator** finds word timestamps and calculates frame numbers:
   ```bash
   python -m src.cli short timing llm-inference
   # Generates: projects/<project>/short/default/scenes/timing.ts
   ```

3. **Scene components** import timing constants instead of hardcoded values:
   ```typescript
   import { TIMING } from "./timing";
   const gptSpring = spring({ frame: localFrame - TIMING.beat_1.gptAppear, ... });
   ```

This eliminates the need to manually update scene files when voiceover timing changes.

**Script options:**

| Option | Description |
|--------|-------------|
| `--duration` | Target duration in seconds (default: 45, range: 30-60) |
| `--variant` | Variant name for multiple shorts from same project |
| `--scenes` | Override scene selection (comma-separated scene IDs) |
| `--force` | Force regenerate even if files exist |
| `--mock` | Use mock LLM for testing |

**Voiceover options:**

| Option | Description |
|--------|-------------|
| `--provider` | TTS provider: `elevenlabs`, `edge`, `mock` (default: edge) |
| `--export-script` | Export recording script for manual voiceover |
| `--audio` | Process manually recorded audio with Whisper |
| `--whisper-model` | Whisper model size: `tiny`, `base`, `small`, `medium`, `large` |

**Features:**
- Single-word captions (72px bold, uppercase, glow effect)
- Dark gradient theme optimized for mobile
- Phase-based animations synced with voiceover
- Custom React scene generation for each beat
- Automatic hook selection from most intriguing scenes

Output: `projects/<project>/short/<variant>/`

**Rendering Shorts:**

```bash
python -m src.cli render llm-inference --short              # Render at 1080p (1080x1920)
python -m src.cli render llm-inference --short -r 4k        # Render at 4K (2160x3840)
python -m src.cli render llm-inference --short --variant teaser  # Render specific variant
python -m src.cli render llm-inference --short --fast       # Faster encoding
```

#### Sound Design

```bash
python -m src.cli sound llm-inference plan        # Plan SFX for all scenes
python -m src.cli sound llm-inference library --list    # List available sounds
python -m src.cli sound llm-inference library --download  # Generate library
python -m src.cli sound llm-inference mix         # Mix voiceover + SFX + music
```

#### AI Background Music

Generate ambient background music for full videos using Meta's MusicGen:

```bash
python -m src.cli music llm-inference generate    # Generate background music
python -m src.cli music llm-inference generate --duration 120  # 120s target
python -m src.cli music llm-inference generate --style "ambient electronic"
python -m src.cli music llm-inference info        # Show device support & presets
```

**Shorts Music Generation:**

Generate punchy, energetic background music optimized for YouTube Shorts:

```bash
python -m src.cli music llm-inference short       # Generate punchy music for short
python -m src.cli music llm-inference short --variant teaser  # Specific variant
python -m src.cli music llm-inference short --style "upbeat electronic, driving bass"
```

The shorts music generator:
- Analyzes beat captions to detect content mood (tech, dramatic, hook, etc.)
- Detects emotional arc (problem → solution journey, tension, triumphant)
- Uses punchy, attention-grabbing presets (120 BPM, bold synths, driving rhythm)
- Applies slightly higher volume (0.35 vs 0.3) for mobile playback
- Enhances prompt based on detected mood (building energy, tension release, etc.)

**Mood Detection:**
| Mood | Trigger | Music Enhancement |
|------|---------|-------------------|
| Journey | Problem + solution detected | Building energy, tension to release |
| Tension | Only problems detected | Building tension, suspenseful |
| Triumphant | Only solutions detected | Uplifting, positive energy |
| Energetic | Default | Standard punchy preset |

#### Fact Checking

Thoroughly verify the accuracy of scripts and narrations against source material:

```bash
python -m src.cli factcheck llm-inference        # Run full fact check
python -m src.cli factcheck llm-inference --mock # Use mock for testing
python -m src.cli factcheck llm-inference -v     # Verbose output
python -m src.cli factcheck llm-inference --no-save  # Don't save report
```

The fact checker:
- Compares all claims against source documents (Markdown, PDF)
- Uses web search to verify facts not in source material
- Identifies factual errors, outdated info, missing context
- Provides severity ratings (critical/high/medium/low/info)
- Suggests corrections with source references
- Generates an accuracy score

Output: `projects/<project>/factcheck/report.json`

#### Feedback Processing

```bash
python -m src.cli feedback llm-inference add "Make text larger in scene 1"
python -m src.cli feedback llm-inference add "Fix timing" --dry-run
python -m src.cli feedback llm-inference list
python -m src.cli feedback llm-inference show fb_0001_1234567890
```

### Resolution Options

| Preset | Resolution | Use Case |
|--------|------------|----------|
| 4k     | 3840x2160  | YouTube/Final export |
| 1440p  | 2560x1440  | High quality |
| 1080p  | 1920x1080  | Default |
| 720p   | 1280x720   | Development |
| 480p   | 854x480    | Quick preview |

## Project Structure

```
video_explainer/
├── projects/                    # Self-contained video projects
│   └── llm-inference/           # Example: LLM Inference video
│       ├── config.json          # Project configuration
│       ├── input/               # Source documents (Markdown, PDF)
│       │   ├── *.md
│       │   └── *.pdf
│       ├── script/              # Generated scripts
│       │   └── script.json
│       ├── narration/           # Scene narration scripts
│       │   └── narrations.json
│       ├── scenes/              # Generated Remotion components
│       │   ├── index.ts         # Scene registry
│       │   ├── styles.ts        # Shared styles
│       │   └── *Scene.tsx       # Scene components
│       ├── voiceover/           # Generated audio files
│       │   ├── manifest.json
│       │   └── *.mp3
│       ├── storyboard/          # Storyboard definitions
│       │   └── storyboard.json
│       ├── music/               # AI-generated background music
│       │   └── background.mp3
│       ├── factcheck/           # Fact check reports
│       │   └── report.json
│       ├── short/               # Shorts variants
│       │   └── default/
│       │       ├── short_script.json
│       │       ├── scenes/      # Custom React components
│       │       ├── voiceover/   # Short voiceover audio
│       │       └── storyboard/  # Shorts storyboard
│       └── output/              # Generated videos
│
├── src/                         # Core pipeline code
│   ├── cli/                     # CLI commands
│   ├── project/                 # Project loader module
│   ├── ingestion/               # Document parsing (MD, PDF, URL)
│   ├── understanding/           # Content analysis (LLM)
│   ├── script/                  # Script generation
│   ├── scenes/                  # Scene component generation
│   ├── audio/                   # TTS providers + transcription
│   ├── sound/                   # Sound design (SFX, music, mixing)
│   ├── music/                   # AI background music generation (MusicGen)
│   ├── voiceover/               # Voiceover generation
│   ├── storyboard/              # Storyboard system
│   ├── factcheck/               # Fact checking with web verification
│   ├── short/                   # Shorts generation
│   ├── feedback/                # Feedback processing
│   ├── refine/                  # Visual refinement (AI-powered inspection)
│   ├── animation/               # Animation rendering
│   ├── composition/             # Video assembly
│   ├── pipeline/                # End-to-end orchestration
│   ├── config.py                # Configuration management
│   └── models.py                # Pydantic data models
│
├── remotion/                    # Remotion project (React animations)
│   ├── src/
│   │   ├── components/          # Reusable animation components
│   │   ├── scenes/              # Scene compositions
│   │   ├── shorts/              # Shorts player and components
│   │   └── types/               # TypeScript types
│   └── scripts/
│       └── render.mjs           # Headless rendering script
│
├── storyboards/                 # Storyboard schema
│   └── schema/
│       └── storyboard.schema.json
│
├── tests/                       # Test suite (844 Python + 149 JS tests)
├── config.yaml                  # Global configuration
└── pyproject.toml               # Python package configuration
```

## Pipeline Architecture

```
Document → Parse → Analyze → Script → TTS → Storyboard → Animation → Compose → Video
                                       │         ↑
                                       │    (JSON schema)
                                       └─────────┘
                                    (word timestamps)
```

### Key Insight: TTS Before Storyboard

TTS generation happens BEFORE storyboard creation because we need audio timing (word-level timestamps) to sync visuals precisely to narration.

## Configuration

### Project Configuration (projects/*/config.json)

```json
{
  "id": "my-video",
  "title": "My Explainer Video",
  "video": {
    "resolution": { "width": 1920, "height": 1080 },
    "fps": 30,
    "target_duration_seconds": 180
  },
  "tts": {
    "provider": "elevenlabs",
    "voice_id": "your-voice-id"
  },
  "style": {
    "background_color": "#0f0f1a",
    "primary_color": "#00d9ff"
  }
}
```

### Global Configuration (config.yaml)

```yaml
llm:
  provider: claude-code  # claude-code | mock | anthropic | openai
  model: claude-sonnet-4-20250514

tts:
  provider: mock  # mock | elevenlabs | edge
  voice_id: null

video:
  width: 1920
  height: 1080
  fps: 30
```

Note: The default LLM provider is `claude-code`, which uses the Claude Code CLI for generation. Use `--mock` flag for testing without API calls.

### Environment Variables

- `ANTHROPIC_API_KEY` - For Claude LLM provider
- `OPENAI_API_KEY` - For OpenAI LLM provider
- `ELEVENLABS_API_KEY` - For ElevenLabs TTS

## Testing

The project includes 990+ tests (844 Python + 149 JavaScript).

### Python Tests

```bash
# Run all Python tests
pytest tests/ -v

# Run without slow tests (no network required)
pytest tests/ -v -m "not slow"

# Run specific test file
pytest tests/test_project.py -v

# Run CLI tests
pytest tests/test_cli.py -v
```

### JavaScript Tests (Remotion)

```bash
cd remotion

# Run all tests
npm test

# Run tests in watch mode
npm run test:watch
```

## Development

### Remotion Studio

Start the Remotion studio for animation development:

```bash
cd remotion
npm run dev
```

Opens at `http://localhost:3000` for previewing compositions.

### Creating New Animation Components

Add components in `remotion/src/components/`:

```tsx
import React from "react";
import { interpolate, useCurrentFrame } from "remotion";

interface MyComponentProps {
  title: string;
}

export const MyComponent: React.FC<MyComponentProps> = ({ title }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 30], [0, 1], {
    extrapolateRight: "clamp",
  });

  return <div style={{ opacity }}>{title}</div>;
};
```

## Visual Style

Default theme for technical content:

| Element | Color | Hex |
|---------|-------|-----|
| Background | Dark Slate | `#0f0f1a` |
| Compute/Data | Cyan | `#00d9ff` |
| Memory | Orange | `#ff6b35` |
| Optimization | Green | `#00ff88` |
| Problems | Red | `#ff4757` |

Typography: Inter/SF Pro for text, JetBrains Mono for code

## Dependencies

### Python (see pyproject.toml)

- pydantic - Data validation
- rich - CLI interface
- pyyaml - Configuration
- edge-tts - Microsoft Edge TTS
- httpx - HTTP client
- pymupdf - PDF parsing
- beautifulsoup4 - HTML parsing (for URL content)
- transformers - MusicGen model for AI background music
- torch - PyTorch backend (MPS/CUDA/CPU)

### Node.js (see remotion/package.json)

- remotion - Video rendering
- @remotion/renderer - Headless rendering
- react - UI components
- vitest - JavaScript testing framework

### System

- FFmpeg - Video processing
- Node.js 20+ - Remotion runtime

## License

MIT License - see LICENSE file for details.

## Acknowledgments

- [Remotion](https://remotion.dev/) - React-based video generation
- [ElevenLabs](https://elevenlabs.io/) - Text-to-Speech
- [MusicGen](https://github.com/facebookresearch/audiocraft) - AI music generation (Meta)
- [FFmpeg](https://ffmpeg.org/) - Video processing
