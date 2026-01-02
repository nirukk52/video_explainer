"""Scene generator - creates Remotion scene components from scripts."""

import json
import re
from pathlib import Path
from typing import Any

from ..config import Config, LLMConfig, load_config
from ..understanding.llm_provider import ClaudeCodeLLMProvider


# System prompt for scene generation
SCENE_SYSTEM_PROMPT = """You are an expert React/Remotion developer creating animated scene components for technical explainer videos.

## Your Expertise

You create visually stunning, educational animations using:
- **Remotion**: useCurrentFrame, useVideoConfig, interpolate, spring, Sequence, AbsoluteFill
- **React**: Functional components with TypeScript
- **CSS-in-JS**: Inline styles for all styling

## CRITICAL REQUIREMENTS

### 1. Citation Requirements (MANDATORY)

Every technical concept MUST include a citation that:
- Appears as a visual overlay in the bottom-right corner
- Fades in when the concept is introduced
- Uses format: "Paper Title — Authors et al., Venue Year"

Example citation element:
```typescript
<div style={{
  position: "absolute",
  bottom: 20 * scale,
  right: 30 * scale,
  fontSize: 14 * scale,
  color: COLORS.textMuted,
  opacity: citationOpacity,
  fontStyle: "italic",
  fontFamily: FONTS.handwritten,
}}>
  "An Image is Worth 16x16 Words" — Dosovitskiy et al., ICLR 2021
</div>
```

### 2. Layout Requirements (MANDATORY)

- **No overflow**: ALL elements must stay within 1920x1080 bounds at ALL frames
- **No overlapping**: Elements must NEVER overlap unless intentionally layered
  - Calculate exact positions for all elements before placing them
  - When showing new content, either: (a) position it in empty space, or (b) fade out/remove previous elements first
  - Stack elements vertically or horizontally with proper gaps (20-40px scaled)
- **Fill the space**: Main content should use at least 60-70% of canvas - AVOID empty/wasted space
- **Consistent margins**: Use 60-80px scaled margins from edges
- **Component sizing**: Make elements LARGE and readable
  - Boxes, diagrams, images should be substantial (at least 200-400px scaled)
  - Don't make elements tiny with lots of whitespace around them
- **Container overflow prevention**: Content inside boxes must fit within the box bounds
  - Calculate content size before setting container size
  - Add padding inside containers (15-20px scaled)
  - Use overflow: "hidden" if needed, but prefer proper sizing

Layout zones:
- Top-left: Scene indicator (required)
- Top area: Title
- Center: Main content (largest area, USE THIS SPACE FULLY)
- Bottom-right: Citations

### 3. Animation Requirements (MANDATORY)

- **No chaotic motion**: No shaking, trembling, or erratic movements
- **Smooth springs**: Use damping: 12, stiffness: 100 for natural movement
- **Proportional timing**: Phase durations scale with durationInFrames
- **Stagger delays**: 10-20 frames between sequential elements
- **Bounded motion**: Ensure animated elements stay within canvas
- **Complete animations**: If animating a sequence (e.g., flattening pixels), ensure it completes for ALL items
- **Narration sync**: Visual phases MUST align with voiceover timing
  - When narration mentions something, it should be visible on screen at that moment
  - Don't show visuals too early or too late relative to narration
  - Calculate phase timings based on when concepts are mentioned in the voiceover

### 3.1 Arrows and Connections (MANDATORY)

- **Complete paths**: Arrows must connect from source to destination without breaks
- **Proper endpoints**: Arrow heads should touch their target elements
- **Visibility**: Arrows should be visible (2-3px stroke, contrasting color)
- **Animation**: Animate arrows drawing from source to destination using strokeDasharray/strokeDashoffset

### 4. Typography Requirements (MANDATORY)

- **Font weight**: Always use fontWeight: 400 for handwritten fonts (FONTS.handwritten)
- **Line height**: Use 1.5 for body text
- **Font sizes**:
  - Titles: 42-48px scaled
  - Subtitles: 20-26px scaled
  - Body: 18-22px scaled
  - Labels: 14-18px scaled
  - Citations: 14-16px scaled

### 5. Visual Content Requirements (MANDATORY)

- **Use real visuals, not placeholders**:
  - Instead of "[CAT]" or "cat picture" text, use actual image elements or colored rectangles representing images
  - Use emoji or unicode symbols where appropriate (🐱, 🚗, 🏥) instead of text labels
  - Create visual representations (colored boxes, icons, shapes) rather than text descriptions
- **No brand names**: Don't use specific company names (Tesla, Google, etc.) - use generic descriptions
- **Representational images**: When showing "an image of X", render a stylized visual representation, not just text

## Animation Principles

1. **Frame-based timing**: Everything is based on `useCurrentFrame()`. Calculate local frames relative to scene start.
2. **Smooth interpolation**: Use `interpolate()` for all transitions with proper extrapolation clamping.
3. **Spring animations**: Use `spring()` for natural movements (NOT bouncy or chaotic).
4. **Staggered reveals**: Animate elements sequentially with calculated delays.
5. **Scale-responsive**: Always use a scale factor based on `width/1920` for responsive sizing.

## Code Patterns

```typescript
// Standard scene structure
import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig, spring } from "remotion";
import { COLORS, FONTS, getSceneIndicatorStyle, getSceneIndicatorTextStyle } from "./styles";

interface SceneNameProps {
  startFrame?: number;
}

export const SceneName: React.FC<SceneNameProps> = ({ startFrame = 0 }) => {
  const frame = useCurrentFrame();
  const { fps, width, height, durationInFrames } = useVideoConfig();
  const localFrame = frame - startFrame;
  const scale = Math.min(width / 1920, height / 1080);

  // Phase timings as percentages of total duration
  const phase1End = Math.round(durationInFrames * 0.25);
  const phase2End = Math.round(durationInFrames * 0.50);
  // ...

  // Animations using interpolate
  const titleOpacity = interpolate(localFrame, [0, 15], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Citation appears when concept is introduced
  const citationOpacity = interpolate(localFrame, [phase1End, phase1End + 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ backgroundColor: COLORS.background, fontFamily: FONTS.handwritten }}>
      {/* Scene indicator */}
      <div style={{ ...getSceneIndicatorStyle(scale), opacity: titleOpacity }}>
        <span style={getSceneIndicatorTextStyle(scale)}>1</span>
      </div>

      {/* Main content - use at least 60% of canvas */}

      {/* Citation - bottom right, fades in with concept */}
      <div style={{
        position: "absolute",
        bottom: 20 * scale,
        right: 30 * scale,
        fontSize: 14 * scale,
        color: COLORS.textMuted,
        opacity: citationOpacity,
        fontStyle: "italic",
      }}>
        "Paper Title" — Authors et al., Venue Year
      </div>
    </AbsoluteFill>
  );
};
```

## Visual Elements to Use

- **Text reveals**: Fade in with slight upward movement
- **Diagrams**: Build up progressively, highlighting active parts
- **Token grids**: Show data as colored blocks that animate
- **Progress bars**: Show comparisons and changes over time
- **Arrows/connections**: Animate to show data flow
- **Subtle highlights**: Use box-shadow sparingly for emphasis
- **Citations**: Always include paper references for technical concepts

## Color Scheme (import from ./styles)

- primary: "#00d9ff" (cyan - main headings, key elements, emphasis)
- secondary: "#ff6b35" (orange - supporting elements, contrasts)
- success: "#00ff88" (green - positive outcomes, solutions, checkmarks)
- error: "#ff4757" (red - problems, warnings, alerts)
- textDim: "#888888" (secondary text, less important info)
- textMuted: "#666666" (tertiary text, citations, captions)
"""


SCENE_GENERATION_PROMPT = """Generate a Remotion scene component for the following scene.

## Scene Information

**Scene Number**: {scene_number}
**Title**: {title}
**Type**: {scene_type}
**Duration**: {duration} seconds at 30fps = {total_frames} frames

**Voiceover/Narration**:
"{voiceover}"

**Visual Description**:
{visual_description}

**Key Elements to Animate**:
{elements}

## Reference: Example Scene Structure

Here's a well-structured example scene for reference:

```typescript
{example_scene}
```

## MANDATORY Requirements

1. Create a complete, working React/Remotion component
2. Name the component `{component_name}`
3. Export it as a named export
4. Include proper TypeScript interface for props
5. Use frame-based animations that match the narration timing
6. Include a scene indicator showing scene number {scene_number}
7. Make all sizes responsive using the scale factor
8. Import styles from "./styles" (COLORS, FONTS, getSceneIndicatorStyle, getSceneIndicatorTextStyle)
9. Phase timings should be proportional to durationInFrames
10. Add a detailed comment block at the top explaining the visual flow

## CRITICAL Layout & Style Requirements

11. **CITATIONS**: Include a citation element in bottom-right that fades in when the technical concept is introduced
12. **NO OVERFLOW**: All elements MUST stay within 1920x1080 bounds at ALL animation keyframes
13. **NO CHAOTIC MOTION**: No shaking, trembling, or erratic animations
14. **FILL THE SPACE**: Main content should use at least 60% of the canvas area
15. **TYPOGRAPHY**: Use fontWeight: 400 for FONTS.handwritten, lineHeight: 1.5 for body text
16. **SIZING**: Titles 42-48px, body 18-22px, labels 14-18px, citations 14-16px (all scaled)
17. **SPACING**: Use 60-80px scaled margins from canvas edges

## Output

Return ONLY the TypeScript/React code. No markdown code blocks, no explanation - just the code.
The component should be saved to: {output_path}
"""


STYLES_TEMPLATE = '''/**
 * Shared Style Constants for {project_title}
 *
 * Centralizes visual styling for consistency across all scenes.
 */

import React from "react";

// ===== COLOR PALETTE =====
export const COLORS = {{
  // Primary colors
  primary: "#00d9ff",      // Primary cyan - titles and highlights
  secondary: "#ff6b35",    // Orange - secondary elements
  success: "#00ff88",      // Green - positive indicators
  warning: "#f1c40f",      // Yellow - caution/warning
  error: "#ff4757",        // Red - errors/problems

  // Neutral colors
  background: "#0f0f1a",   // Dark background
  surface: "#1a1a2e",      // Surface/card background
  text: "#ffffff",         // Primary text
  textDim: "#888888",      // Secondary text
  textMuted: "#666666",    // Muted text
}};

// ===== TYPOGRAPHY =====
export const TYPOGRAPHY = {{
  title: {{
    fontSize: 56,
    fontWeight: 700 as const,
    color: COLORS.primary,
    margin: 0,
  }},
  subtitle: {{
    fontSize: 28,
    fontWeight: 400 as const,
    color: COLORS.textDim,
    marginTop: 8,
  }},
  body: {{
    fontSize: 22,
    fontWeight: 400 as const,
    color: COLORS.text,
    lineHeight: 1.6,
  }},
  mono: {{
    fontFamily: "JetBrains Mono, monospace",
  }},
}};

// ===== SCENE INDICATOR =====
export const SCENE_INDICATOR = {{
  container: {{
    top: 20,
    left: 20,
    width: 40,
    height: 40,
    borderRadius: 8,
  }},
  text: {{
    fontSize: 18,
    fontWeight: 700 as const,
    fontFamily: "JetBrains Mono, monospace",
  }},
}};

// ===== ANIMATION CONSTANTS =====
export const ANIMATION = {{
  fadeInDuration: 15,
  springConfig: {{
    damping: 12,
    stiffness: 100,
    mass: 1,
  }},
  quickSpring: {{
    damping: 15,
    stiffness: 200,
  }},
}};

// ===== HELPER FUNCTIONS =====

export const getScale = (width: number, height: number): number => {{
  return Math.min(width / 1920, height / 1080);
}};

export const getSceneIndicatorStyle = (scale: number): React.CSSProperties => ({{
  position: "absolute",
  top: SCENE_INDICATOR.container.top * scale,
  left: SCENE_INDICATOR.container.left * scale,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  width: SCENE_INDICATOR.container.width * scale,
  height: SCENE_INDICATOR.container.height * scale,
  borderRadius: SCENE_INDICATOR.container.borderRadius * scale,
  backgroundColor: COLORS.primary + "20",
  border: `${{2 * scale}}px solid ${{COLORS.primary}}`,
}});

export const getSceneIndicatorTextStyle = (scale: number): React.CSSProperties => ({{
  fontSize: SCENE_INDICATOR.text.fontSize * scale,
  fontWeight: SCENE_INDICATOR.text.fontWeight,
  color: COLORS.primary,
  fontFamily: SCENE_INDICATOR.text.fontFamily,
}});

export const getTitleStyle = (scale: number): React.CSSProperties => ({{
  fontSize: TYPOGRAPHY.title.fontSize * scale,
  fontWeight: TYPOGRAPHY.title.fontWeight,
  color: TYPOGRAPHY.title.color,
  margin: 0,
}});

export default {{ COLORS, TYPOGRAPHY, ANIMATION }};
'''


INDEX_TEMPLATE = '''/**
 * {project_title} Scene Registry
 *
 * Exports all scene components for the video.
 * Keys match scene_id suffixes in storyboard.json (e.g., "scene1_hook" -> "hook")
 */

import React from "react";

{imports}

export type SceneComponent = React.FC<{{ startFrame?: number }}>;

/**
 * Scene registry mapping storyboard scene types to components.
 * Keys must match the scene_id suffix in storyboard.json
 */
const SCENE_REGISTRY: Record<string, SceneComponent> = {{
{registry_entries}
}};

// Standard export name for the build system (required by remotion/src/scenes/index.ts)
export const PROJECT_SCENES = SCENE_REGISTRY;

{exports}

export function getScene(type: string): SceneComponent | undefined {{
  return SCENE_REGISTRY[type];
}}

export function getAvailableSceneTypes(): string[] {{
  return Object.keys(SCENE_REGISTRY);
}}
'''


class SceneGenerator:
    """Generates Remotion scene components from scripts using Claude Code."""

    def __init__(
        self,
        config: Config | None = None,
        working_dir: Path | None = None,
        timeout: int = 300,
    ):
        """Initialize the scene generator.

        Args:
            config: Configuration object
            working_dir: Working directory for Claude Code
            timeout: Timeout for LLM calls in seconds
        """
        self.config = config or load_config()
        self.working_dir = working_dir or Path.cwd()
        self.timeout = timeout

    def generate_all_scenes(
        self,
        project_dir: Path,
        script_path: Path | None = None,
        example_scenes_dir: Path | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        """Generate all scene components for a project.

        Args:
            project_dir: Path to the project directory
            script_path: Path to script.json (defaults to project_dir/script/script.json)
            example_scenes_dir: Directory with example scenes for reference
            force: Overwrite existing scenes

        Returns:
            Dict with generation results
        """
        # Resolve paths
        script_path = script_path or project_dir / "script" / "script.json"
        scenes_dir = project_dir / "scenes"

        if not script_path.exists():
            raise FileNotFoundError(f"Script not found: {script_path}")

        # Check if scenes already exist
        if scenes_dir.exists() and not force:
            existing = list(scenes_dir.glob("*.tsx"))
            if existing:
                raise FileExistsError(
                    f"Scenes already exist in {scenes_dir}. Use --force to overwrite."
                )

        # Load script
        with open(script_path) as f:
            script = json.load(f)

        # Create scenes directory
        scenes_dir.mkdir(parents=True, exist_ok=True)

        # Load example scene for reference
        example_scene = self._load_example_scene(example_scenes_dir)

        # Generate styles.ts first
        self._generate_styles(scenes_dir, script.get("title", "Untitled"))

        # Generate each scene
        results = {
            "scenes_dir": str(scenes_dir),
            "scenes": [],
            "errors": [],
        }

        for idx, scene in enumerate(script.get("scenes", [])):
            scene_num = idx + 1
            try:
                result = self._generate_scene(
                    scene=scene,
                    scene_number=scene_num,
                    scenes_dir=scenes_dir,
                    example_scene=example_scene,
                )
                results["scenes"].append(result)
                print(f"  Generated scene {scene_num}: {result['component_name']}")
            except Exception as e:
                error = {"scene_number": scene_num, "error": str(e)}
                results["errors"].append(error)
                print(f"  Error generating scene {scene_num}: {e}")

        # Generate index.ts
        self._generate_index(scenes_dir, results["scenes"], script.get("title", "Untitled"))

        return results

    def _generate_scene(
        self,
        scene: dict,
        scene_number: int,
        scenes_dir: Path,
        example_scene: str,
    ) -> dict:
        """Generate a single scene component.

        Args:
            scene: Scene data from script
            scene_number: Scene number (1-indexed)
            scenes_dir: Output directory for scenes
            example_scene: Example scene code for reference

        Returns:
            Dict with scene generation result
        """
        # Extract scene info
        title = scene.get("title", f"Scene {scene_number}")
        scene_type = scene.get("scene_type", "explanation")
        duration = scene.get("duration_seconds", 20)
        voiceover = scene.get("voiceover", "")

        # Derive scene key from title - this must match how storyboard extracts keys
        # from narration scene_ids (e.g., "scene1_hook" -> "hook")
        scene_key = self._title_to_scene_key(title)

        # Handle both old and new visual formats
        if "visual_cue" in scene:
            visual_desc = scene["visual_cue"].get("description", "")
            elements = scene["visual_cue"].get("elements", [])
        else:
            visual_desc = scene.get("visual_description", "")
            elements = scene.get("key_elements", [])

        # Generate component name from title
        component_name = self._title_to_component_name(title)
        filename = f"{component_name}.tsx"
        output_path = scenes_dir / filename

        # Format elements list
        elements_str = "\n".join(f"- {e}" for e in elements) if elements else "- General scene elements"

        # Build prompt
        prompt = SCENE_GENERATION_PROMPT.format(
            scene_number=scene_number,
            title=title,
            scene_type=scene_type,
            duration=duration,
            total_frames=int(duration * 30),
            voiceover=voiceover,
            visual_description=visual_desc,
            elements=elements_str,
            component_name=component_name,
            example_scene=example_scene[:4000],  # Limit example size
            output_path=output_path,
        )

        # Generate using Claude Code
        llm_config = LLMConfig(provider="claude-code", model="claude-sonnet-4-20250514")
        llm = ClaudeCodeLLMProvider(
            llm_config,
            working_dir=self.working_dir,
            timeout=self.timeout,
        )

        # Use file write capability
        full_prompt = f"""{SCENE_SYSTEM_PROMPT}

{prompt}

Write the complete component code to the file: {output_path}
"""

        result = llm.generate_with_file_access(full_prompt, allow_writes=True)

        if not result.success:
            raise RuntimeError(f"Failed to generate scene: {result.error_message}")

        # Verify file was created
        if not output_path.exists():
            # Try to extract code from response and write manually
            code = self._extract_code(result.response)
            if code:
                with open(output_path, "w") as f:
                    f.write(code)
            else:
                raise RuntimeError(f"Scene file not created: {output_path}")

        return {
            "scene_number": scene_number,
            "title": title,
            "component_name": component_name,
            "filename": filename,
            "path": str(output_path),
            "scene_type": scene_type,
            "scene_key": scene_key,  # Derived from title, used as registry key
        }

    def _generate_styles(self, scenes_dir: Path, project_title: str) -> None:
        """Generate the styles.ts file."""
        styles_path = scenes_dir / "styles.ts"
        content = STYLES_TEMPLATE.format(project_title=project_title)
        with open(styles_path, "w") as f:
            f.write(content)

    def _generate_index(
        self,
        scenes_dir: Path,
        scenes: list[dict],
        project_title: str,
    ) -> None:
        """Generate the index.ts file."""
        # Build imports
        imports = []
        exports = []
        registry_entries = []

        for scene in scenes:
            name = scene["component_name"]
            filename = scene["filename"].replace(".tsx", "")
            # Use scene_key as registry key - derived from title to match storyboard
            # (storyboard extracts keys from narration scene_ids, which are based on titles)
            scene_key = scene["scene_key"]

            imports.append(f'import {{ {name} }} from "./{filename}";')
            exports.append(f"export {{ {name} }} from \"./{filename}\";")
            registry_entries.append(f'  {scene_key}: {name},')

        content = INDEX_TEMPLATE.format(
            project_title=project_title,
            imports="\n".join(imports),
            exports="\n".join(exports),
            registry_entries="\n".join(registry_entries),
        )

        index_path = scenes_dir / "index.ts"
        with open(index_path, "w") as f:
            f.write(content)

    def _load_example_scene(self, example_dir: Path | None = None) -> str:
        """Load an example scene for reference."""
        # Default to llm-inference scenes
        if example_dir is None:
            example_dir = Path(__file__).parent.parent.parent / "projects" / "llm-inference" / "scenes"

        if not example_dir.exists():
            return "// No example scene available"

        # Try to load a good example scene
        example_files = ["PhasesScene.tsx", "HookScene.tsx", "BottleneckScene.tsx"]
        for filename in example_files:
            path = example_dir / filename
            if path.exists():
                with open(path) as f:
                    return f.read()

        # Fall back to any .tsx file
        tsx_files = list(example_dir.glob("*.tsx"))
        if tsx_files:
            with open(tsx_files[0]) as f:
                return f.read()

        return "// No example scene available"

    def _title_to_component_name(self, title: str) -> str:
        """Convert a scene title to a component name."""
        # Remove special characters and convert to PascalCase
        words = re.sub(r"[^a-zA-Z0-9\s]", "", title).split()
        pascal = "".join(word.capitalize() for word in words)
        return f"{pascal}Scene"

    def _component_to_registry_key(self, component_name: str) -> str:
        """Convert component name to registry key."""
        # Remove 'Scene' suffix and convert to snake_case
        name = component_name.replace("Scene", "")
        # Insert underscore before capitals and lowercase
        key = re.sub(r"([a-z])([A-Z])", r"\1_\2", name).lower()
        return key

    def _title_to_scene_key(self, title: str) -> str:
        """Convert a scene title to a scene key for registry.

        This must match how narration generates scene_ids (e.g., "scene1_hook").
        The storyboard extracts keys from scene_ids using split("_", 1)[1].

        Examples:
            "The Pixel Problem" -> "hook" (matches scene_type for hook)
            "The Tokenization Challenge" -> "tokenization_challenge"
            "Cutting Images Into Visual Words" -> "cutting_patches"
        """
        # Remove common prefixes like "The", "A", "An"
        words = title.split()
        if words and words[0].lower() in ("the", "a", "an"):
            words = words[1:]

        # Convert to snake_case: lowercase with underscores
        key = "_".join(word.lower() for word in words)

        # Remove any non-alphanumeric characters except underscores
        key = re.sub(r"[^a-z0-9_]", "", key)

        # Collapse multiple underscores
        key = re.sub(r"_+", "_", key).strip("_")

        return key

    def _title_to_registry_name(self, title: str) -> str:
        """Convert project title to registry constant name."""
        # Convert to UPPER_SNAKE_CASE
        words = re.sub(r"[^a-zA-Z0-9\s]", "", title).split()
        return "_".join(word.upper() for word in words[:3]) + "_SCENES"

    def _extract_code(self, response: str) -> str | None:
        """Extract TypeScript code from response."""
        # Try to find code block
        patterns = [
            r"```(?:typescript|tsx|ts)?\s*([\s\S]*?)```",
            r"```\s*([\s\S]*?)```",
        ]
        for pattern in patterns:
            match = re.search(pattern, response)
            if match:
                return match.group(1).strip()

        # If response looks like code, return as-is
        if "import" in response and "export" in response:
            return response.strip()

        return None


def generate_scenes(
    project_dir: Path,
    script_path: Path | None = None,
    force: bool = False,
    timeout: int = 300,
) -> dict[str, Any]:
    """Convenience function to generate all scenes for a project.

    Args:
        project_dir: Path to project directory
        script_path: Optional custom script path
        force: Overwrite existing scenes
        timeout: Timeout for each scene generation

    Returns:
        Generation results dict
    """
    generator = SceneGenerator(timeout=timeout)
    return generator.generate_all_scenes(
        project_dir=project_dir,
        script_path=script_path,
        force=force,
    )
