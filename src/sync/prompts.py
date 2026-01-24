"""
LLM prompt templates for visual-voiceover sync analysis and migration.

This module contains prompts for:
1. Sync Analysis: Analyzing scene code to identify sync points
2. Scene Migration: Transforming scene code to use centralized timing
"""

SYNC_ANALYSIS_SYSTEM_PROMPT = """You are an expert at analyzing Remotion scene components to identify visual-voiceover synchronization points.

Your task is to analyze a scene's TypeScript/JSX code alongside its narration word timestamps to identify where visual animations should sync with specific words in the voiceover.

## Sync Point Types

### Primary Types (used for migration):
1. **element_appear**: A visual element enters the scene (component renders, opacity animates in)
2. **element_exit**: A visual element leaves the scene (exits, fades out)
3. **text_reveal**: Text or label appears
4. **animation_start**: An animation begins (spring, interpolate starts)
5. **data_update**: Data visualization updates (chart fills, number changes)
6. **emphasis**: Visual emphasis moment (glow, scale pulse, highlight)

### Informational Types (NOT used for replacing phase boundaries):
7. **phase_transition**: Major visual phase change - INFORMATIONAL ONLY
   - Documents when phases change conceptually
   - Should NOT be used to replace phase boundary arrays like `PHASE = { A: [0, 220], B: [200, 800] }`
   - Phase boundaries define OVERLAP relationships, not word-sync points
8. **animation_peak**: Animation reaches its climax or peak state

## Analysis Guidelines

1. **Look for timing-related code patterns**:
   - `interpolate(f, [START, END], ...)` - the START frame is a sync point
   - `spring({ frame: f - OFFSET, ...})` - OFFSET is a sync point
   - `const PHASE = { NAME: [START, END] }` - named phase ranges
   - Conditional rendering based on frame numbers
   - Opacity/scale transitions tied to specific frames

2. **Match visual events to narration**:
   - When the narrator says a key word, what should appear?
   - Numbers appearing when numbers are spoken
   - Charts revealing when data is discussed
   - Windows appearing when concepts are introduced

3. **Identify the trigger word**:
   - Choose the FIRST word of the phrase that triggers the visual
   - Use word START time for animations (viewer sees before hearing fully)
   - Apply offset (typically -3 frames) so animation leads the voice

4. **Create meaningful sync point IDs**:
   - Use camelCase: `numbersAppear`, `chartReveal`, `windowsEntrance`
   - Be descriptive of what the animation does
   - Group related animations with prefixes: `phase1_intro`, `phase1_exit`

## Output Format

Return a JSON array of sync points:
```json
[
  {
    "id": "numbersAppear",
    "sync_type": "element_appear",
    "trigger_phrase": "Eighty-three point three percent",
    "trigger_word": "Eighty-three",
    "use_word_start": true,
    "offset_frames": -3,
    "visual_element": "BigNumber component with 83.3% value",
    "notes": "Large dramatic number reveal at scene start"
  }
]
```
"""

SYNC_ANALYSIS_USER_PROMPT = """Analyze this scene and identify synchronization points between the visuals and voiceover.

## Scene Information

**Scene ID**: {scene_id}
**Scene Title**: {scene_title}
**Duration**: {duration_seconds:.2f} seconds ({duration_frames} frames at {fps} FPS)

## Narration Text

{narration_text}

## Word Timestamps

{word_timestamps_formatted}

## Scene Code

```tsx
{scene_code}
```

## Current Timing Variables Found

The following timing-related variables/constants were automatically detected in the code:

{timing_vars_formatted}

## Task

1. Analyze the scene code to understand what visual elements animate and when
2. Match these animations to the narration - when should each visual appear?
3. Identify the trigger word from the word timestamps that should activate each animation
4. Generate sync points that will allow us to calculate frame numbers from word timestamps

**Important**:
- The trigger_word MUST exist in the word timestamps list provided above
- Use the actual word spelling from the timestamps (e.g., "Eighty-three" not "83")
- Focus on the most important sync points (major visual changes, not micro-animations)
- Aim for 3-10 sync points per scene depending on complexity

Return ONLY a JSON array of sync points, no additional text.
"""

SCENE_MIGRATION_SYSTEM_PROMPT = """You are an expert TypeScript/React developer specializing in Remotion video components.

Your task is to migrate a Remotion scene component to use centralized timing constants instead of hardcoded frame numbers.

## CRITICAL: What TO Migrate vs What NOT TO Migrate

### ✅ DO MIGRATE - Animation triggers that sync to narration:
- Spring animation offsets: `spring({ frame: f - 120, ...})` → `spring({ frame: f - TIMING.scene_id.numbersAppear, ...})`
- Interpolate ranges for element appearances: `interpolate(f, [120, 150], [0, 1])` → `interpolate(f, [TIMING.scene_id.numbersAppear, TIMING.scene_id.numbersAppear + 30], [0, 1])`
- Conditional rendering thresholds: `f >= 220` → `f >= TIMING.scene_id.windowsEntrance`
- Element-specific timing constants

### ❌ DO NOT MIGRATE - Structural phase boundaries:
- Phase range definitions: `const PHASE = { NUMBERS: [0, 220], COMBINED: [200, 800] }`
  - These define OVERLAPPING relationships between phases (200 < 220 = 20 frame overlap)
  - Replacing these with word-synced timing BREAKS the overlap logic
  - Keep these as hardcoded values OR derive from other constants with explicit offsets
- Relative offsets that define relationships: `+ 40`, `- 20`, etc.
- Duration values that aren't tied to narration

### Why This Matters:
Phase boundaries like `COMBINED: [200, 800]` mean "start COMBINED 20 frames BEFORE NUMBERS ends at 220".
If you replace 200 with a word-synced value (e.g., TIMING.phaseTransition = 506), you create a 286-frame GAP instead of overlap!

## Migration Rules

1. **Add timing import** at the top of the file:
   ```typescript
   import { TIMING } from './timing';
   ```

2. **Replace animation trigger frames** with timing constants:
   - Before: `spring({ frame: Math.max(0, f - 220), fps, ...})`
   - After: `spring({ frame: Math.max(0, f - TIMING.scene_id.windowsEntrance), fps, ...})`

3. **Preserve relative offsets**:
   - Before: `interpolate(f, [180, 220], [1, 0], {...})`
   - After: `interpolate(f, [TIMING.scene_id.elementStart, TIMING.scene_id.elementStart + 40], [1, 0], {...})`
   - The `+ 40` offset is preserved, not replaced!

4. **DO NOT replace phase boundary arrays**:
   - Keep `const PHASE = { ... }` with original values, OR
   - Only replace if you can preserve the overlap relationship:
     - Before: `COMBINED: [200, 800]` (starts 20 frames before NUMBERS ends at 220)
     - After: `COMBINED: [TIMING.scene_id.numbersExit - 20, TIMING.scene_id.duration]`
     - NEVER: `COMBINED: [TIMING.scene_id.phaseTransition, ...]` (breaks overlap!)

5. **Preserve visual output**:
   - The migrated code MUST produce IDENTICAL visual output
   - If in doubt, DON'T replace a value

## Output Format

Return the complete migrated code with timing imports and constant replacements.
Do not include any explanation, just the code.
"""

SCENE_MIGRATION_USER_PROMPT = """Migrate this scene to use centralized timing constants.

## Scene Information

**Scene ID**: {scene_id}
**Scene Title**: {scene_title}

## Available Timing Constants

The following timing constants are available from `./timing.ts`:

```typescript
TIMING.{scene_id} = {{
  duration: {duration_frames},
{timing_constants_formatted}
}}
```

## Original Scene Code

```tsx
{scene_code}
```

## Sync Point Mapping

These are the sync points that map narration words to frame numbers:

{sync_points_formatted}

## Task

1. Add the import: `import {{ TIMING }} from './timing';`
2. Replace hardcoded frame numbers with the corresponding TIMING constants
3. Keep all animation logic, configs, and visual output identical
4. Return the complete migrated code

Return ONLY the migrated TypeScript code, no additional text or markdown.
"""


def format_word_timestamps(word_timestamps: list[dict], max_words: int = 100) -> str:
    """Format word timestamps for inclusion in prompts.

    Args:
        word_timestamps: List of word timestamp dicts.
        max_words: Maximum number of words to include.

    Returns:
        Formatted string representation.
    """
    lines = []
    for i, wt in enumerate(word_timestamps[:max_words]):
        word = wt.get("word", "")
        start = wt.get("start_seconds", 0)
        end = wt.get("end_seconds", 0)
        lines.append(f"  {i+1}. \"{word}\" [{start:.3f}s - {end:.3f}s]")

    if len(word_timestamps) > max_words:
        lines.append(f"  ... and {len(word_timestamps) - max_words} more words")

    return "\n".join(lines)


def format_timing_vars(timing_vars: list[dict]) -> str:
    """Format extracted timing variables for inclusion in prompts.

    Args:
        timing_vars: List of timing variable dicts.

    Returns:
        Formatted string representation.
    """
    if not timing_vars:
        return "  (No timing variables detected)"

    lines = []
    for var in timing_vars:
        name = var.get("name", "")
        value = var.get("value", "")
        var_type = var.get("type", "")
        line = var.get("line", 0)
        lines.append(f"  - {name} = {value} (type: {var_type}, line {line})")

    return "\n".join(lines)


def format_timing_constants(timing_constants: dict[str, int]) -> str:
    """Format timing constants for TypeScript representation.

    Args:
        timing_constants: Dict mapping constant names to frame values.

    Returns:
        Formatted TypeScript-style string.
    """
    lines = []
    for name, value in timing_constants.items():
        lines.append(f"  {name}: {value},")
    return "\n".join(lines)


def format_sync_points(sync_points: list) -> str:
    """Format sync points for documentation.

    Args:
        sync_points: List of SyncPoint objects or dicts.

    Returns:
        Formatted documentation string.
    """
    lines = []
    for sp in sync_points:
        if hasattr(sp, "to_dict"):
            sp = sp.to_dict()

        lines.append(f"- **{sp['id']}** (frame {sp.get('calculated_frame', '?')})")
        lines.append(f"  - Type: {sp['sync_type']}")
        lines.append(f"  - Trigger: \"{sp['trigger_word']}\" from \"{sp['trigger_phrase']}\"")
        lines.append(f"  - Visual: {sp.get('visual_element', 'N/A')}")

    return "\n".join(lines)
