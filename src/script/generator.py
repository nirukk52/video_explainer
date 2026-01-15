"""Script generator - creates video scripts from content analysis."""

import re

from ..config import Config, load_config
from ..models import (
    ContentAnalysis,
    ParsedDocument,
    Script,
    ScriptScene,
    VisualCue,
)
from ..understanding.llm_provider import LLMProvider, get_llm_provider


SCRIPT_SYSTEM_PROMPT = """You are an elite technical video scriptwriter who creates viral-quality explainer content. Your scripts make complex topics genuinely exciting while preserving technical accuracy.

## Your Writing Style

**Voice**: Punchy, direct, confident. Short sentences that hit hard. No filler words, no hedging, no "basically" or "essentially." Every word earns its place.

**Tone**: Like a brilliant friend explaining something they're genuinely excited about. Technical but never dry. You respect the audience's intelligence while making complex ideas accessible.

**Structure**: Problem → Tension → Solution → Insight. Build curiosity, create stakes, then deliver satisfying explanations.

## Core Principles

1. **Lead with contrast or surprise**: Start with a striking comparison, counterintuitive fact, or provocative question. Never start with definitions.
   - BAD: "Let's learn about transformers."
   - GOOD: "Forty tokens per second versus three thousand. Same model, same hardware—eighty-seven times faster. The difference? Pure software."

2. **Use concrete numbers**: Specific numbers create credibility and memorability.
   - BAD: "This uses a lot of memory"
   - GOOD: "Fourteen gigabytes. That's what a 7-billion parameter model needs in memory."

3. **Show the problem before the solution**: Create tension. Make the viewer feel the pain of the naive approach before revealing the elegant fix.

4. **Explain through mechanism, not description**: Don't just say what something does—show HOW it works, step by step.
   - BAD: "The KV cache stores previous computations."
   - GOOD: "Token one generates Key-one and Value-one. These go straight into the cache. Token two arrives—it generates its own Key and Value, but for attention, it reuses Key-one and Value-one from the cache. No recalculation."

5. **End scenes with forward momentum**: Each scene should create anticipation for the next. Use phrases like "But there's a problem..." or "Here's where it gets interesting..."

## CRITICAL: Citation Requirements (MANDATORY)

Every technical concept MUST include a citation in the narration. Cite papers naturally by mentioning author names:

**DO** (natural citations):
- "as introduced by Dosovitskiy and colleagues in 2021"
- "building on the work of Vaswani et al."
- "using the architecture from the original Transformer paper"
- "as shown in the MAE paper by He and colleagues"
- "introduced in the ViViT paper by Arnab and colleagues in 2021"

**DON'T** (unnatural citations):
- "according to ViT dash Dosovitskiy et al. comma ICLR 2021"
- Reading citation format verbatim
- Skipping citations entirely

Key papers to cite (when relevant):
- Vision Transformer (ViT): Dosovitskiy et al., 2021
- Attention/Transformer: Vaswani et al., 2017
- CLIP: Radford et al., OpenAI 2021
- MAE (Masked Autoencoders): He et al., 2022
- ViViT (Video Vision Transformer): Arnab et al., 2021
- TimeSformer: Bertasius et al., 2021
- LLaVA: Liu et al., 2023
- ResNet: He et al., 2016

## Narration Guidelines

- Write for spoken delivery: read it aloud, ensure natural rhythm
- Vary sentence length: short punchy sentences mixed with longer explanatory ones
- Use rhetorical questions to create engagement
- Pause points: use periods strategically for dramatic effect
- Include natural paper citations when introducing technical concepts

### Word Count Guidelines by Scene Type (FOLLOW STRICTLY)

Different scene types need different pacing for optimal visual matching:

| Scene Type | Words | Duration | Pacing |
|------------|-------|----------|--------|
| **Hook** | 30-50 words | 10-20s | Punchy, fast. Grab attention immediately. |
| **Context** | 50-70 words | 20-30s | Build tension. Show the problem. |
| **Explanation** | 60-80 words | 25-35s | Clear, methodical. One concept at a time. |
| **Insight** | 40-60 words | 15-25s | Emphasis on the key revelation. |
| **Conclusion** | 30-50 words | 10-20s | Memorable takeaway. End strong. |

**WHY THIS MATTERS**: Shorter narrations (30-50 words) work better for hooks and conclusions because they need quick, impactful visuals. Longer narrations work for explanations where we can show step-by-step animations.

### Visual Beats (REQUIRED)

For each scene, identify 2-4 "visual beats" - moments where a new visual element should appear. Structure your narration with natural pauses between these beats.

**Example for an explanation scene (4 visual beats)**:
"[BEAT 1: Show token grid] Each token produces Query, Key, and Value vectors. [BEAT 2: Highlight Q,K,V] The attention mechanism multiplies Query by Key-transpose. [BEAT 3: Show attention matrix] Then softmax normalizes the scores. [BEAT 4: Show final output] Finally, we compute a weighted sum of Values."

Mark visual beats in your mind when writing - the narration should have natural breath points where visuals can transition.

## Visual Thinking

For each scene, imagine the perfect animation:
- What elements appear on screen?
- What transforms, moves, or highlights?
- What visual metaphor makes the concept click?
- Think in terms of: tokens, arrows, grids, comparisons, before/after, step-by-step reveals
- Include paper citations as visual overlays in bottom-right corner

Always respond with valid JSON matching the requested schema."""


SCRIPT_USER_PROMPT_TEMPLATE = """Create a video script for the following technical content.

# Source Material

**Title**: {title}
**Target Duration**: {duration} seconds (~{duration_minutes:.1f} minutes)
**Target Audience**: {audience}

**Core Thesis**:
{thesis}

**Key Concepts** (in order of importance):
{concepts}

**Source Content**:
{content}

---

# Your Task

Create an engaging, technically accurate video script with 12-18 scenes. The script should:

1. **Hook (1 scene, ~15-20s)**: Open with a striking contrast, surprising statistic, or provocative question. Create immediate curiosity.

2. **Context/Problem (2-3 scenes, ~40-60s)**: Establish why this matters. Show the naive approach and its problems. Build tension.

3. **Core Explanation (6-10 scenes, ~3-5 min)**: Break down the key concepts. Each scene should explain ONE idea clearly with a memorable visualization. Build concepts progressively—each scene should set up the next.

4. **Advanced Insights (2-3 scenes, ~40-60s)**: Deeper implications, edge cases, or advanced applications.

5. **Conclusion (1 scene, ~20-30s)**: Synthesize everything. End with a memorable takeaway or forward-looking statement.

---

# Quality Examples

Here are examples of excellent narration style to emulate:

**Strong Hook**:
"Forty tokens per second. That's what you get with naive inference. The best production systems? Over three thousand. Same model, same hardware—eighty-seven times faster. The difference is purely software. Here's how they do it."

**Clear Technical Explanation**:
"Quick attention refresher. Each token produces Query, Key, and Value vectors. To predict the next token, we compute attention: Q times K-transpose, scaled, then softmax, then weighted sum of Values. Here's the key insight: Keys and Values for past tokens never change. So why recompute them every time?"

**Problem Setup with Tension**:
"Here's the first problem with naive decoding. For each new token, we recompute Keys and Values for ALL previous tokens. Token one? Compute once. Token two? Compute everything twice. Token one hundred? One hundred times the work. This is O of n squared complexity. Most of this computation is completely redundant."

**Satisfying Solution Reveal**:
"Watch what happens with the KV cache. Token one generates Key-one and Value-one. These go straight into the cache. Now token two arrives. It generates Key-two and Value-two, but for attention, it reuses Key-one and Value-one from the cache. No recalculation. Each token adds one new pair. The cache grows, but the work per token stays constant."

---

# Output Format

Respond with JSON matching this schema:
{{
  "title": "string - compelling title for the video",
  "total_duration_seconds": number,
  "scenes": [
    {{
      "scene_id": "string - format: scene1_hook, scene2_context, etc.",
      "scene_type": "hook|context|explanation|insight|conclusion",
      "title": "string - short descriptive title",
      "voiceover": "string - the exact narration text (follow word count guidelines!)",
      "word_count": number - count of words in voiceover (hook: 30-50, context: 50-70, explanation: 60-80, insight: 40-60, conclusion: 30-50),
      "visual_description": "string - detailed description of what appears on screen and how it animates",
      "visual_beats": ["string - list of 2-4 key visual moments with descriptions"],
      "key_elements": ["string - list of visual elements to animate"],
      "duration_seconds": number,
      "builds_to": "string - what concept or scene this sets up (optional)"
    }}
  ]
}}

Remember: Every sentence should either teach something, create curiosity, or move the narrative forward. Cut everything else."""


class ScriptGenerator:
    """Generates video scripts from content analysis."""

    def __init__(self, config: Config | None = None, llm: LLMProvider | None = None):
        """Initialize the generator.

        Args:
            config: Configuration object. If None, loads default.
            llm: LLM provider. If None, creates one from config.
        """
        self.config = config or load_config()
        self.llm = llm or get_llm_provider(self.config)

    def generate(
        self,
        document: ParsedDocument,
        analysis: ContentAnalysis,
        target_duration: int | None = None,
    ) -> Script:
        """Generate a video script from analyzed content.

        Args:
            document: The parsed source document
            analysis: Content analysis with key concepts
            target_duration: Target duration in seconds (uses analysis suggestion if None)

        Returns:
            Script with scenes and visual cues
        """
        duration = target_duration or analysis.suggested_duration_seconds

        # Format concepts for the prompt - richer format
        concepts_text = "\n".join(
            f"{i+1}. **{c.name}** (complexity: {c.complexity}/10, visual potential: {c.visual_potential})\n"
            f"   {c.explanation}\n"
            f"   Analogies: {', '.join(c.analogies) if c.analogies else 'None provided'}"
            for i, c in enumerate(analysis.key_concepts)
        )

        # Get content from document - include more content for context
        content_parts = []
        for section in document.sections[:15]:  # Include more sections
            content_parts.append(f"## {section.heading}\n{section.content[:2000]}")
        content_text = "\n\n".join(content_parts)

        # Build the prompt
        prompt = SCRIPT_USER_PROMPT_TEMPLATE.format(
            title=document.title,
            duration=duration,
            duration_minutes=duration / 60,
            audience=analysis.target_audience,
            thesis=analysis.core_thesis,
            concepts=concepts_text,
            content=content_text[:30000],  # Allow more content for richer scripts
        )

        # Generate script via LLM
        result = self.llm.generate_json(prompt, SCRIPT_SYSTEM_PROMPT)

        # Parse into Script model
        return self._parse_script_result(result, document.source_path)

    def _parse_script_result(self, result: dict, source_path: str) -> Script:
        """Parse LLM result into a Script model."""
        scenes = []
        for idx, s in enumerate(result.get("scenes", [])):
            # Handle both old format (visual_cue) and new format (visual_description + key_elements)
            if "visual_cue" in s:
                visual_cue_data = s.get("visual_cue", {})
                visual_cue = VisualCue(
                    description=visual_cue_data.get("description", ""),
                    visual_type=visual_cue_data.get("visual_type", "animation"),
                    elements=visual_cue_data.get("elements", []),
                    duration_seconds=visual_cue_data.get(
                        "duration_seconds", s.get("duration_seconds", 10.0)
                    ),
                )
            else:
                # New format
                visual_cue = VisualCue(
                    description=s.get("visual_description", ""),
                    visual_type="animation",  # Default for new format
                    elements=s.get("key_elements", []),
                    duration_seconds=s.get("duration_seconds", 10.0),
                )

            # Handle scene_id as string (new format) or int (old format)
            scene_id = s.get("scene_id", idx + 1)
            if isinstance(scene_id, str):
                # Extract number from string like "scene1_hook"
                match = re.search(r'\d+', scene_id)
                scene_id_num = int(match.group()) if match else idx + 1
            else:
                scene_id_num = scene_id

            # Combine notes and builds_to for notes field
            notes = s.get("notes", "")
            if s.get("builds_to"):
                notes = f"{notes} Builds to: {s['builds_to']}".strip()

            scene = ScriptScene(
                scene_id=scene_id_num,
                scene_type=s.get("scene_type", "explanation"),
                title=s.get("title", ""),
                voiceover=s.get("voiceover", ""),
                visual_cue=visual_cue,
                duration_seconds=s.get("duration_seconds", 10.0),
                notes=notes,
            )
            scenes.append(scene)

        total_duration = sum(s.duration_seconds for s in scenes)

        return Script(
            title=result.get("title", "Untitled"),
            total_duration_seconds=total_duration,
            scenes=scenes,
            source_document=source_path,
        )

    def format_script_for_review(self, script: Script) -> str:
        """Format a script for human review.

        Args:
            script: The script to format

        Returns:
            Formatted string representation suitable for review
        """
        lines = [
            f"# {script.title}",
            f"",
            f"**Total Duration**: {script.total_duration_seconds:.0f} seconds "
            f"({script.total_duration_seconds / 60:.1f} minutes)",
            f"**Source**: {script.source_document}",
            f"**Scenes**: {len(script.scenes)}",
            "",
            "---",
            "",
        ]

        for scene in script.scenes:
            timestamp = sum(
                s.duration_seconds
                for s in script.scenes
                if s.scene_id < scene.scene_id
            )
            minutes = int(timestamp // 60)
            seconds = int(timestamp % 60)

            lines.extend([
                f"## Scene {scene.scene_id}: {scene.title}",
                f"**Type**: {scene.scene_type} | **Duration**: {scene.duration_seconds:.0f}s | "
                f"**Timestamp**: {minutes:02d}:{seconds:02d}",
                "",
                "### Voiceover",
                f"> {scene.voiceover}",
                "",
                "### Visual",
                f"**Type**: {scene.visual_cue.visual_type}",
                f"**Description**: {scene.visual_cue.description}",
                "",
                f"**Elements**: {', '.join(scene.visual_cue.elements) if scene.visual_cue.elements else 'None specified'}",
                "",
            ])

            if scene.notes:
                lines.extend([
                    f"**Notes**: {scene.notes}",
                    "",
                ])

            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    def save_script(self, script: Script, path: str) -> None:
        """Save a script to a file.

        Args:
            script: The script to save
            path: Path to save the script
        """
        import json
        from pathlib import Path

        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Save as JSON for machine processing
        with open(output_path, "w") as f:
            json.dump(script.model_dump(), f, indent=2)

        # Also save human-readable version
        readable_path = output_path.with_suffix(".md")
        with open(readable_path, "w") as f:
            f.write(self.format_script_for_review(script))

    @staticmethod
    def load_script(path: str) -> Script:
        """Load a script from a file.

        Args:
            path: Path to the script file

        Returns:
            Loaded Script object
        """
        import json
        from pathlib import Path

        with open(Path(path)) as f:
            data = json.load(f)

        return Script(**data)
