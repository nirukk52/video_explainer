# Video Explainer System - Progress Tracker

## Quick Context for Future Sessions

### One-Line Summary
Building a system to generate high-quality explainer videos from technical documents using Remotion (React-based) programmatic animations with project-based organization.

### Prompt for New Claude Code Session
```
I'm continuing work on the Video Explainer system. This project generates
explainer videos from technical documents.

Key context:
- Design doc: design.md (full architecture and visual style guide)
- Progress: progress.md (current state and next steps)
- README: README.md (setup and CLI usage)

Current phase: Phase 4.5 - Feedback System
- Phase 1 MVP: COMPLETE (112 tests)
- Phase 2 First Video: COMPLETE
- Phase 3 Automated Animation: COMPLETE
- Phase 3.5 Quality Focus: COMPLETE
- Phase 4 Project Organization: COMPLETE
- Phase 4.5 Feedback System: COMPLETE (397 tests: 352 Python + 45 JavaScript)
  - Claude Code LLM Provider for intelligent file modifications
  - Feedback CLI (add, list, show) for iterative improvements
  - Preview branch workflow for safe changes
  - Feedback history tracking with JSON persistence

Key commands:
  source .venv/bin/activate && pytest tests/ -v  # Run Python tests (352 passing)
  cd remotion && npm test                         # Run JS tests (45 passing)
  python -m src.cli list                          # List projects
  python -m src.cli info llm-inference            # Show project info
  python -m src.cli voiceover llm-inference --mock # Generate voiceovers
  python -m src.cli render llm-inference          # Render video (1080p)
  python -m src.cli render llm-inference -r 4k    # Render in 4K for YouTube
  python -m src.cli feedback llm-inference add "..." # Process feedback
  cd remotion && npm run dev                      # Start Remotion studio

Key directories:
  projects/llm-inference/                         # Example video project
  src/cli/                                        # CLI commands
  src/project/                                    # Project loader
  src/feedback/                                   # Feedback system
  remotion/                                       # Remotion React components

Check "Next Actions" section below for current tasks.
```

---

## Project Overview

| Aspect | Details |
|--------|---------|
| **Goal** | Generate high-quality explainer videos from technical content |
| **First Topic** | LLM Inference (Prefill/Decode/KV Cache) |
| **Target Duration** | 3-4 minutes |
| **Animation Tool** | Remotion (React-based, programmatic rendering) |
| **TTS** | ElevenLabs (with word timestamps) or Edge TTS or Mock |
| **LLM** | Mock responses during dev, Claude/GPT-4 for production |
| **Video Specs** | 1080p, 30fps, MP4 |
| **Organization** | Project-based (each video in projects/ directory) |

---

## Current Status

### Completed (Phase 1 MVP)
- [x] Project structure initialized
- [x] Git repository created
- [x] Python package setup (pyproject.toml)
- [x] Configuration system (config.py, config.yaml)
- [x] Core data models (models.py)
- [x] Content ingestion module (markdown parser)
- [x] Mock LLM provider with realistic responses
- [x] Content understanding/analyzer module
- [x] Script generation module with visual cues
- [x] CLI review interface (rich-based)
- [x] ElevenLabs TTS integration (with mock for testing)
- [x] Video composition with FFmpeg
- [x] Dockerfile for containerization
- [x] End-to-end tests
- [x] **112 tests, all passing**

### Completed (Phase 2 - First Real Video)
- [x] Video generation pipeline orchestrator (src/pipeline/)
- [x] Animation renderer module (src/animation/)
- [x] Motion Canvas FFmpeg plugin integration
- [x] MockTTS generates valid audio files via FFmpeg
- [x] Real ElevenLabs TTS integration tested
- [x] **First real explainer video generated!**

### Completed (Phase 3 - Automated Animation)
- [x] Remotion integration (React-based programmatic rendering)
- [x] Abstract AnimationRenderer interface for swappable backends
- [x] RemotionRenderer implementation with script-to-props conversion
- [x] Animation components library (TitleCard, TokenGrid, ProgressBar, TextReveal)
- [x] SceneRenderer to map visual cues to React components
- [x] Headless rendering via `@remotion/renderer` and `@remotion/bundler`
- [x] Full E2E pipeline generating videos from scripts
- [x] **119 tests, all passing**

### Completed (Phase 3.5 - Quality & Generalization)
- [x] Identified quality issues with templated animations
- [x] Designed storyboard-first workflow (TTS → Storyboard → Animation)
- [x] Created detailed storyboard for Prefill vs Decode scene
- [x] Built custom Remotion components (Token, TokenRow, GPUGauge)
- [x] Built PrefillDecodeScene hand-crafted demo
- [x] Defined JSON schema for storyboards
- [x] Built StoryboardPlayer (runtime storyboard interpreter)
- [x] Created Python storyboard module (loader, validator, renderer)
- [x] Add TTS word-level timestamps via ElevenLabs API
- [x] Build StoryboardGenerator (LLM-assisted)
- [x] **187 tests passing**

### Completed (Phase 4 - Project Organization)
- [x] Project-based organization (projects/ directory)
- [x] CLI module for independent pipeline stages (src/cli/)
- [x] Project loader module (src/project/)
- [x] JSON configuration files (config.json per project)
- [x] Narrations moved to project-specific JSON files
- [x] Cleanup of deprecated code (removed LLM-specific content from shared modules)
- [x] Cleanup of old scattered files (output/, remotion/src/videos/, etc.)
- [x] Updated tests for generic mock responses
- [x] Updated documentation (README.md, design.md, progress.md)
- [x] Data-driven video architecture with scene registry
- [x] Resolution configuration (4K to 480p) for YouTube export
- [x] JavaScript testing with vitest for render utilities
- [x] Comprehensive CLI tests (36 tests)
- [x] Refactored render.mjs with testable utility functions
- [x] **322 tests passing (277 Python + 45 JavaScript)**

### Completed (Phase 4.5 - Feedback System)
- [x] ClaudeCodeLLMProvider using Claude Code CLI in headless mode
- [x] Feedback module (src/feedback/) with models, store, processor
- [x] Feedback CLI commands (add, list, show)
- [x] Preview branch workflow for safe file modifications
- [x] Feedback history tracking with JSON persistence
- [x] 75 new tests (40 feedback + 35 Claude Code provider)
- [x] **397 tests passing (352 Python + 45 JavaScript)**

### Completed (Phase 5 - Sound Design System)
- [x] Frame-accurate SFX system (sfx_cues in storyboard.json)
- [x] 10 focused procedurally generated sounds (numpy-based)
- [x] Remotion-native SFX playback at exact frame offsets
- [x] Storyboard schema extended with sfx_cues array
- [x] CLI commands (`sound library --list`, `--generate`)
- [x] Manual voiceover support with Whisper transcription
- [x] Auto-sync storyboard durations with voiceover lengths
- [x] Sound design for llm-inference video (100+ SFX cues, 16 scenes)
- [x] 21 sound module tests
- [x] **402+ tests passing (357+ Python + 45 JavaScript)**

### Next Steps (Phase 6 - Production Ready)
- [ ] Enable real LLM API (Anthropic/OpenAI) for dynamic content analysis
- [ ] Add more animation components (code highlights, equations, diagrams)
- [ ] Build web interface for easier use
- [ ] Cloud deployment (Docker/Kubernetes)
- [ ] Support for more input formats (PDF, URL scraping)

---

## Architecture Summary

```
Pipeline (Project-Based):

projects/llm-inference/
    ├── config.json           # Project configuration
    ├── narration/            # Scene narrations
    │   └── narrations.json
    ├── voiceover/            # Generated audio
    │   ├── manifest.json
    │   └── *.mp3
    ├── storyboard/           # Visual planning
    │   └── storyboard.json
    └── output/               # Final videos

Pipeline Flow:
Document → Parse → Analyze → Script → TTS → Storyboard → Animation → Compose → Video
                                       │         ↑
                                       │    (JSON schema)
                                       └─────────┘
                                    (word timestamps)

Key modules:
├── src/
│   ├── cli/              # CLI commands (list, info, voiceover, render, feedback)
│   ├── project/          # Project loader module
│   ├── feedback/         # Feedback system (models, store, processor)
│   ├── ingestion/        # Document parsing
│   ├── understanding/    # Content analysis (LLM providers)
│   ├── script/           # Script generation
│   ├── audio/            # TTS providers (ElevenLabs, Edge, Mock)
│   ├── voiceover/        # Voiceover generation with timestamps
│   ├── storyboard/       # Storyboard system
│   ├── animation/        # Animation rendering (Remotion)
│   ├── composition/      # Video assembly
│   └── pipeline/         # End-to-end orchestration
├── remotion/             # Remotion project
│   ├── src/
│   │   ├── components/   # Animation components
│   │   ├── scenes/       # Scene compositions
│   │   └── types/        # TypeScript types
│   └── scripts/
│       ├── render.mjs        # Headless rendering
│       ├── render-utils.mjs  # Testable utility functions
│       └── render-utils.test.mjs  # JavaScript tests
└── tests/                    # 352 Python tests + 45 JS tests
```

---

## Key Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Animation Library | Remotion (React) | Headless rendering, programmatic, actively maintained |
| Previous Choice | Motion Canvas | Moved away - no native headless rendering support |
| Project Organization | Self-contained projects | Each video in `projects/` with all assets |
| Configuration | JSON files | Human readable, easy to edit |
| Pipeline Execution | CLI commands | Run stages independently, easier iteration |
| TTS Provider | ElevenLabs + Edge TTS | High quality with word timestamps |
| LLM During Dev | Mock responses | Save money, test pipeline |
| Video Resolution | 1080p default, 4K for export | CLI supports 4k, 1440p, 1080p, 720p, 480p |

---

## Visual Style (for LLM Inference topic)

```
Background: #0f0f1a (dark slate)
Compute/Data: #00d9ff (cyan)
Memory: #ff6b35 (orange)
Optimization: #00ff88 (green)
Problems: #ff4757 (red)

Typography: Inter/SF Pro for text, JetBrains Mono for code
Animation: easeInOutCubic, 0.3-0.5s transitions
```

---

## Running the Project

```bash
# Activate virtual environment
source .venv/bin/activate

# Run Python tests (352 tests)
pytest tests/ -v

# Run JavaScript tests (45 tests)
cd remotion && npm test

# List projects
python -m src.cli list

# Show project info
python -m src.cli info llm-inference

# Generate voiceovers (mock)
python -m src.cli voiceover llm-inference --mock

# Render video (default 1080p)
python -m src.cli render llm-inference

# Render in 4K for YouTube
python -m src.cli render llm-inference --resolution 4k

# Render in 720p for faster development
python -m src.cli render llm-inference -r 720p

# Start Remotion studio for development
cd remotion && npm run dev

# Create a new project
python -m src.cli create my-new-video --title "My New Video"

# Process feedback (uses Claude Code CLI)
python -m src.cli feedback llm-inference add "Make text larger in scene 1"

# Analyze feedback without applying (dry run)
python -m src.cli feedback llm-inference add "Fix timing" --dry-run

# List all feedback for a project
python -m src.cli feedback llm-inference list

# Show details of a specific feedback item
python -m src.cli feedback llm-inference show fb_0001_1234567890
```

---

## Dependencies

### Python (pyproject.toml)
- pydantic - Data validation
- rich - CLI interface
- pyyaml - Configuration
- edge-tts - Microsoft Edge TTS
- requests - HTTP client

### Node.js (remotion/package.json)
- remotion - Video rendering
- @remotion/renderer - Headless rendering
- react - UI components
- vitest - JavaScript testing framework

### System
- FFmpeg - Video processing
- Node.js 20+ - Remotion runtime
- Python 3.10+ - Pipeline runtime

---

## Next Actions

### Immediate
1. **Create more video content** - Use the pipeline to create additional explainer videos

### Future (Phase 5)
2. **Enable real LLM API** - Switch from mock to Claude/GPT-4 for dynamic
   content analysis and script generation

3. **Add more animation components** - Create components for:
   - Code block highlighting with syntax colors
   - Mathematical equation rendering
   - Diagram animations (flowcharts, architecture)

4. **Create web interface** - Simple UI for uploading documents

5. **Cloud deployment** - Docker/Kubernetes for production

---

## Notes for Future Sessions

- Always run tests before committing:
  - Python: `pytest tests/ -v` (352 tests)
  - JavaScript: `cd remotion && npm test` (45 tests)
- Projects are self-contained in `projects/` directory
- Use CLI commands for independent pipeline execution
- Mock providers available for development without API costs
- Human review checkpoints at: script, storyboard, final
- Use `--resolution 4k` for YouTube-ready exports
- Use `--resolution 720p` for faster development iterations
- Use `feedback add --dry-run` to analyze feedback without applying changes
- Feedback creates preview branches for safe review before merging

---

## Commits Made

| Date | Commit | Description |
|------|--------|-------------|
| Dec 2024 | d770b7c | Initial project setup with ingestion, understanding, and script modules |
| Dec 2024 | 609b95a | Add CLI review interface and Motion Canvas animation setup |
| Dec 2024 | b3fc60d | Add TTS and video composition modules |
| Dec 2024 | 1237125 | Complete Phase 1 MVP with Dockerfile and E2E tests |
| Dec 2024 | 43799de | Add video generation pipeline and first video output |
| Dec 2024 | ff2b337 | Add comprehensive README.md |
| Dec 2024 | 41ceadc | Complete Phase 2: First real explainer video generated |
| Dec 2024 | 50dbc3f | Refactor pipeline: remove one-off scripts, use config-based providers |
| Dec 2024 | - | Phase 3: Remotion integration for automated animation rendering |
| Dec 2024 | - | Phase 3.5: Storyboard system, quality focus, hand-crafted demo |
| Dec 2024 | - | Phase 4: Project-based organization, CLI, cleanup (241 tests) |

---

*Last Updated: December 2024*
*Session: Phase 4.5 - Added Claude Code LLM Provider, Feedback System CLI (397 tests total)*
