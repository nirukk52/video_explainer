# CLI Reference

Complete reference for all CLI commands.

## Overview

```bash
python -m src.cli <command> [options]
```

## Project Management

### list

List all available projects.

```bash
python -m src.cli list
```

### info

Show detailed project information.

```bash
python -m src.cli info <project>
```

### create

Create a new project.

```bash
python -m src.cli create <project_id>
python -m src.cli create <project_id> --title "My Video"
```

---

## Content Generation Pipeline

### generate

Run the entire pipeline end-to-end.

```bash
python -m src.cli generate <project>
python -m src.cli generate <project> --force           # Regenerate everything
python -m src.cli generate <project> --from scenes     # Start from step
python -m src.cli generate <project> --to voiceover    # Stop at step
python -m src.cli generate <project> --interactive     # Pause for plan review
python -m src.cli generate <project> --mock            # Use mock LLM/TTS
```

**Pipeline steps:** plan → script → narration → scenes → voiceover → storyboard → render

| Option | Description |
|--------|-------------|
| `--force` | Regenerate all steps, even if outputs exist |
| `--interactive` | Pause for interactive plan review before continuing |
| `--from STEP` | Start from: plan, script, narration, scenes, voiceover, storyboard, render |
| `--to STEP` | Stop after this step |
| `--resolution` | Output: 4k, 1440p, 1080p (default), 720p, 480p |
| `--voice-provider` | TTS: elevenlabs, edge, mock |
| `--mock` | Use mock LLM and TTS |
| `--timeout` | Timeout per scene in seconds (default: 300) |

---

### plan

Create and manage video plans before script generation. Plans provide a structured outline with scene breakdowns, visual approaches, and ASCII art previews for user review and approval.

```bash
python -m src.cli plan create <project>                # Interactive plan creation
python -m src.cli plan create <project> --no-interactive  # Auto-generate without review
python -m src.cli plan create <project> --force        # Overwrite existing plan
python -m src.cli plan review <project>                # Review and refine existing plan
python -m src.cli plan show <project>                  # Display current plan
python -m src.cli plan approve <project>               # Approve without interactive session
```

**Subcommands:**

| Command | Description |
|---------|-------------|
| `create` | Generate a new video plan |
| `review` | Review and refine existing plan interactively |
| `show` | Display the current plan |
| `approve` | Approve plan without interactive session |

**Options for `create`:**

| Option | Description |
|--------|-------------|
| `--no-interactive` | Generate plan without interactive review |
| `--duration` | Target video duration in seconds |
| `--force` | Overwrite existing plan |
| `--mock` | Use mock LLM |

**Interactive Commands:**

When in interactive mode, use these commands:

| Command | Description |
|---------|-------------|
| `a`, `approve` | Approve the plan and proceed |
| `r <feedback>`, `refine <feedback>` | Refine with natural language feedback |
| `s`, `save` | Save current draft |
| `q`, `quit` | Exit (saves draft automatically) |
| `h`, `help` | Show help |

**Refinement examples:**
```
> r Add arrows showing data flow in scene 2
> r Make the ASCII visual for scene 3 show a side-by-side comparison
> r Scene 4 should have the formula more prominent
> r Reduce the duration of the hook scene
```

**Output:** `projects/<project>/plan/plan.json`, `plan.md`

---

### script

Generate a video script from input documents. If an approved plan exists, the script will follow the plan's structure.

```bash
python -m src.cli script <project>                    # From input/ directory (uses plan if approved)
python -m src.cli script <project> --input file.pdf  # From specific file
python -m src.cli script <project> --url https://... # From URL
python -m src.cli script <project> --skip-plan       # Generate without using plan
python -m src.cli script <project> --mock            # Mock for testing
```

**Supported formats:** Markdown (`.md`), PDF (`.pdf`), URLs

| Option | Description |
|--------|-------------|
| `--input, -i` | Input file path |
| `--url` | Web URL to fetch |
| `--duration` | Target video duration in seconds |
| `--skip-plan` | Generate script without using approved plan (backward compatible) |
| `--continue-on-error` | Skip failed files |
| `--mock` | Use mock LLM |
| `-v, --verbose` | Verbose output |

**Output:** `projects/<project>/script/script.json`

---

### narration

Generate scene narrations from the script.

```bash
python -m src.cli narration <project>
python -m src.cli narration <project> --force        # Overwrite existing
python -m src.cli narration <project> --topic "AI"   # Custom topic
python -m src.cli narration <project> --mock         # Mock for testing
```

| Option | Description |
|--------|-------------|
| `--force` | Overwrite existing narrations |
| `--topic` | Custom topic for narration context |
| `--mock` | Use mock LLM |
| `-v, --verbose` | Verbose output |

**Output:** `projects/<project>/narration/narrations.json`

---

### scenes

Generate Remotion scene components (React/TypeScript).

```bash
python -m src.cli scenes <project>
python -m src.cli scenes <project> --force           # Regenerate all
python -m src.cli scenes <project> --scene 3         # Single scene by index
python -m src.cli scenes <project> --scene Hook.tsx  # Single scene by name
python -m src.cli scenes <project> --sync            # Sync timing only
python -m src.cli scenes <project> --timeout 600     # 10 min per scene
```

| Option | Description |
|--------|-------------|
| `--force` | Overwrite existing scenes |
| `--scene` | Generate specific scene (index or filename) |
| `--sync` | Update timing without regenerating visuals |
| `--timeout` | Timeout per scene in seconds |
| `-v, --verbose` | Verbose output |

**Output:** `projects/<project>/scenes/*.tsx`, `styles.ts`, `index.ts`

---

### voiceover

Generate audio files from narrations.

```bash
python -m src.cli voiceover <project>
python -m src.cli voiceover <project> --provider edge
python -m src.cli voiceover <project> --force
python -m src.cli voiceover <project> --scene scene1_hook
python -m src.cli voiceover <project> --mock
```

| Option | Description |
|--------|-------------|
| `--provider` | TTS: elevenlabs, edge, mock, manual |
| `--force` | Regenerate all voiceovers |
| `--scene` | Generate specific scene only |
| `--mock` | Use mock audio |
| `--audio-dir` | Directory for manual recordings |
| `--whisper-model` | Whisper model for manual provider |
| `--export-script` | Export recording script |

**Output:** `projects/<project>/voiceover/*.mp3`, `manifest.json`

---

### storyboard

Generate or view the storyboard linking scenes with audio.

```bash
python -m src.cli storyboard <project>
python -m src.cli storyboard <project> --view       # View existing
python -m src.cli storyboard <project> --force      # Regenerate
```

| Option | Description |
|--------|-------------|
| `--view` | View existing storyboard |
| `--force` | Regenerate storyboard |
| `-v, --verbose` | Verbose output |

**Output:** `projects/<project>/storyboard/storyboard.json`

---

### render

Render the final video.

```bash
python -m src.cli render <project>
python -m src.cli render <project> -r 4k            # 4K resolution
python -m src.cli render <project> --preview        # Fast preview
python -m src.cli render <project> --fast           # Faster encoding
python -m src.cli render <project> --concurrency 8  # Thread count
python -m src.cli render <project> --gl angle       # Use ANGLE for WebGL
python -m src.cli render <project> --short          # Render short
```

| Option | Description |
|--------|-------------|
| `-r, --resolution` | 4k, 1440p, 1080p (default), 720p, 480p |
| `--preview` | Fast preview render |
| `--fast` | Faster encoding (lower quality) |
| `--concurrency N` | Override thread count |
| `--gl` | OpenGL renderer: angle, egl, swiftshader, swangle, vulkan |
| `--short` | Render short instead of full video |
| `--variant` | Short variant name |

**Output:** `projects/<project>/output/video.mp4`

### Resolution Presets

| Preset | Full Video | Shorts |
|--------|------------|--------|
| 4k | 3840x2160 | 2160x3840 |
| 1440p | 2560x1440 | 1440x2560 |
| 1080p | 1920x1080 | 1080x1920 |
| 720p | 1280x720 | 720x1280 |
| 480p | 854x480 | 480x854 |

---

## Sound Design

See [SOUND.md](SOUND.md) for detailed documentation.

### sound

```bash
python -m src.cli sound <project> library --list     # List sounds
python -m src.cli sound <project> library --generate # Generate SFX files
python -m src.cli sound <project> analyze            # Preview detection
python -m src.cli sound <project> generate           # Write SFX cues
python -m src.cli sound <project> clear              # Remove SFX cues
```

### music

```bash
python -m src.cli music <project> generate           # Background music
python -m src.cli music <project> short              # Shorts music
python -m src.cli music <project> info               # Device info
```

---

## Refinement

See [REFINEMENT.md](REFINEMENT.md) for detailed documentation.

### refine

```bash
python -m src.cli refine <project>                    # Visual refinement
python -m src.cli refine <project> --phase analyze    # Gap analysis
python -m src.cli refine <project> --phase script     # Script refinement
python -m src.cli refine <project> --phase visual-cue # Visual cue refinement
python -m src.cli refine <project> --phase visual     # Visual refinement
```

| Option | Description |
|--------|-------------|
| `--phase` | analyze, script, visual-cue, visual (default) |
| `--scene N` | Refine specific scene |
| `--apply` | Apply patches (visual-cue phase) |
| `--batch-approve` | Auto-approve (script phase) |
| `--live` | Stream output |

---

## Shorts

See [SHORTS.md](SHORTS.md) for detailed documentation.

### short

```bash
python -m src.cli short generate <project>           # Full pipeline
python -m src.cli short script <project>             # Generate script
python -m src.cli short scenes <project>             # Generate scenes
python -m src.cli short voiceover <project>          # Generate voiceover
python -m src.cli short storyboard <project>         # Generate storyboard
python -m src.cli short timing <project>             # Generate timing
```

---

## Quality Assurance

### factcheck

Verify script accuracy against source material.

```bash
python -m src.cli factcheck <project>
python -m src.cli factcheck <project> --mock         # Mock for testing
python -m src.cli factcheck <project> --no-save      # Don't save report
```

| Option | Description |
|--------|-------------|
| `--mock` | Use mock for testing |
| `--no-save` | Don't save report file |
| `-v, --verbose` | Verbose output |
| `--timeout` | Timeout in seconds |

**Output:** `projects/<project>/factcheck/report.json`

---

### feedback

Process natural language feedback to update project files.

```bash
python -m src.cli feedback <project> add "Make text larger"
python -m src.cli feedback <project> add "Fix scene 3" --dry-run
python -m src.cli feedback <project> list
python -m src.cli feedback <project> show <id>
python -m src.cli feedback <project> retry <id>
```

| Command | Description |
|---------|-------------|
| `add` | Add and process new feedback |
| `list` | List all feedback for project |
| `show <id>` | Show feedback details |
| `retry <id>` | Retry failed feedback |

| Option | Description |
|--------|-------------|
| `--dry-run` | Analyze without applying changes |
| `--live` | Stream Claude Code output |

**Supported intents:**
- `script_content` - Narration/voiceover changes
- `visual_cue` - Visual specification changes
- `visual_impl` - Scene component code changes
- `script_structure` - Add/remove/reorder scenes
- `timing` - Duration changes
- `style` - Visual styling changes

**Output:** `projects/<project>/refinement/feedback.json`
