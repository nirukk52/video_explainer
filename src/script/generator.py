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


SCRIPT_SYSTEM_PROMPT = """You are creating a technical explainer video script. Your sole objective is to make every concept in the source material deeply understandable to a technical audience.

## Your Only Goal

Make the audience truly understand the concepts. Everything else—structure, length, pacing—serves this goal. A technical viewer watching your video should walk away with genuine understanding, not just familiarity.

## What "Understanding" Means

Understanding is NOT:
- Hearing that something exists
- Knowing the name of a technique
- A surface-level summary

Understanding IS:
- Knowing WHY a problem is hard
- Seeing HOW a mechanism works, step by step
- Grasping the intuition behind formulas
- Recognizing the trade-offs and design decisions
- Being able to explain it to someone else

## Core Principles

### 1. Respect Concept Dependencies

Concepts build on each other. If concept B requires understanding concept A, you MUST explain A first and explain it well.

Example from reinforcement learning:
- Advantage functions require understanding value functions
- Value functions require understanding expected reward
- PPO requires understanding why vanilla policy gradients are unstable

Map these dependencies. Never reference something you haven't explained.

### 2. Explain Mechanisms, Not Just Outcomes

Don't just say what something does—show HOW it works.

SHALLOW: "PPO uses clipping to stabilize training."

DEEP: "Here's the problem: a single bad gradient update can collapse your policy, and you might never recover. PPO's solution is elegant. It computes a ratio between the new and old policy probabilities. If this ratio tries to go above 1.2 or below 0.8, the objective stops growing—there's no incentive to push further. This implicitly constrains how far the policy can drift in one update."

### 3. Make Math Intuitive, Not Just Labeled

Math in papers is often intimidating. Your job is to make it intuitive.

DON'T just label terms:
"A(s,a) = Q(s,a) - V(s), where Q is the action-value function and V is the state-value function."
(This is useless—you've just replaced symbols with jargon.)

DO build intuition step by step:
"You're in a situation. Some actions are better than others. Q asks: if I take THIS specific action, how well will things go? V asks: on average, across all actions I might take, how well will things go? The advantage A is the difference—it tells you: is this action better or worse than my average option? Positive means better, negative means worse."

The goal: a viewer who's never seen this formula should understand what it MEANS, not just what the symbols stand for.

When including formulas:
- Build intuition BEFORE showing the formula
- Explain WHY each term matters, not just what it's called
- Use concrete examples when possible
- Don't include formulas that don't aid understanding

### 4. Create Information Gaps Before Filling Them

Make viewers WANT to know before you explain.

WEAK: "TLS uses Diffie-Hellman for key exchange."

STRONG: "You need to agree on a secret with a server you've never met. But everything you send crosses public networks—anyone could be listening. How do you share a secret in public? This seems impossible..."

Then explain the solution. The gap creates tension; the explanation provides release.

### 5. Connect Causally, Not Sequentially

Every scene should connect with "but" or "therefore"—never just "and then."

WEAK: "Next, we'll discuss value functions."

STRONG: "But there's a problem with REINFORCE: high variance. Every trajectory gives wildly different rewards, so gradient estimates fluctuate dramatically. Therefore, we need a way to center the learning signal..."

### 6. Go Deep on Core Concepts

If a concept is central to understanding the topic, give it the time it deserves. Don't compress important ideas into a single rushed scene. If PPO is important, it might need multiple scenes: one for the problem, one for the mechanism, one for why it works.

## Audience Calibration

Your audience is technically literate but not specialists:
- They can follow logical reasoning and code
- They have basic ML familiarity (gradients, training loops, loss functions)
- They find most math in ML papers intimidating and hard to follow
- They DON'T know the specific domain you're explaining

Treat them as smart but unfamiliar. Build from foundations. Make math intuitive—don't assume they can parse formulas easily.

## Citations

When the source material references research papers, cite them naturally in the narration:
- "Vaswani and colleagues showed that attention alone is enough—no recurrence needed."
- "The 2017 Transformer paper introduced the architecture that would change everything."
- "As demonstrated in the PPO paper by Schulman et al..."

Good citations:
- Flow naturally in speech
- Give credit where concepts originated
- Help viewers find the original work

Bad citations:
- Reading citation format verbatim: "ViT dash Dosovitskiy et al. comma ICLR 2021"
- Interrupting the flow of explanation
- Citing every minor detail

If the source material has no papers to cite, don't force it.

## What to Avoid

- **Skipping foundational concepts**: If something is needed to understand what follows, explain it
- **Rushed explanations**: If a concept is important, give it proper time
- **Vague descriptions**: "The algorithm is efficient" → Show WHY it's efficient
- **Forced analogies**: Don't say "it's like a post office"—just explain the mechanism
- **Hedging language**: Avoid "basically", "essentially", "sort of"
- **Praising without showing**: Don't say "elegant" or "clever"—show the mechanism and let viewers feel it

## Visual Descriptions

For each scene, describe visuals that illuminate the specific mechanism being explained. These should be:
- Derived from what the narration is saying
- Specific to THIS concept, not generic animations
- Focused on showing HOW things work step by step
- Detailed enough that an animator could implement them

Think carefully about what visual would actually help understanding. A visualization of policy gradient updates should show the probability distribution shifting based on rewards—not just generic boxes with arrows.

Always respond with valid JSON matching the requested schema."""


SCRIPT_USER_PROMPT_TEMPLATE = """Create a video script that makes the following technical content deeply understandable.

# Source Material

**Title**: {title}
**Target Duration**: Around {duration_minutes:.0f} minutes (soft constraint—go longer if needed for understanding)
**Target Audience**: {audience}

**Core Thesis**:
{thesis}

**Key Concepts Identified**:
{concepts}

**Full Source Content**:
{content}

---

# Your Task

Think carefully about this source material. Your job is to create a script that gives viewers genuine understanding of these concepts.

## Step 1: Analyze the Source Material

Before writing anything, think through:

1. **What are the core concepts?** List every important idea that needs to be explained.

2. **What are the dependencies?** Which concepts require understanding other concepts first? Map this out.

3. **What makes each concept hard to understand?** Identify the specific confusion points.

4. **What would make each concept click?** What explanation, example, or visualization would create the "aha" moment?

5. **What's the central question?** Frame the video around ONE compelling question that seems hard or counterintuitive.

## Step 2: Plan the Concept Sequence

Arrange concepts so that:
- Foundational concepts come before concepts that depend on them
- Each scene builds on what came before
- The hardest/most important concepts get the most time
- Nothing is referenced before it's explained

## Step 3: Write Each Scene

For each scene:
- Focus on ONE concept or one aspect of a concept
- Explain the mechanism, not just the outcome
- If there's a formula, explain what each term means
- Create an information gap before filling it
- Connect causally to previous scene ("But..." or "Therefore...")

For visual descriptions:
- Describe visuals that illuminate THIS specific concept
- Show the mechanism step by step
- Be specific enough that an animator could implement it
- Avoid generic animations—each visual should be tailored to what's being explained

## Step 3: Verify Coverage

Before finalizing, check:
- Have you covered all the core concepts from the source material?
- Have you explained the dependencies before concepts that need them?
- Would a technical viewer actually understand each concept, not just hear about it?
- Are the visual descriptions specific to each concept, not generic?

---

# Output Format

Respond with JSON matching this schema:
{{
  "title": "string - compelling title for the video",
  "central_question": "string - the ONE question this video answers",
  "concept_map": {{
    "core_concepts": ["string - list of core concepts covered"],
    "dependencies": ["string - concept A requires concept B, etc."]
  }},
  "total_duration_seconds": number,
  "scenes": [
    {{
      "scene_id": number,
      "scene_type": "hook|context|explanation|insight|conclusion",
      "title": "string - descriptive title",
      "concept_covered": "string - which concept from source this scene explains (null for hook/conclusion)",
      "voiceover": "string - the exact narration text",
      "connection_to_previous": "string - how this connects (But.../Therefore.../So...) - null for first scene",
      "visual_description": "string - detailed description of visuals specific to this concept",
      "key_visual_moments": ["string - specific moments where visuals change, tied to narration"],
      "duration_seconds": number
    }}
  ]
}}

Take your time. Think through the concepts carefully. The goal is genuine understanding, not just coverage."""


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

        # Format concepts for the prompt - focus on the concept itself
        concepts_text = "\n".join(
            f"{i+1}. **{c.name}**\n"
            f"   {c.explanation}\n"
            f"   Prerequisites: {', '.join(c.prerequisites) if c.prerequisites else 'None'}"
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
            duration_minutes=duration / 60,
            audience=analysis.target_audience,
            thesis=analysis.core_thesis,
            concepts=concepts_text,
            content=content_text[:50000],  # Include more content for thorough understanding
        )

        # Generate script via LLM
        result = self.llm.generate_json(prompt, SCRIPT_SYSTEM_PROMPT)

        # Parse into Script model
        return self._parse_script_result(result, document.source_path)

    def _parse_script_result(self, result: dict, source_path: str) -> Script:
        """Parse LLM result into a Script model."""
        scenes = []
        for idx, s in enumerate(result.get("scenes", [])):
            # Handle multiple formats for visual information
            if "visual_cue" in s:
                # Old format with nested visual_cue object
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
                # New format with flat visual_description and key_visual_moments
                visual_cue = VisualCue(
                    description=s.get("visual_description", ""),
                    visual_type="animation",
                    elements=s.get("key_visual_moments", s.get("key_elements", [])),
                    duration_seconds=s.get("duration_seconds", 10.0),
                )

            # Handle scene_id as string or int
            scene_id = s.get("scene_id", idx + 1)
            if isinstance(scene_id, str):
                match = re.search(r'\d+', scene_id)
                scene_id_num = int(match.group()) if match else idx + 1
            else:
                scene_id_num = scene_id

            # Build notes from various fields
            notes_parts = []
            if s.get("concept_covered"):
                notes_parts.append(f"Concept: {s['concept_covered']}")
            if s.get("connection_to_previous"):
                notes_parts.append(f"Connection: {s['connection_to_previous']}")
            if s.get("emotional_target"):
                notes_parts.append(f"Emotion: {s['emotional_target']}")
            if s.get("builds_to"):
                notes_parts.append(f"Builds to: {s['builds_to']}")
            if s.get("notes"):
                notes_parts.append(s["notes"])
            notes = " | ".join(notes_parts)

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

        # Store central_question in metadata if present
        metadata = {}
        if result.get("central_question"):
            metadata["central_question"] = result["central_question"]

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

            # Word count for reference
            word_count = len(scene.voiceover.split())

            lines.extend([
                f"## Scene {scene.scene_id}: {scene.title}",
                f"**Type**: {scene.scene_type} | **Duration**: {scene.duration_seconds:.0f}s | "
                f"**Words**: {word_count} | **Timestamp**: {minutes:02d}:{seconds:02d}",
                "",
            ])

            # Show connection and emotional target from notes if present
            if scene.notes:
                notes_display = scene.notes.replace(" | ", "\n- ")
                if notes_display:
                    lines.extend([
                        f"**Arc**: {notes_display}",
                        "",
                    ])

            lines.extend([
                "### Voiceover",
                f"> {scene.voiceover}",
                "",
                "### Visual",
                f"{scene.visual_cue.description}",
                "",
            ])

            if scene.visual_cue.elements:
                lines.extend([
                    f"**Key Moments**: {' → '.join(scene.visual_cue.elements)}",
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
