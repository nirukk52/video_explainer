# Video Explainer System

A system for generating high-quality explainer videos from technical documents. Transform research papers, articles, and documentation into engaging video content with automated narration and programmatic animations.

## Features

- **Project-Based Organization**: Self-contained projects with all files in one place
- **Document Parsing**: Parse Markdown documents with code blocks, equations, and images
- **Content Analysis**: Automatically extract key concepts and structure content for video
- **Script Generation**: Generate video scripts with visual cues and voiceover text
- **Text-to-Speech**: Integration with ElevenLabs and Edge TTS (with mock mode for development)
- **Manual Voiceover Support**: Import your own recordings with Whisper transcription
- **Sound Design**: Automated SFX planning, music layering, and audio mixing
- **AI Background Music**: Generate ambient background music using Meta's MusicGen model (MPS/CUDA/CPU)
- **Remotion Animations**: React-based programmatic video generation
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
python -m src.cli render <project>        # 6. Render final video

# Optional: Sound Design
python -m src.cli sound <project> plan    # Plan SFX for scenes
python -m src.cli sound <project> mix     # Mix voiceover + SFX + music
python -m src.cli music <project> generate  # Generate AI background music

# Iteration
python -m src.cli feedback <project> add "Make text larger in scene 1"
```

#### Script Generation

Generate a video script from input documents (Markdown files in `projects/<project>/input/`):

```bash
python -m src.cli script llm-inference           # Uses Claude Code LLM
python -m src.cli script llm-inference --mock    # Use mock for testing
python -m src.cli script llm-inference --duration 300  # Target 5 min video
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

#### Scene Generation (NEW)

Generate Remotion scene components (React/TypeScript) from the script:

```bash
python -m src.cli scenes llm-inference           # Generate all scenes
python -m src.cli scenes llm-inference --force   # Overwrite existing scenes
python -m src.cli scenes llm-inference --timeout 600  # 10 min per scene
python -m src.cli scenes llm-inference -v        # Verbose output
```

Output: `projects/<project>/scenes/*.tsx`, `styles.ts`, `index.ts`

This uses Claude Code to generate animated React components with:
- Remotion primitives (useCurrentFrame, interpolate, spring)
- Consistent styling from shared styles.ts
- Scene registry for dynamic loading

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

View or generate storyboard linking scenes with audio:

```bash
python -m src.cli storyboard llm-inference --view  # View existing
python -m src.cli storyboard llm-inference         # Generate new
```

Output: `projects/<project>/storyboard/storyboard.json`

#### Rendering

Render the final video:

```bash
python -m src.cli render llm-inference            # Default 1080p
python -m src.cli render llm-inference -r 4k      # 4K for YouTube
python -m src.cli render llm-inference -r 720p    # Quick preview
python -m src.cli render llm-inference --preview  # Fast preview
```

Output: `projects/<project>/output/video.mp4`

#### Sound Design

```bash
python -m src.cli sound llm-inference plan        # Plan SFX for all scenes
python -m src.cli sound llm-inference library --list    # List available sounds
python -m src.cli sound llm-inference library --download  # Generate library
python -m src.cli sound llm-inference mix         # Mix voiceover + SFX + music
```

#### AI Background Music

```bash
python -m src.cli music llm-inference generate    # Generate background music
python -m src.cli music llm-inference generate --duration 120  # 120s target
python -m src.cli music llm-inference generate --style "ambient electronic"
python -m src.cli music llm-inference info        # Show device support
```

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
│       ├── input/               # Source documents (Markdown)
│       │   └── *.md
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
│       └── output/              # Generated videos
│
├── src/                         # Core pipeline code
│   ├── cli/                     # CLI commands
│   ├── project/                 # Project loader module
│   ├── ingestion/               # Document parsing
│   ├── understanding/           # Content analysis (LLM)
│   ├── script/                  # Script generation
│   ├── scenes/                  # Scene component generation (NEW)
│   ├── audio/                   # TTS providers + transcription
│   ├── sound/                   # Sound design (SFX, music, mixing)
│   ├── music/                   # AI background music generation (MusicGen)
│   ├── voiceover/               # Voiceover generation
│   ├── storyboard/              # Storyboard system
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
│   │   └── types/               # TypeScript types
│   └── scripts/
│       └── render.mjs           # Headless rendering script
│
├── storyboards/                 # Storyboard schema
│   └── schema/
│       └── storyboard.schema.json
│
├── tests/                       # Test suite (425+ Python tests + 45 JS tests)
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

The project includes 470+ tests (425+ Python + 45 JavaScript).

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
- requests - HTTP client
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
