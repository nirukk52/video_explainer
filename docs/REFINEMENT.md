# Refinement System

The refinement system helps elevate video quality to professional standards through a 5-phase process.

## Overview

| Phase | Name | Purpose |
|-------|------|---------|
| 1 | Analyze | Gap analysis - identifies missing concepts and generates patches |
| 2 | Script | Applies patches + storytelling refinements to script |
| 3 | Visual-Cue | Improves visual specifications in script.json |
| 4 | Visual | AI-powered visual inspection and code fixes |
| 5 | Sync | Synchronize visual animations with voiceover timing |

**Key Design:** Phases 1 and 2 are connected. Phase 1 outputs patches that Phase 2 consumes and applies.

## Quick Start

```bash
# Run all phases in sequence
python -m src.cli refine <project> --phase analyze
python -m src.cli refine <project> --phase script --batch-approve
python -m src.cli refine <project> --phase visual-cue --apply
python -m src.cli refine <project> --phase visual
python -m src.cli refine <project> --phase sync --full

# Or just run visual refinement (default)
python -m src.cli refine <project>

# Or just run sync to align animations with voiceover
python -m src.cli refine <project> --phase sync --full
```

## Phase 1: Gap Analysis

Compares source material against the generated script to identify gaps and generate patches.

**Prerequisites:** Input source material (`input/*.md` or `input/*.txt`) and narrations

```bash
python -m src.cli refine <project> --phase analyze
```

**What it detects:**
- **Missing concepts** - Important topics from source not covered in script
- **Shallow coverage** - Concepts mentioned but not explained deeply enough
- **Narrative gaps** - Logical jumps between scenes that confuse viewers

**How it works:**
1. Loads source material from `input/*.md` or `input/*.txt`
2. Extracts key concepts with importance ratings (critical, high, medium, low)
3. Analyzes script coverage depth (not_covered, mentioned, explained, deep_dive)
4. Identifies narrative gaps between scenes
5. Generates patches to fix identified gaps

**Patch Types:**

| Type | Description |
|------|-------------|
| `add_scene` | Insert a new scene to cover missing concepts |
| `modify_scene` | Update existing scene content |
| `expand_scene` | Add more detail to shallow coverage |
| `add_bridge` | Add transitional content between scenes |

**Output:** `projects/<project>/refine/gap_analysis.json`

Returns exit code 1 if critical gaps are found.

---

## Phase 2: Script Refinement

Loads patches from Phase 1, generates additional storytelling refinements, and applies approved changes.

**Prerequisites:** Run Phase 1 first to generate patches

```bash
python -m src.cli refine <project> --phase script              # Interactive
python -m src.cli refine <project> --phase script --batch-approve  # Auto-approve
```

**How it works:**
1. Loads patches from Phase 1 (`gap_analysis.json`)
2. Analyzes each scene against 10 narration principles
3. Generates additional storytelling patches for quality issues
4. Combines Phase 1 patches + storytelling patches
5. Interactive mode: Presents each patch for approval (y/n/e to edit)
6. Applies approved patches to update `script.json` and `narrations.json`

### 10 Narration Principles

| # | Principle | Description |
|---|-----------|-------------|
| 1 | Hook in the first sentence | Grab attention with surprising facts, questions, or stakes |
| 2 | Build tension before release | Create anticipation before revealing solutions |
| 3 | Seamless transitions | Connect scenes with callback phrases |
| 4 | One insight per scene | Focus each scene on a single memorable takeaway |
| 5 | Concrete analogies | Use familiar comparisons for abstract concepts |
| 6 | Emotional beats | Include moments of wonder, surprise, or satisfaction |
| 7 | Match length to complexity | Simple ideas = short scenes, complex = more time |
| 8 | Rhetorical questions | Plant questions before answering |
| 9 | Clear stakes | Explain why the audience should care |
| 10 | Strong scene endings | End with memorable phrases or setup for next scene |

**Scoring weights:**
- Hook strength: 15%
- Flow quality: 15%
- Tension/buildup: 15%
- Insight clarity: 20%
- Emotional engagement: 15%
- Factual accuracy: 10%
- Length appropriateness: 10%

**Output:** Updates `script/script.json` and `narration/narrations.json`

---

## Phase 3: Visual-Cue Refinement

Analyzes and improves the `visual_cue` specifications in `script.json`.

**Prerequisites:** Script with visual_cue fields in `script/script.json`

```bash
python -m src.cli refine <project> --phase visual-cue           # Analyze
python -m src.cli refine <project> --phase visual-cue --scene 0 # Specific scene
python -m src.cli refine <project> --phase visual-cue --apply   # Apply patches
```

**How it works:**
1. Reads `script/script.json` and extracts visual_cue for each scene
2. Evaluates each visual_cue against established patterns
3. Creates `UpdateVisualCuePatch` for scenes needing improvement
4. With `--apply`, updates `script.json` with improved visual_cues

### Visual Pattern Guidelines

The refiner ensures visual_cues specify:
- **Material style** - Dark glass panels vs light panels
- **Shadow layers** - Multi-layer shadows with specific opacities
- **3D depth** - Layered compositions with clear z-ordering
- **Color values** - Specific rgba ranges for backgrounds

**Output:**
- Analysis: `projects/<project>/refine/visual_cue_analysis.json`
- With `--apply`: Updates `script/script.json`

---

## Phase 4: Visual Refinement

AI-powered visual inspection using Claude Code with browser access.

**Prerequisites:** Scene components generated and storyboard created

```bash
python -m src.cli refine <project> --phase visual
python -m src.cli refine <project> --phase visual --scene 3 --live
```

**How it works:**
1. **Beat Parsing** - Narration analyzed to identify key visual moments
2. **Visual Inspection** - Claude Code opens scene in Remotion Studio
3. **Quality Assessment** - Screenshots analyzed against 13 guiding principles
4. **Fix Application** - Claude Code edits scene components to fix issues
5. **Verification** - New screenshots verify improvements

### 13 Guiding Principles

| Principle | Description |
|-----------|-------------|
| Show Don't Tell | Use visuals, not just text |
| Animation Reveals | Animate elements in sync with narration |
| Progressive Disclosure | Show info as it's mentioned |
| Text Complements | Text supports visuals, doesn't replace |
| Visual Hierarchy | Guide viewer's eye |
| Breathing Room | Don't clutter |
| Purposeful Motion | Every animation has meaning |
| Emotional Resonance | Connect with viewer |
| Professional Polish | Clean, consistent |
| Sync with Narration | Timing matches speech |
| Screen Space Utilization | Use full canvas effectively |
| Material Depth | Multi-layer shadows and 3D depth |
| Visual Spec Match | Match visual_cue from script.json |

**Technical Details:**

Uses `SingleScenePlayer` Remotion composition that loads individual scenes starting at frame 0, eliminating navigation through the entire video.

**Output:** Scene files modified in place (`projects/<project>/scenes/*.tsx`)

---

## Phase 5: Visual-Voiceover Sync

Automatically synchronizes visual animations with voiceover timing by generating frame-accurate timing constants.

**Prerequisites:**
- Voiceover manifest with word timestamps (`voiceover/manifest.json`)
- Scene components with timing variables (`scenes/*.tsx`)

```bash
# Full sync workflow (recommended)
python -m src.cli refine <project> --phase sync --full

# Individual steps
python -m src.cli refine <project> --phase sync --generate-map
python -m src.cli refine <project> --phase sync --generate-timing
python -m src.cli refine <project> --phase sync --migrate-scenes

# Preview without changes
python -m src.cli refine <project> --phase sync --full --dry-run

# Process specific scene
python -m src.cli refine <project> --phase sync --full --scene 1
```

### How it works

The sync phase runs in three steps:

#### Step 1: Generate Sync Map (`--generate-map`)

Uses LLM to analyze each scene's code and identify sync points - moments where visual animations should align with specific words in the narration.

**Input:** Scene code + word timestamps from manifest

**Output:** `sync/sync_map.json` containing:
```json
{
  "scenes": [{
    "scene_id": "the_impossible_leap",
    "sync_points": [{
      "id": "numbersAppear",
      "sync_type": "element_appear",
      "trigger_phrase": "Eighty-three point three percent",
      "trigger_word": "Eighty-three",
      "offset_frames": -3,
      "visual_element": "BigNumber component"
    }]
  }]
}
```

#### Step 2: Generate Timing File (`--generate-timing`)

Converts sync points to frame numbers using word timestamps from the voiceover manifest.

**Output:** `scenes/timing.ts`
```typescript
export const TIMING = {
  the_impossible_leap: {
    duration: 1112,
    numbersAppear: 129,
    vsAppear: 176,
    windowsEntrance: 356,
  },
  // ... more scenes
} as const;
```

#### Step 3: Migrate Scenes (`--migrate-scenes`)

Uses LLM to transform scene code to import and use the centralized timing constants.

**Before:**
```typescript
const entrance = spring({
  frame: Math.max(0, f - 220),
  fps,
});
```

**After:**
```typescript
import { TIMING } from './timing';

const entrance = spring({
  frame: Math.max(0, f - TIMING.the_impossible_leap.windowsEntrance),
  fps,
});
```

### Sync Point Types

| Type | Description |
|------|-------------|
| `element_appear` | Visual element enters the scene |
| `element_exit` | Visual element leaves the scene |
| `phase_transition` | Major visual phase change |
| `text_reveal` | Text or label appears |
| `animation_start` | Animation sequence begins |
| `data_update` | Data visualization updates |
| `highlight` | Element gets highlighted |
| `camera_move` | Camera/viewport changes |

### Timing Calculation

Frame numbers are calculated from word timestamps:

```
frame = (word_start_seconds × fps) + offset_frames
```

- **offset_frames**: Default -3 frames (anticipate by ~100ms at 30fps)
- **use_word_start**: Use word start (default) or end time
- Frames are clamped to valid range (0 to scene duration)

### Backup & Recovery

Scene migrations create automatic backups:
- Backups stored in `scenes/.backups/`
- Named: `SceneName.YYYYMMDD_HHMMSS.bak`
- Restored automatically if validation fails

### Validation

After migration, scenes are validated for:
- Balanced braces, parentheses, and brackets
- Required import and export statements
- TIMING import present when TIMING is used

For full TypeScript validation, run:
```bash
cd remotion && npx tsc --noEmit
```

**Output:**
- `sync/sync_map.json` - Sync point definitions
- `sync/sync_result.json` - Execution summary
- `scenes/timing.ts` - Centralized timing constants
- `scenes/*.tsx` - Migrated scene components

---

## CLI Options

| Option | Description |
|--------|-------------|
| `--phase` | Phase to run: `analyze`, `script`, `visual-cue`, `visual`, or `sync` (default: visual) |
| `--scene N` | Refine only scene N (1-indexed) |
| `--force` | Continue even if project files are out of sync |
| `--skip-validation` | Skip project sync validation |
| `-q, --quiet` | Suppress progress messages |

### Phase-specific options

**Script phase:**
| Option | Description |
|--------|-------------|
| `--batch-approve` | Auto-approve all suggested changes |

**Visual-cue phase:**
| Option | Description |
|--------|-------------|
| `--apply` | Apply generated patches to script.json |

**Visual phase:**
| Option | Description |
|--------|-------------|
| `--legacy` | Use Playwright-based screenshot capture instead of Claude Code |
| `--live` | Stream Claude Code output in real-time |

**Sync phase:**
| Option | Description |
|--------|-------------|
| `--full` | Run complete sync workflow (default if no step specified) |
| `--generate-map` | Generate sync map only |
| `--generate-timing` | Generate timing.ts only |
| `--migrate-scenes` | Migrate scenes to use timing imports |
| `--dry-run` | Preview changes without modifying files |
