"""Short generator - creates YouTube Shorts from existing projects."""

import json
from pathlib import Path
from typing import Any

from ..config import Config, load_config
from ..models import Script
from ..project.loader import Project
from ..understanding.llm_provider import LLMProvider, get_llm_provider
from .models import (
    ShortConfig,
    ShortMode,
    ShortScene,
    ShortScript,
    ShortResult,
    HookAnalysis,
    CondensedNarration,
    SummaryAnalysis,
    SceneHighlight,
    VisualType,
    ShortsVisual,
    ShortsBeat,
    ShortsStoryboard,
    SceneComponentConfig,
    PhaseMarker,
)


def normalize_script_format(script_data: dict[str, Any]) -> dict[str, Any]:
    """Normalize script data to use visual_cue format.

    Some projects use a flat 'visual_description' field on scenes,
    while the Script model expects a nested 'visual_cue' object.
    This function normalizes both formats to the expected structure.

    Also converts old numeric scene_ids to string format.

    Args:
        script_data: Raw script data from JSON.

    Returns:
        Script data with visual_cue format.
    """
    import re

    if "scenes" not in script_data:
        return script_data

    for idx, scene in enumerate(script_data["scenes"]):
        # Convert old numeric scene_ids to string format
        scene_id = scene.get("scene_id")
        if scene_id is None or isinstance(scene_id, int):
            # Convert int to slug based on title
            title = scene.get("title", f"scene_{idx + 1}")
            slug = title.lower()
            slug = re.sub(r'[\s\-]+', '_', slug)
            slug = re.sub(r'[^a-z0-9_]', '', slug)
            slug = re.sub(r'_+', '_', slug)
            slug = slug.strip('_')
            scene["scene_id"] = slug
        elif isinstance(scene_id, str) and re.match(r'^scene\d+_', scene_id):
            # Strip "sceneN_" prefix from old format
            scene["scene_id"] = re.sub(r'^scene\d+_', '', scene_id)

        # Already has visual_cue - no conversion needed
        if "visual_cue" in scene:
            continue

        # Convert flat visual_description to visual_cue object
        if "visual_description" in scene:
            scene["visual_cue"] = {
                "description": scene.pop("visual_description"),
                "visual_type": "animation",  # Default type
                "elements": [],
                "duration_seconds": scene.get("duration_seconds", 5.0),
            }

    # Add source_document if missing (some formats don't have it)
    if "source_document" not in script_data:
        script_data["source_document"] = ""

    return script_data


def merge_number_tokens(timestamps: list[dict]) -> list[dict]:
    """Merge adjacent tokens that form a single number.

    Whisper often splits numbers like "150,528" into separate tokens:
    ["150", ",528"] or ["150", ",", "528"]. This function merges them
    back into a single token for better caption display.

    Args:
        timestamps: List of word timestamp dicts with 'word', 'start_seconds', 'end_seconds'.

    Returns:
        List with number tokens merged.
    """
    if not timestamps:
        return timestamps

    import re

    merged = []
    i = 0

    while i < len(timestamps):
        current = timestamps[i]
        word = current["word"]

        # Check if this could be the start of a number sequence
        # Pattern: digits optionally followed by comma/period fragments
        if re.match(r"^\d+[,.]?$", word):
            # Look ahead for continuation tokens (comma + digits, or just digits)
            combined_word = word
            end_seconds = current["end_seconds"]
            j = i + 1

            while j < len(timestamps):
                next_word = timestamps[j]["word"]
                # Match: ",528" or ".5" or just continuation digits
                if re.match(r"^[,.]\d+$", next_word):
                    combined_word += next_word
                    end_seconds = timestamps[j]["end_seconds"]
                    j += 1
                # Match standalone comma/period followed by digits
                elif next_word in [",", "."] and j + 1 < len(timestamps):
                    following = timestamps[j + 1]["word"]
                    if re.match(r"^\d+$", following):
                        combined_word += next_word + following
                        end_seconds = timestamps[j + 1]["end_seconds"]
                        j += 2
                    else:
                        break
                else:
                    break

            merged.append({
                "word": combined_word,
                "start_seconds": current["start_seconds"],
                "end_seconds": end_seconds,
            })
            i = j
        else:
            merged.append(current)
            i += 1

    return merged


HOOK_ANALYSIS_SYSTEM_PROMPT = """You are an expert at creating viral YouTube Shorts.

Your job is to analyze a full video script and identify the SINGLE most intriguing 30-45 second segment that would make viewers desperate to watch the full video.

The best hooks:
- Create immediate curiosity or surprise
- Don't give away the full solution
- End with an implicit "how did they solve this?" question
- Have high information density
- Use specific numbers or surprising facts
- Feel incomplete - viewers MUST click to learn more"""


HOOK_ANALYSIS_USER_PROMPT_TEMPLATE = """Analyze this video script and identify the SINGLE most intriguing 30-45 second segment.

Criteria:
- Creates immediate curiosity or surprise
- Doesn't give away the full solution
- Ends with an implicit "how did they solve this?" question
- Has high information density
- Uses specific numbers or surprising facts

Script:
{script_json}

Current narrations for each scene:
{narrations_json}

Return JSON:
{{
  "selected_scene_ids": ["scene_id_1", "scene_id_2"],
  "hook_question": "But how did they solve this impossible problem?",
  "reasoning": "This scene opens with a striking number..."
}}

IMPORTANT:
- Select 1-3 consecutive scenes that together form a compelling 30-45 second hook
- The hook should create tension and curiosity, not resolve it
- Prefer scenes with specific numbers, surprising facts, or dramatic contrasts"""


CONDENSED_NARRATION_SYSTEM_PROMPT = """You are an expert at creating punchy, viral YouTube Short narrations.

Your job is to condense selected scenes from a longer video into a tight, engaging short that:
- Hooks instantly with a surprising fact or question
- Builds tension and curiosity
- Ends with a cliffhanger that drives viewers to the full video

Style:
- Dense, punchy delivery (no filler words)
- Short sentences that hit hard
- Specific numbers and facts
- Creates an information gap that demands resolution"""


CONDENSED_NARRATION_USER_PROMPT_TEMPLATE = """Create a condensed {duration}s narration for a YouTube Short from these scenes.

Requirements:
- Dense, punchy delivery (no filler words)
- Build to a cliffhanger question at the end
- Don't reveal the solution - create curiosity
- Include specific numbers/facts from the original
- Target word count: ~{word_count} words (2.5 words per second)

Selected scenes and their original narration:
{scene_narrations}

CTA voiceover to generate (5 seconds, ~12 words):
Should end with something like "Full breakdown in the description."

Return JSON:
{{
  "condensed_narration": "The punchy condensed narration text...",
  "cta_narration": "Want to know how they solved this? Full breakdown in the description.",
  "hook_question": "But how did they actually solve this?"
}}

IMPORTANT:
- The condensed_narration should be tighter and punchier than the original
- End with tension, not resolution
- The CTA should feel natural and create urgency"""


# =============================================================================
# SUMMARY MODE PROMPTS
# =============================================================================

SUMMARY_ANALYSIS_SYSTEM_PROMPT = """You are an expert at creating viral YouTube Shorts that tease full-length videos.

Your job is to analyze an ENTIRE video script and extract the most compelling teaser elements from EVERY scene. The goal is to create a rapid-fire montage that showcases the breadth and depth of the full video.

For each scene, identify:
- A 2-5 word "teaser phrase" that captures the essence
- Any specific numbers that would hook viewers
- The visual concept that best represents this layer

The summary should create intrigue through ACCUMULATION - viewers should be overwhelmed by how much content exists and feel compelled to watch the full breakdown."""


SUMMARY_ANALYSIS_USER_PROMPT_TEMPLATE = """Analyze this ENTIRE video script and extract teaser elements from EVERY scene.

Script title: {title}
Total scenes: {total_scenes}

Script:
{script_json}

Current narrations for each scene:
{narrations_json}

For EACH scene, provide:
1. A teaser_phrase (2-5 words that capture the essence)
2. A key_number (specific stat if available, empty string if none)
3. A visual_hint (what visual concept represents this: "grid", "flow", "number", "code", "diagram")

Also determine:
- narrative_arc: The overall story structure ("journey", "descent", "transformation", "discovery")
- hook_opening: A compelling 1-2 sentence opening (e.g., "You press a key. 300 milliseconds later, an AI responds.")
- intrigue_close: A closing line before CTA that emphasizes the breadth (e.g., "19 layers. From quantum physics to global networks.")

Return JSON:
{{
  "scene_highlights": [
    {{
      "scene_id": "the_browser",
      "scene_title": "The Browser",
      "teaser_phrase": "60 frames per second",
      "key_number": "16ms",
      "visual_hint": "flow"
    }},
    ...
  ],
  "narrative_arc": "descent",
  "hook_opening": "You press a key. 300 milliseconds later, an AI responds. In that blink of an eye—nineteen layers of technology.",
  "intrigue_close": "Nineteen layers. From quantum physics to global networks.",
  "total_scenes": {total_scenes}
}}

IMPORTANT:
- Include ALL scenes - this is a summary, not a selection
- Teaser phrases should be punchy and memorable
- Extract specific numbers whenever possible (they hook viewers)
- The hook_opening should create immediate curiosity
- The intrigue_close should emphasize the SCALE of what's covered"""


SUMMARY_NARRATION_SYSTEM_PROMPT = """You are an expert at creating rapid-fire, montage-style YouTube Short narrations.

Your job is to create a SUMMARY narration that sweeps through an entire video's content in 60 seconds or less. Unlike hook-style shorts that deep-dive into one moment, summary shorts create intrigue through BREADTH.

Style:
- Rapid-fire, punchy phrases (2-5 words per concept)
- Build momentum through accumulation
- Use specific numbers to add credibility
- Create a sense of overwhelming depth
- End with scale/scope emphasis, not a question

The viewer should think: "Wow, there's so much here - I need to see the full breakdown!"

Structure:
1. Hook opening (establish the premise)
2. Rapid sweep through all layers (brief mention of each)
3. Closing that emphasizes scale
4. CTA driving to full video"""


SUMMARY_NARRATION_USER_PROMPT_TEMPLATE = """Create a {duration}s summary narration that sweeps through ALL scenes of this video.

Video title: {title}
Total scenes: {total_scenes}

Scene highlights to weave together:
{scene_highlights_json}

Narrative arc: {narrative_arc}
Hook opening: {hook_opening}
Intrigue close: {intrigue_close}

Requirements:
- Target word count: ~{word_count} words (2.5 words per second)
- Touch on EVERY scene briefly (2-5 words each during the sweep)
- Use specific numbers where available
- Build momentum through the sweep
- End with the intrigue_close, NOT a question

CTA voiceover to generate (8-10 seconds, ~20-25 words):
Should emphasize the depth available and drive to full video.
Example: "Nineteen layers of technology. Each one a feat of engineering. See the complete journey—full breakdown in the description."

Return JSON:
{{
  "condensed_narration": "The rapid-fire sweep narration covering all scenes...",
  "cta_narration": "Nineteen layers of technology. Each one a feat of engineering. See the complete journey—full breakdown in the description.",
  "intrigue_close": "Nineteen layers. From quantum physics to global networks."
}}

IMPORTANT:
- This is a SUMMARY, not a deep dive - touch everything briefly
- Use the teaser_phrases as inspiration but create flowing prose
- Numbers hook viewers - include as many as fit naturally
- Build a sense of overwhelming scale and depth
- The narration should feel like a breathless sweep through layers"""


VISUAL_EXTRACTION_SYSTEM_PROMPT = """You are an expert at creating VISUALLY COMPELLING content for viral YouTube Shorts.

## Your Primary Goal

Create visuals that SHOW the concept being explained - not just display text. Shorts viewers scroll past boring text in 0.5 seconds.

## What Good Shorts Visuals Look Like

**Example 1 - Grid/Matrix Concept:**
Caption: "Every image gets divided into a grid of patches"
Visual: patch_grid with 8x8 animated cells lighting up in sequence
Why it works: Shows the actual division happening, not just "Grid" text

**Example 2 - Connections/Relationships:**
Caption: "Each element connects to every other element"
Visual: attention_visual with glowing heatmap cells
Why it works: Visualizes the connections, not just describes them

**Example 3 - Dimensions/Vectors:**
Caption: "Transformed into a 768-dimensional representation"
Visual: embedding_bars with 16 animated bars of varying heights
Why it works: Shows magnitude and dimensionality visually

**Example 4 - Processing/Flow:**
Caption: "Data flows through multiple transformation stages"
Visual: flow_diagram with animated arrows between nodes
Why it works: Shows the flow direction and stages

## Core Principles

1. SHOW, don't tell. If the caption describes a process, animate that process.
2. Match visual to content. What is the caption actually about?
3. Animated > Static. Moving visuals hold attention longer.
4. One concept per beat. Don't overcrowd with multiple ideas.
5. Extract specific numbers from captions when they appear."""


VISUAL_EXTRACTION_USER_PROMPT_TEMPLATE = """Break this short narration into visual beats for a YouTube Short.

Narration:
{narration}

{source_context}

Target duration: {duration} seconds
Aim for {beat_count} beats (each ~{beat_duration} seconds)

IMPORTANT: Choose visuals that SHOW the concept, not just display text. Prefer animated components.

For each beat, specify:
1. caption_text: The exact portion of narration (will be shown as captions)
2. visual_type: The component type (prefer: patch_grid, token_grid, flow_diagram, embedding_bars)
3. primary_text: Short label for the visual (optional for animated components)
4. scene_config: Configuration for animated components

Return JSON:
{{
  "beats": [
    {{
      "caption_text": "A single image has over 150,000 pixels",
      "visual_type": "patch_grid",
      "primary_text": "150,528 pixels",
      "scene_config": {{
        "rows": 12,
        "cols": 12,
        "animate_sequence": true,
        "show_count": true
      }},
      "color": "primary"
    }},
    {{
      "caption_text": "Vision transformers cut it into patches",
      "visual_type": "patch_grid",
      "primary_text": "196 patches",
      "scene_config": {{
        "rows": 14,
        "cols": 14,
        "patch_size": 16,
        "show_labels": true
      }},
      "color": "accent"
    }},
    {{
      "caption_text": "Each patch becomes a token that flows through the model",
      "visual_type": "flow_diagram",
      "primary_text": "",
      "scene_config": {{
        "nodes": ["Image", "Patches", "Embeddings", "Transformer", "Output"],
        "direction": "horizontal"
      }},
      "color": "primary"
    }},
    {{
      "caption_text": "Every patch attends to every other patch",
      "visual_type": "token_grid",
      "primary_text": "Self-Attention",
      "scene_config": {{
        "mode": "prefill",
        "rows": 4,
        "cols": 4,
        "tokens": ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9", "P10", "P11", "P12", "P13", "P14", "P15", "P16"],
        "show_connections": true
      }},
      "color": "accent"
    }},
    {{
      "caption_text": "But how do patches become mathematical language?",
      "visual_type": "question",
      "primary_text": "How do patches become math?",
      "color": "accent"
    }}
  ],
  "hook_question": "But how do patches become math?"
}}

TEXT Visual types: big_number, comparison, text_highlight, simple_flow, icon_stat, key_point, question
SCENE Visual types: token_grid, progress_bars, code_block, diagram
Colors: primary (blue), secondary (orange), accent (purple), success (green), warning (yellow)

IMPORTANT:
- Each beat should have ONE clear visual focus
- Use scene components when the content is technical (tokens, performance, code)
- Use text-based visuals for simpler concepts (numbers, comparisons, questions)
- Extract specific numbers when possible
- The caption_text should be a direct portion of the narration
- Make the last beat a question or cliffhanger if possible"""


class ShortGenerator:
    """Generates YouTube Shorts from existing projects."""

    def __init__(self, config: Config | None = None, llm: LLMProvider | None = None):
        """Initialize the generator.

        Args:
            config: Configuration object. If None, loads default.
            llm: LLM provider. If None, creates one from config.
        """
        self.config = config or load_config()
        self.llm = llm or get_llm_provider(self.config)

    def analyze_for_hook(
        self,
        script: Script,
        narrations: list[dict[str, Any]],
    ) -> HookAnalysis:
        """Use LLM to identify the most intriguing 30-45s hook.

        Args:
            script: The full video script.
            narrations: List of scene narrations.

        Returns:
            HookAnalysis with selected scenes and hook question.
        """
        script_data = script.model_dump()
        prompt = HOOK_ANALYSIS_USER_PROMPT_TEMPLATE.format(
            script_json=json.dumps(script_data, indent=2),
            narrations_json=json.dumps(narrations, indent=2),
        )

        result = self.llm.generate_json(prompt, HOOK_ANALYSIS_SYSTEM_PROMPT)

        return HookAnalysis(
            selected_scene_ids=result.get("selected_scene_ids", []),
            hook_question=result.get("hook_question", "But how did they solve this?"),
            reasoning=result.get("reasoning", ""),
        )

    def generate_condensed_narration(
        self,
        script: Script,
        narrations: list[dict[str, Any]],
        selected_scene_ids: list[str],
        target_duration: int = 45,
    ) -> CondensedNarration:
        """Generate condensed narration optimized for shorts.

        Args:
            script: The full video script.
            narrations: List of all scene narrations.
            selected_scene_ids: IDs of scenes to include.
            target_duration: Target duration in seconds.

        Returns:
            CondensedNarration with narration text and hook question.
        """
        # Filter narrations to selected scenes
        selected_narrations = [
            n for n in narrations if n.get("scene_id") in selected_scene_ids
        ]

        # Calculate target word count (2.5 words per second)
        word_count = int(target_duration * 2.5)

        prompt = CONDENSED_NARRATION_USER_PROMPT_TEMPLATE.format(
            duration=target_duration,
            word_count=word_count,
            scene_narrations=json.dumps(selected_narrations, indent=2),
        )

        result = self.llm.generate_json(prompt, CONDENSED_NARRATION_SYSTEM_PROMPT)

        return CondensedNarration(
            condensed_narration=result.get("condensed_narration", ""),
            cta_narration=result.get(
                "cta_narration",
                "Want to know how they solved this? Full breakdown in the description.",
            ),
            hook_question=result.get("hook_question", "But how did they solve this?"),
        )

    def analyze_for_summary(
        self,
        script: Script,
        narrations: list[dict[str, Any]],
    ) -> SummaryAnalysis:
        """Analyze script to extract teaser elements from ALL scenes for summary mode.

        Unlike analyze_for_hook which selects scenes, this extracts highlights
        from every scene to create a rapid-fire summary.

        Args:
            script: The full video script.
            narrations: List of scene narrations.

        Returns:
            SummaryAnalysis with highlights from all scenes.
        """
        script_data = script.model_dump()
        total_scenes = len(script_data.get("scenes", []))

        prompt = SUMMARY_ANALYSIS_USER_PROMPT_TEMPLATE.format(
            title=script.title,
            total_scenes=total_scenes,
            script_json=json.dumps(script_data, indent=2),
            narrations_json=json.dumps(narrations, indent=2),
        )

        result = self.llm.generate_json(prompt, SUMMARY_ANALYSIS_SYSTEM_PROMPT)

        # Parse scene highlights
        scene_highlights = []
        for h in result.get("scene_highlights", []):
            scene_highlights.append(
                SceneHighlight(
                    scene_id=h.get("scene_id", ""),
                    scene_title=h.get("scene_title", ""),
                    teaser_phrase=h.get("teaser_phrase", ""),
                    key_number=h.get("key_number", ""),
                    visual_hint=h.get("visual_hint", ""),
                )
            )

        return SummaryAnalysis(
            scene_highlights=scene_highlights,
            narrative_arc=result.get("narrative_arc", "journey"),
            hook_opening=result.get("hook_opening", ""),
            intrigue_close=result.get("intrigue_close", ""),
            total_scenes=total_scenes,
        )

    def generate_summary_narration(
        self,
        script: Script,
        narrations: list[dict[str, Any]],
        summary_analysis: SummaryAnalysis,
        target_duration: int = 60,
    ) -> CondensedNarration:
        """Generate summary narration that sweeps through ALL scenes.

        Unlike generate_condensed_narration which deep-dives into selected scenes,
        this creates a rapid-fire overview of the entire video content.

        Args:
            script: The full video script.
            narrations: List of all scene narrations.
            summary_analysis: Analysis with highlights from all scenes.
            target_duration: Target duration in seconds (max 60).

        Returns:
            CondensedNarration with summary narration and CTA.
        """
        # Cap at 60 seconds for shorts
        target_duration = min(target_duration, 60)

        # Calculate target word count (2.5 words per second)
        word_count = int(target_duration * 2.5)

        # Convert scene highlights to JSON for the prompt
        highlights_data = [h.model_dump() for h in summary_analysis.scene_highlights]

        prompt = SUMMARY_NARRATION_USER_PROMPT_TEMPLATE.format(
            duration=target_duration,
            title=script.title,
            total_scenes=summary_analysis.total_scenes,
            scene_highlights_json=json.dumps(highlights_data, indent=2),
            narrative_arc=summary_analysis.narrative_arc,
            hook_opening=summary_analysis.hook_opening,
            intrigue_close=summary_analysis.intrigue_close,
            word_count=word_count,
        )

        result = self.llm.generate_json(prompt, SUMMARY_NARRATION_SYSTEM_PROMPT)

        return CondensedNarration(
            condensed_narration=result.get("condensed_narration", ""),
            cta_narration=result.get(
                "cta_narration",
                "See the complete journey. Full breakdown in the description.",
            ),
            hook_question=result.get(
                "intrigue_close",
                summary_analysis.intrigue_close or "The full journey awaits.",
            ),
        )

    def generate_short(
        self,
        project: Project,
        variant: str = "default",
        duration: int | None = None,
        scene_ids: list[str] | None = None,
        mode: str = "hook",
        force: bool = False,
        mock: bool = False,
    ) -> ShortResult:
        """Complete short generation pipeline.

        Args:
            project: The source project.
            variant: Variant name for multiple shorts from same project.
            duration: Target duration in seconds. Defaults to 45 for hook mode, 60 for summary mode.
            scene_ids: Optional override for scene selection (only for hook mode).
            mode: Generation mode - "hook" (deep dive into selected scenes) or "summary" (sweep all scenes).
            force: Force regeneration even if files exist.
            mock: Use mock data for testing.

        Returns:
            ShortResult with paths to generated files.
        """
        # Validate and normalize mode
        try:
            short_mode = ShortMode(mode)
        except ValueError:
            return ShortResult(
                success=False,
                variant=variant,
                error=f"Invalid mode: {mode}. Must be 'hook' or 'summary'.",
            )

        # Set default duration based on mode
        if duration is None:
            duration = 60 if short_mode == ShortMode.SUMMARY else 45

        # Cap summary mode at 60 seconds
        if short_mode == ShortMode.SUMMARY and duration > 60:
            duration = 60
        # Setup directories
        variant_dir = project.root_dir / "short" / variant
        variant_dir.mkdir(parents=True, exist_ok=True)

        short_script_path = variant_dir / "short_script.json"
        scenes_dir = variant_dir / "scenes"
        voiceover_dir = variant_dir / "voiceover"
        storyboard_dir = variant_dir / "storyboard"
        output_dir = variant_dir / "output"

        for d in [scenes_dir, voiceover_dir, storyboard_dir, output_dir]:
            d.mkdir(parents=True, exist_ok=True)

        try:
            # 1. Load existing script and narrations
            script_path = project.get_path("script")
            if not script_path.exists():
                return ShortResult(
                    success=False,
                    variant=variant,
                    error="Script not found. Run 'script' command first.",
                )

            with open(script_path) as f:
                script_data = json.load(f)
            # Normalize script format (handles visual_description -> visual_cue conversion)
            script_data = normalize_script_format(script_data)
            script = Script(**script_data)

            narration_path = project.get_path("narration")
            if not narration_path.exists():
                return ShortResult(
                    success=False,
                    variant=variant,
                    error="Narrations not found. Run 'narration' command first.",
                )

            with open(narration_path) as f:
                narrations_data = json.load(f)
            narrations = narrations_data.get("scenes", [])

            # 2. Analyze and generate narration based on mode
            if short_mode == ShortMode.SUMMARY:
                # Summary mode: sweep through ALL scenes
                all_scene_ids = [n.get("scene_id") for n in narrations]

                if mock:
                    condensed_narration = CondensedNarration(
                        condensed_narration="This is a mock summary narration for testing. It would normally contain a rapid-fire sweep through all scenes.",
                        cta_narration="See the complete journey. Full breakdown in the description.",
                        hook_question="The full journey awaits.",
                    )
                else:
                    summary_analysis = self.analyze_for_summary(script, narrations)
                    condensed_narration = self.generate_summary_narration(
                        script,
                        narrations,
                        summary_analysis,
                        target_duration=duration,
                    )

                selected_scene_ids = all_scene_ids
                cta_text = "See the complete journey"

            else:
                # Hook mode: select compelling scenes for deep dive
                if scene_ids:
                    # User provided scene IDs - validate them
                    valid_scene_ids = {n.get("scene_id") for n in narrations}
                    invalid_ids = set(scene_ids) - valid_scene_ids
                    if invalid_ids:
                        return ShortResult(
                            success=False,
                            variant=variant,
                            error=f"Invalid scene IDs: {invalid_ids}. Valid IDs: {valid_scene_ids}",
                        )
                    selected_scene_ids = scene_ids
                    hook_question = "But how did they solve this?"  # Default
                else:
                    # LLM selects best hook
                    if mock:
                        # Use first 2 scenes for mock
                        selected_scene_ids = [n.get("scene_id") for n in narrations[:2]]
                        hook_question = "But how did they actually solve this impossible problem?"
                    else:
                        hook_analysis = self.analyze_for_hook(script, narrations)
                        selected_scene_ids = hook_analysis.selected_scene_ids
                        hook_question = hook_analysis.hook_question

                # Generate condensed narration for hook mode
                if mock:
                    condensed_narration = CondensedNarration(
                        condensed_narration="This is a mock condensed narration for testing. It would normally contain punchy, dense content from the selected scenes.",
                        cta_narration="Want to know how they solved this? Full breakdown in the description.",
                        hook_question=hook_question,
                    )
                else:
                    condensed_narration = self.generate_condensed_narration(
                        script,
                        narrations,
                        selected_scene_ids,
                        target_duration=duration,
                    )

                cta_text = "Full breakdown in description"

            # 3. Build short script
            short_scenes = []
            # Reserve 8s for CTA in summary mode (longer CTA), 5s for hook mode
            cta_duration = 8 if short_mode == ShortMode.SUMMARY else 5
            scene_duration = (duration - cta_duration) / len(selected_scene_ids)

            for scene_id in selected_scene_ids:
                short_scenes.append(
                    ShortScene(
                        source_scene_id=scene_id,
                        duration_seconds=scene_duration,
                    )
                )

            short_script = ShortScript(
                source_project=project.id,
                title=f"{script.title} - Short",
                condensed_narration=condensed_narration.condensed_narration,
                hook_question=condensed_narration.hook_question,
                scenes=short_scenes,
                cta_text=cta_text,
                cta_narration=condensed_narration.cta_narration,
                total_duration_seconds=duration,
                mode=short_mode,
            )

            # 4. Save short script
            with open(short_script_path, "w", encoding="utf-8") as f:
                json.dump(short_script.model_dump(), f, indent=2, ensure_ascii=False)

            return ShortResult(
                success=True,
                variant=variant,
                short_script_path=short_script_path,
                scenes_dir=scenes_dir,
                voiceover_dir=voiceover_dir,
                storyboard_path=storyboard_dir / "storyboard.json",
                output_path=output_dir / "short.mp4",
            )

        except Exception as e:
            return ShortResult(
                success=False,
                variant=variant,
                error=str(e),
            )

    def generate_mock_short_script(
        self,
        project_id: str,
        topic: str,
        duration: int = 45,
    ) -> ShortScript:
        """Generate mock short script for testing.

        Args:
            project_id: Source project ID.
            topic: Topic for the mock content.
            duration: Target duration in seconds.

        Returns:
            Mock ShortScript for testing.
        """
        return ShortScript(
            source_project=project_id,
            title=f"{topic} - Short",
            condensed_narration=f"Here's something that will blow your mind about {topic}. The numbers are staggering—and the solution? Completely unexpected. Traditional approaches failed completely. But one team found a way that nobody expected.",
            hook_question=f"But how did they actually solve the {topic} problem?",
            scenes=[
                ShortScene(
                    source_scene_id="scene1_hook",
                    duration_seconds=(duration - 5) / 2,
                ),
                ShortScene(
                    source_scene_id="scene2_insight",
                    duration_seconds=(duration - 5) / 2,
                ),
            ],
            cta_text="Full breakdown in description",
            cta_narration="Want to know how they solved this? Full breakdown in the description.",
            total_duration_seconds=duration,
        )

    def save_short_script(self, short_script: ShortScript, path: Path) -> None:
        """Save short script to file.

        Args:
            short_script: The short script to save.
            path: Path to save the script.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(short_script.model_dump(), f, indent=2, ensure_ascii=False)

    @staticmethod
    def load_short_script(path: Path) -> ShortScript:
        """Load short script from file.

        Args:
            path: Path to the short script file.

        Returns:
            Loaded ShortScript object.
        """
        with open(path) as f:
            data = json.load(f)
        return ShortScript(**data)

    def extract_visual_beats(
        self,
        narration: str,
        duration: int = 40,
        beat_count: int = 6,
        source_script: Script | None = None,
    ) -> list[dict[str, Any]]:
        """Extract visual beats from narration using LLM.

        Args:
            narration: The condensed narration text.
            duration: Total duration in seconds.
            beat_count: Target number of beats.
            source_script: Optional source script for context about visuals.

        Returns:
            List of beat dictionaries with visual specifications.
        """
        beat_duration = duration / beat_count

        # Build source context from original script if available
        source_context = ""
        if source_script:
            source_context = "Original video context (for visual ideas):\n"
            for scene in source_script.scenes[:5]:  # Limit to first 5 scenes
                visual_cue = scene.visual_cue
                source_context += f"- Scene: {scene.title}\n"
                source_context += f"  Visual type: {visual_cue.visual_type}\n"
                source_context += f"  Elements: {', '.join(visual_cue.elements)}\n"
                source_context += f"  Description: {visual_cue.description}\n"

        prompt = VISUAL_EXTRACTION_USER_PROMPT_TEMPLATE.format(
            narration=narration,
            duration=duration,
            beat_count=beat_count,
            beat_duration=f"{beat_duration:.1f}",
            source_context=source_context,
        )

        result = self.llm.generate_json(prompt, VISUAL_EXTRACTION_SYSTEM_PROMPT)
        return result.get("beats", [])

    def generate_shorts_storyboard(
        self,
        short_script: ShortScript,
        mock: bool = False,
    ) -> ShortsStoryboard:
        """Generate a complete shorts storyboard with visual beats.

        Args:
            short_script: The short script with condensed narration.
            mock: Use mock data for testing.

        Returns:
            ShortsStoryboard with visual beats.
        """
        # Get the condensed narration from the script
        full_narration = short_script.condensed_narration

        # Calculate timing
        content_duration = short_script.total_duration_seconds - 5  # Reserve 5s for CTA
        beat_count = max(4, int(content_duration / 6))  # ~6 seconds per beat

        if mock:
            # Generate mock beats
            beats_data = self._generate_mock_beats(full_narration, content_duration, beat_count)
        else:
            # Use LLM to extract visual beats
            beats_data = self.extract_visual_beats(
                full_narration,
                duration=int(content_duration),
                beat_count=beat_count,
            )

        # Convert to ShortsBeat objects with timing
        beats: list[ShortsBeat] = []
        beat_duration = content_duration / len(beats_data) if beats_data else content_duration

        for i, beat_data in enumerate(beats_data):
            start_time = i * beat_duration
            end_time = (i + 1) * beat_duration

            # Parse scene_config if present
            scene_config = None
            if "scene_config" in beat_data:
                config_data = beat_data["scene_config"]
                scene_config = SceneComponentConfig(
                    component_type=beat_data.get("visual_type", ""),
                    props=config_data.get("props", {}),
                    tokens=config_data.get("tokens", []),
                    mode=config_data.get("mode", "prefill"),
                    rows=config_data.get("rows", 4),
                    cols=config_data.get("cols", 4),
                    bars=config_data.get("bars", []),
                    code=config_data.get("code", ""),
                    language=config_data.get("language", "python"),
                    highlight_lines=config_data.get("highlight_lines", []),
                    image_path=config_data.get("image_path", ""),
                    caption=config_data.get("caption", ""),
                )

            visual = ShortsVisual(
                type=VisualType(beat_data.get("visual_type", "text_highlight")),
                primary_text=beat_data.get("primary_text", ""),
                secondary_text=beat_data.get("secondary_text", ""),
                tertiary_text=beat_data.get("tertiary_text", ""),
                icon=beat_data.get("icon", ""),
                color=beat_data.get("color", "primary"),
                scene_config=scene_config,
            )

            beats.append(ShortsBeat(
                id=f"beat_{i + 1}",
                start_seconds=start_time,
                end_seconds=end_time,
                visual=visual,
                caption_text=beat_data.get("caption_text", ""),
                word_timestamps=[],  # Will be filled by voiceover generation
            ))

        # Add CTA beat at the end
        cta_beat = ShortsBeat(
            id="cta",
            start_seconds=content_duration,
            end_seconds=short_script.total_duration_seconds,
            visual=ShortsVisual(
                type=VisualType.QUESTION,
                primary_text=short_script.hook_question,
                color="accent",
            ),
            caption_text=short_script.cta_narration,
            word_timestamps=[],
        )
        beats.append(cta_beat)

        return ShortsStoryboard(
            id=f"{short_script.source_project}_short",
            title=short_script.title,
            total_duration_seconds=short_script.total_duration_seconds,
            beats=beats,
            hook_question=short_script.hook_question,
            cta_text=short_script.cta_text,
        )

    def _generate_mock_beats(
        self,
        narration: str,
        duration: float,
        beat_count: int,
    ) -> list[dict[str, Any]]:
        """Generate mock beats for testing.

        Args:
            narration: The narration text.
            duration: Total duration.
            beat_count: Number of beats to generate.

        Returns:
            List of mock beat data.
        """
        # Split narration roughly into beat_count parts
        words = narration.split()
        words_per_beat = max(1, len(words) // beat_count)

        mock_visual_types = [
            ("big_number", "150,528", "pixels in one image", "primary"),
            ("comparison", "2,000", "150,000+", "warning"),
            ("text_highlight", "75× longer", "than typical text sequences", "accent"),
            ("key_point", "The solution?", "Cut the image into patches", "success"),
            ("simple_flow", "Image", "Patches", "primary"),
            ("icon_stat", "16×16", "pixel patches", "secondary"),
        ]

        beats = []
        for i in range(beat_count):
            start_idx = i * words_per_beat
            end_idx = min((i + 1) * words_per_beat, len(words))
            caption = " ".join(words[start_idx:end_idx])

            visual_type, primary, secondary, color = mock_visual_types[i % len(mock_visual_types)]

            beats.append({
                "caption_text": caption if caption else f"Beat {i + 1} content",
                "visual_type": visual_type,
                "primary_text": primary,
                "secondary_text": secondary,
                "tertiary_text": "",
                "icon": "",
                "color": color,
            })

        return beats

    def save_shorts_storyboard(self, storyboard: ShortsStoryboard, path: Path) -> None:
        """Save shorts storyboard to file.

        Args:
            storyboard: The storyboard to save.
            path: Path to save the storyboard.
        """
        path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to dict, handling enum values
        def serialize_beat(beat: ShortsBeat) -> dict:
            visual_dict = {
                "type": beat.visual.type.value,
                "primary_text": beat.visual.primary_text,
                "secondary_text": beat.visual.secondary_text,
                "tertiary_text": beat.visual.tertiary_text,
                "icon": beat.visual.icon,
                "color": beat.visual.color,
            }

            # Include scene_config if present
            if beat.visual.scene_config:
                visual_dict["scene_config"] = beat.visual.scene_config.model_dump()

            # Include source_scene_id if present
            if beat.visual.source_scene_id:
                visual_dict["source_scene_id"] = beat.visual.source_scene_id

            result = {
                "id": beat.id,
                "start_seconds": beat.start_seconds,
                "end_seconds": beat.end_seconds,
                "visual": visual_dict,
                "caption_text": beat.caption_text,
                "word_timestamps": beat.word_timestamps,
            }

            # Include custom scene generation fields if present
            if beat.visual_description:
                result["visual_description"] = beat.visual_description
            if beat.visual_elements:
                result["visual_elements"] = beat.visual_elements
            if beat.component_name:
                result["component_name"] = beat.component_name
            if beat.source_scene_file:
                result["source_scene_file"] = beat.source_scene_file

            # Include phase markers for timing synchronization
            if beat.phase_markers:
                result["phase_markers"] = [
                    {
                        "id": marker.id,
                        "end_word": marker.end_word,
                        "description": marker.description,
                    }
                    for marker in beat.phase_markers
                ]

            return result

        data = {
            "id": storyboard.id,
            "title": storyboard.title,
            "total_duration_seconds": storyboard.total_duration_seconds,
            "beats": [serialize_beat(beat) for beat in storyboard.beats],
            "hook_question": storyboard.hook_question,
            "cta_text": storyboard.cta_text,
            "voiceover_path": storyboard.voiceover_path,
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @staticmethod
    def load_shorts_storyboard(path: Path) -> ShortsStoryboard:
        """Load shorts storyboard from file.

        Args:
            path: Path to the storyboard file.

        Returns:
            Loaded ShortsStoryboard object.
        """
        with open(path) as f:
            data = json.load(f)

        # Convert beats back to objects
        beats = []
        for beat_data in data.get("beats", []):
            visual_data = beat_data.get("visual", {})

            # Parse scene_config if present
            scene_config = None
            if "scene_config" in visual_data:
                config_data = visual_data["scene_config"]
                scene_config = SceneComponentConfig(**config_data)

            visual = ShortsVisual(
                type=VisualType(visual_data.get("type", "text_highlight")),
                primary_text=visual_data.get("primary_text", ""),
                secondary_text=visual_data.get("secondary_text", ""),
                tertiary_text=visual_data.get("tertiary_text", ""),
                icon=visual_data.get("icon", ""),
                color=visual_data.get("color", "primary"),
                scene_config=scene_config,
                source_scene_id=visual_data.get("source_scene_id", ""),
            )
            # Parse phase markers if present
            phase_markers = [
                PhaseMarker(
                    id=m.get("id", ""),
                    end_word=m.get("end_word", ""),
                    description=m.get("description", ""),
                )
                for m in beat_data.get("phase_markers", [])
            ]

            beats.append(ShortsBeat(
                id=beat_data.get("id", ""),
                start_seconds=beat_data.get("start_seconds", 0),
                end_seconds=beat_data.get("end_seconds", 0),
                visual=visual,
                caption_text=beat_data.get("caption_text", ""),
                word_timestamps=beat_data.get("word_timestamps", []),
                # Custom scene generation fields
                visual_description=beat_data.get("visual_description", ""),
                visual_elements=beat_data.get("visual_elements", []),
                component_name=beat_data.get("component_name", ""),
                source_scene_file=beat_data.get("source_scene_file", ""),
                # Phase markers for timing synchronization
                phase_markers=phase_markers,
            ))

        return ShortsStoryboard(
            id=data.get("id", ""),
            title=data.get("title", ""),
            total_duration_seconds=data.get("total_duration_seconds", 0),
            beats=beats,
            hook_question=data.get("hook_question", ""),
            cta_text=data.get("cta_text", ""),
            voiceover_path=data.get("voiceover_path", ""),
        )

    def update_storyboard_with_timestamps(
        self,
        storyboard: ShortsStoryboard,
        word_timestamps: list,
    ) -> ShortsStoryboard:
        """Update storyboard beats with word timestamps from voiceover.

        Distributes word timestamps to the appropriate beats based on timing.

        Args:
            storyboard: The storyboard to update.
            word_timestamps: List of WordTimestamp objects from voiceover.

        Returns:
            Updated ShortsStoryboard with word timestamps in each beat.
        """
        # Convert WordTimestamp objects to dicts
        timestamps = [
            {
                "word": ts.word if hasattr(ts, "word") else ts.get("word", ""),
                "start_seconds": ts.start_seconds if hasattr(ts, "start_seconds") else ts.get("start_seconds", 0),
                "end_seconds": ts.end_seconds if hasattr(ts, "end_seconds") else ts.get("end_seconds", 0),
            }
            for ts in word_timestamps
        ]

        # Merge number tokens (e.g., "150" + ",528" → "150,528")
        timestamps = merge_number_tokens(timestamps)

        # Assign timestamps to beats based on timing
        for beat in storyboard.beats:
            beat_timestamps = [
                ts for ts in timestamps
                if ts["start_seconds"] >= beat.start_seconds
                and ts["start_seconds"] < beat.end_seconds
            ]
            # Adjust timestamps to be relative to beat start
            for ts in beat_timestamps:
                ts["start_seconds"] -= beat.start_seconds
                ts["end_seconds"] -= beat.start_seconds
            beat.word_timestamps = beat_timestamps

        return storyboard

    def generate_shorts_storyboard_from_voiceover(
        self,
        short_script: ShortScript,
        word_timestamps: list,
        voiceover_duration: float,
        mock: bool = False,
    ) -> ShortsStoryboard:
        """Generate storyboard from actual voiceover word timestamps.

        This ensures captions perfectly match the spoken audio by creating
        beats based on actual word timings, not arbitrary time divisions.

        Args:
            short_script: The short script with narration.
            word_timestamps: List of WordTimestamp objects from voiceover.
            voiceover_duration: Actual duration of the voiceover audio.
            mock: Use mock data for testing.

        Returns:
            ShortsStoryboard with beats aligned to actual speech.
        """
        # Convert WordTimestamp objects to dicts
        timestamps = [
            {
                "word": ts.word if hasattr(ts, "word") else ts.get("word", ""),
                "start_seconds": ts.start_seconds if hasattr(ts, "start_seconds") else ts.get("start_seconds", 0),
                "end_seconds": ts.end_seconds if hasattr(ts, "end_seconds") else ts.get("end_seconds", 0),
            }
            for ts in word_timestamps
        ]

        # Merge number tokens (e.g., "150" + ",528" → "150,528")
        timestamps = merge_number_tokens(timestamps)

        if not timestamps:
            # Fallback to old method if no timestamps
            return self.generate_shorts_storyboard(short_script, mock)

        # Group words into sentences/phrases based on punctuation and pauses
        beat_groups = self._group_words_into_beats(timestamps, voiceover_duration)

        # Create caption text for each beat
        beats_with_captions = []
        for group in beat_groups:
            caption_words = [ts["word"] for ts in group["timestamps"]]
            caption_text = " ".join(caption_words)
            beats_with_captions.append({
                "caption_text": caption_text,
                "start_seconds": group["start_seconds"],
                "end_seconds": group["end_seconds"],
                "timestamps": group["timestamps"],
            })

        # Use LLM to assign visual types to each beat based on its caption
        if mock:
            visual_specs = self._generate_mock_visuals_for_captions(beats_with_captions)
        else:
            visual_specs = self._generate_visuals_for_captions(beats_with_captions)

        # Build final beats
        beats: list[ShortsBeat] = []
        for i, (beat_data, visual_spec) in enumerate(zip(beats_with_captions, visual_specs)):
            # Parse scene_config if present
            scene_config = None
            if "scene_config" in visual_spec:
                config_data = visual_spec["scene_config"]
                scene_config = SceneComponentConfig(
                    component_type=visual_spec.get("visual_type", ""),
                    props=config_data.get("props", {}),
                    tokens=config_data.get("tokens", []),
                    mode=config_data.get("mode", "prefill"),
                    rows=config_data.get("rows", 4),
                    cols=config_data.get("cols", 4),
                    bars=config_data.get("bars", []),
                    code=config_data.get("code", ""),
                    language=config_data.get("language", "python"),
                    highlight_lines=config_data.get("highlight_lines", []),
                    image_path=config_data.get("image_path", ""),
                    caption=config_data.get("caption", ""),
                )

            # Handle visual type - fallback to text_highlight if invalid
            visual_type_str = visual_spec.get("visual_type", "text_highlight")
            try:
                visual_type = VisualType(visual_type_str)
            except ValueError:
                print(f"  Warning: Unknown visual type '{visual_type_str}', using text_highlight")
                visual_type = VisualType.TEXT_HIGHLIGHT

            visual = ShortsVisual(
                type=visual_type,
                primary_text=visual_spec.get("primary_text", ""),
                secondary_text=visual_spec.get("secondary_text", ""),
                tertiary_text=visual_spec.get("tertiary_text", ""),
                icon=visual_spec.get("icon", ""),
                color=visual_spec.get("color", "primary"),
                scene_config=scene_config,
            )

            # Convert timestamps to beat-relative (starting from 0)
            beat_timestamps = []
            for ts in beat_data["timestamps"]:
                beat_timestamps.append({
                    "word": ts["word"],
                    "start_seconds": ts["start_seconds"] - beat_data["start_seconds"],
                    "end_seconds": ts["end_seconds"] - beat_data["start_seconds"],
                })

            beats.append(ShortsBeat(
                id=f"beat_{i + 1}",
                start_seconds=beat_data["start_seconds"],
                end_seconds=beat_data["end_seconds"],
                visual=visual,
                caption_text=beat_data["caption_text"],
                word_timestamps=beat_timestamps,
            ))

        # Add CTA beat at the end (if there's time after the last word)
        last_word_end = timestamps[-1]["end_seconds"] if timestamps else voiceover_duration
        cta_start = last_word_end + 0.5  # Small gap before CTA

        # Ensure CTA timing is valid (start < end, with minimum 1s duration)
        min_cta_duration = 1.0
        if cta_start + min_cta_duration > voiceover_duration:
            # Not enough time for CTA gap, start CTA right after last word
            cta_start = last_word_end

        # Only add CTA if there's still valid timing
        if cta_start < voiceover_duration:
            cta_beat = ShortsBeat(
                id="cta",
                start_seconds=cta_start,
                end_seconds=voiceover_duration,
                visual=ShortsVisual(
                    type=VisualType.QUESTION,
                    primary_text=short_script.hook_question,
                    color="accent",
                ),
                caption_text=short_script.cta_narration,
                word_timestamps=[],  # CTA has no word timestamps (just displayed text)
            )
            beats.append(cta_beat)

        return ShortsStoryboard(
            id=f"{short_script.source_project}_short",
            title=short_script.title,
            total_duration_seconds=voiceover_duration,
            beats=beats,
            hook_question=short_script.hook_question,
            cta_text=short_script.cta_text,
        )

    def _group_words_into_beats(
        self,
        timestamps: list[dict],
        total_duration: float,
        target_beat_count: int = 6,
    ) -> list[dict]:
        """Group word timestamps into logical beats based on sentence boundaries.

        Args:
            timestamps: List of word timestamp dicts.
            total_duration: Total voiceover duration.
            target_beat_count: Approximate number of beats to create.

        Returns:
            List of beat groups, each with timestamps and timing info.
        """
        if not timestamps:
            return []

        # Find sentence boundaries (words ending with . ! ?)
        sentence_end_indices = []
        for i, ts in enumerate(timestamps):
            word = ts["word"]
            if word.endswith(('.', '!', '?', '...', '—')):
                sentence_end_indices.append(i)

        # If no sentence boundaries found, split by target duration
        if not sentence_end_indices:
            target_duration = total_duration / target_beat_count
            beat_groups = []
            current_group = {"timestamps": [], "start_seconds": 0, "end_seconds": 0}

            for ts in timestamps:
                if not current_group["timestamps"]:
                    current_group["start_seconds"] = ts["start_seconds"]

                current_group["timestamps"].append(ts)
                current_group["end_seconds"] = ts["end_seconds"]

                group_duration = current_group["end_seconds"] - current_group["start_seconds"]
                if group_duration >= target_duration and len(beat_groups) < target_beat_count - 1:
                    beat_groups.append(current_group)
                    current_group = {"timestamps": [], "start_seconds": 0, "end_seconds": 0}

            if current_group["timestamps"]:
                beat_groups.append(current_group)

            return beat_groups

        # Group by sentence boundaries, combining short sentences
        beat_groups = []
        current_group = {"timestamps": [], "start_seconds": 0, "end_seconds": 0}
        target_duration = total_duration / target_beat_count
        min_beat_duration = 3.0  # Minimum seconds per beat

        word_idx = 0
        for sentence_end_idx in sentence_end_indices:
            # Add all words up to and including the sentence end
            while word_idx <= sentence_end_idx:
                ts = timestamps[word_idx]
                if not current_group["timestamps"]:
                    current_group["start_seconds"] = ts["start_seconds"]
                current_group["timestamps"].append(ts)
                current_group["end_seconds"] = ts["end_seconds"]
                word_idx += 1

            # Check if this group is long enough to be a beat
            group_duration = current_group["end_seconds"] - current_group["start_seconds"]

            # Create new beat if: long enough AND we haven't exceeded target beat count
            if group_duration >= min_beat_duration and len(beat_groups) < target_beat_count - 1:
                beat_groups.append(current_group)
                current_group = {"timestamps": [], "start_seconds": 0, "end_seconds": 0}

        # Add remaining words to current group
        while word_idx < len(timestamps):
            ts = timestamps[word_idx]
            if not current_group["timestamps"]:
                current_group["start_seconds"] = ts["start_seconds"]
            current_group["timestamps"].append(ts)
            current_group["end_seconds"] = ts["end_seconds"]
            word_idx += 1

        if current_group["timestamps"]:
            beat_groups.append(current_group)

        return beat_groups

    def _generate_visuals_for_captions(
        self,
        beats_with_captions: list[dict],
    ) -> list[dict]:
        """Use LLM to generate visual specs for each caption.

        Args:
            beats_with_captions: List of beats with their caption text.

        Returns:
            List of visual specifications for each beat.
        """
        # Build prompt with all captions
        captions_list = "\n".join([
            f"Beat {i+1} ({b['start_seconds']:.1f}s - {b['end_seconds']:.1f}s): \"{b['caption_text']}\""
            for i, b in enumerate(beats_with_captions)
        ])

        prompt = f"""Assign visual types to these video beats. Each beat has caption text that will be spoken.

Beats:
{captions_list}

For each beat, choose a visual that SHOWS the concept being described:
- What is the caption actually about? Show that visually.
- Prefer animated visuals (grids, bars, flows) over static text.
- If the caption mentions a number, show it prominently.
- If the caption describes a process, animate that process.

Return JSON:
{{
  "visuals": [
    {{
      "visual_type": "patch_grid",
      "primary_text": "",
      "color": "primary",
      "scene_config": {{"rows": 8, "cols": 8}}
    }},
    ...
  ]
}}

Visual types available:
- patch_grid: Animated grid (config: rows, cols)
- token_grid: Processing tokens (config: rows, cols, mode)
- embedding_bars: Animated bars (config: dimensions)
- attention_visual: Heatmap connections (config: size, pattern)
- masked_grid: Grid with hidden cells (config: rows, cols, masked_indices)
- flow_diagram: Transformation flow (config: nodes, direction)
- big_number: Large statistic (primary_text = the number)
- question: Hook question (primary_text = the question)

Colors: primary, accent, warning, success"""

        result = self.llm.generate_json(prompt, VISUAL_EXTRACTION_SYSTEM_PROMPT)
        visuals = result.get("visuals", [])

        # Ensure we have a visual for each beat
        while len(visuals) < len(beats_with_captions):
            visuals.append({
                "visual_type": "patch_grid",
                "primary_text": "",
                "color": "primary",
                "scene_config": {"rows": 8, "cols": 8},
            })

        return visuals

    def _generate_mock_visuals_for_captions(
        self,
        beats_with_captions: list[dict],
    ) -> list[dict]:
        """Generate mock visual specs for testing.

        Args:
            beats_with_captions: List of beats with their caption text.

        Returns:
            List of mock visual specifications.
        """
        mock_visuals = [
            {"visual_type": "comparison", "primary_text": "50,000 vs 150,528", "secondary_text": "tokens vs pixels", "color": "primary"},
            {"visual_type": "big_number", "primary_text": "22 billion", "secondary_text": "comparisons", "color": "warning"},
            {"visual_type": "big_number", "primary_text": "16 million", "secondary_text": "colors", "color": "accent"},
            {"visual_type": "patch_grid", "primary_text": "Patches", "color": "success", "scene_config": {"rows": 14, "cols": 14}},
            {"visual_type": "patch_grid", "primary_text": "196 patches", "color": "primary", "scene_config": {"rows": 14, "cols": 14}},
            {"visual_type": "question", "primary_text": "What's next?", "color": "accent"},
        ]

        visuals = []
        for i, beat in enumerate(beats_with_captions):
            visuals.append(mock_visuals[i % len(mock_visuals)])

        return visuals

    def _match_beat_to_source_scene(
        self,
        caption_text: str,
        source_script: Script,
        selected_scene_ids: list[str],
    ) -> tuple[str, list[str], str]:
        """Find source scene that best matches beat caption.

        Compares the beat's caption text to source scene voiceovers to find
        the best matching scene, then returns its visual_cue description,
        elements, and the scene filename for inspiration.

        Args:
            caption_text: The beat's caption text.
            source_script: The original full video script.
            selected_scene_ids: List of scene IDs used in this short.

        Returns:
            Tuple of (visual_description, visual_elements, scene_filename) from the best matching scene.
        """
        if not source_script or not source_script.scenes:
            return "", [], ""

        # Normalize caption for comparison
        caption_words = set(caption_text.lower().split())

        best_match = None
        best_score = 0

        for scene in source_script.scenes:
            scene_id = f"scene{scene.scene_id}_{scene.scene_type}"

            # Prioritize scenes that were selected for this short
            priority_bonus = 2 if scene_id in selected_scene_ids else 0

            # Calculate word overlap score
            voiceover_words = set(scene.voiceover.lower().split())
            overlap = len(caption_words & voiceover_words)
            score = overlap + priority_bonus

            if score > best_score:
                best_score = score
                best_match = scene

        if best_match and best_score > 0:
            visual_cue = best_match.visual_cue
            # Generate scene filename from title (same logic as full video)
            import re
            words = re.sub(r"[^a-zA-Z0-9\s]", "", best_match.title).split()
            component_name = "".join(word.capitalize() for word in words) + "Scene"
            scene_filename = f"{component_name}.tsx"
            return visual_cue.description, visual_cue.elements, scene_filename

        return "", [], ""

    def generate_shorts_with_custom_scenes(
        self,
        short_script: ShortScript,
        word_timestamps: list,
        voiceover_duration: float,
        source_script: Script,
        scenes_dir: Path,
        project_scenes_dir: Path | None = None,
        selected_scene_ids: list[str] | None = None,
        mock: bool = False,
    ) -> ShortsStoryboard:
        """Generate storyboard with custom scene components for each beat.

        This is the enhanced pipeline that:
        1. Creates storyboard beats from voiceover timing
        2. Matches each beat to source visual descriptions
        3. Generates custom React components for each beat (using full video scenes as inspiration)
        4. Returns storyboard with component_name references

        Args:
            short_script: The short script with narration.
            word_timestamps: Word-level timestamps from voiceover.
            voiceover_duration: Duration of voiceover in seconds.
            source_script: Original full video script with visual_cue data.
            scenes_dir: Directory to write generated scene files for shorts.
            project_scenes_dir: Directory containing full video scene files for inspiration.
            selected_scene_ids: Scene IDs selected for this short.
            mock: Use mock data for testing.

        Returns:
            ShortsStoryboard with beats containing component_name references.
        """
        from .custom_scene_generator import ShortsCustomSceneGenerator

        # Step 1: Create basic storyboard from voiceover timing
        storyboard = self.generate_shorts_storyboard_from_voiceover(
            short_script,
            word_timestamps,
            voiceover_duration,
            mock=mock,
        )

        # Step 2: Match each beat to source visual description and scene file
        scene_ids = selected_scene_ids or []
        for beat in storyboard.beats:
            # Skip CTA beat
            if beat.id == "cta":
                continue

            visual_desc, elements, scene_file = self._match_beat_to_source_scene(
                beat.caption_text,
                source_script,
                scene_ids,
            )
            beat.visual_description = visual_desc
            beat.visual_elements = elements
            beat.source_scene_file = scene_file

        # Step 3: Generate custom scene components
        if not mock:
            scene_gen = ShortsCustomSceneGenerator()
            scene_gen.generate_all_scenes(
                storyboard,
                source_script,
                scenes_dir,
                project_scenes_dir=project_scenes_dir,
                word_timestamps=word_timestamps,
            )

        return storyboard
