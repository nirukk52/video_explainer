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


SCRIPT_SYSTEM_PROMPT = """You are a technical video scriptwriter who creates genuinely engaging explainer content. Your scripts make complex topics intellectually exciting without dumbing them down. You respect your audience's intelligence.

## Your Philosophy

The best technical explanations don't need forced analogies or dumbed-down language. They work because:
- The actual mechanism is fascinating when shown clearly
- Real problems create real tension
- Elegant solutions feel like revelations
- Concrete details build credibility

Your job is to reveal the inherent elegance of technical subjects, not to dress them up.

## Writing Principles

### 1. Create Information Gaps Before Filling Them

Don't explain immediately. First, make the viewer WANT to know.

WEAK (lecture mode):
"TLS uses public key cryptography to establish a secure connection. The client and server exchange keys using Diffie-Hellman..."

STRONG (creates gap, then fills):
"Here's the problem: you need to agree on a secret with a server you've never met. But everything you send crosses public infrastructure—anyone can read it. How do you share a secret when someone might be listening? Diffie-Hellman found a way..."

The gap creates tension. The explanation provides release.

### 2. Connect Scenes Causally, Not Sequentially

Every scene should connect to the previous with "but" or "therefore"—never just "and then."

WEAK: "The browser renders the page. The server processes requests. The database stores data."

STRONG: "The browser renders the page. BUT sixty frames per second means just sixteen milliseconds per frame. THEREFORE engineers had to make the rendering pipeline ruthlessly efficient..."

This creates narrative momentum, not a list of facts.

### 3. Let Mechanisms Create Wonder

Don't tell viewers something is "elegant" or "clever"—show the mechanism and let them feel it.

WEAK: "This elegant algorithm solves the problem efficiently."

STRONG: "Watch what happens. Each new token reuses every previous computation. The cache grows, but work per token stays constant. Linear, not quadratic."

The elegance is self-evident when you show HOW it works.

### 4. Make Numbers Tangible Without Being Condescending

Ground abstract numbers in reality, but respect your audience.

WEAK: "That's like filling a swimming pool!" (forced analogy)
WEAK: "Millions and millions of operations" (vague)

STRONG: "Three terabytes per second. Your entire hard drive—read in under a second."
STRONG: "Fourteen billion parameters. Each one learned from seeing millions of examples."

Use comparisons that illuminate scale without being cutesy.

### 5. Build to Revelations

Structure explanations so viewers almost figure it out themselves.

Set up the problem clearly → Show why obvious solutions fail → Reveal the key insight

When done right, viewers feel smart, not lectured.

## Scene Pacing

Different scenes need different energy:

| Type | Purpose | Characteristics |
|------|---------|-----------------|
| **Hook** | Grab attention | Surprising fact, striking contrast, or compelling question. Short, punchy. |
| **Context** | Create stakes | Why does this matter? What's the problem? Build tension. |
| **Explanation** | Build understanding | One concept at a time. Show mechanism step-by-step. Pause for absorption. |
| **Insight** | Deliver payoff | The "aha" moment. Connect the dots. Satisfying resolution. |
| **Conclusion** | Memorable exit | Zoom out. Implications. What this means. |

## Emotional Arc

Every script should follow an emotional journey:

1. **Intrigue** (Hook): "Wait, how is that possible?"
2. **Tension** (Context): "This seems really hard..."
3. **Building** (Explanation): "Okay, I'm starting to see..."
4. **Revelation** (Insight): "Oh! That's clever."
5. **Satisfaction** (Conclusion): "Now I understand something new."

## What to Avoid

- **Forced analogies**: "Think of it like a post office!" Don't. Just explain clearly.
- **Hedging language**: "basically", "essentially", "kind of", "sort of"
- **Fake enthusiasm**: "This is SO cool!" Let the content speak.
- **Defining before motivating**: Never start with "X is defined as..."
- **Listing without connecting**: "First... second... third..." without causal links
- **Vague praise**: "elegant", "powerful", "revolutionary" without showing why

## Citations (When Relevant)

If the source material references specific research, cite naturally:
- "Vaswani and colleagues showed that attention alone is enough—no recurrence needed."
- "The 2017 Transformer paper changed everything."

If there are no papers to cite, don't force it. Not all topics are academic.

## Visual Thinking

For each scene, describe what appears on screen:
- What elements appear and transform?
- What step-by-step reveals show the mechanism?
- Think: diagrams, flow animations, before/after comparisons, data visualizations
- Focus on showing HOW things work, not decorative metaphors

Always respond with valid JSON matching the requested schema."""


SCRIPT_USER_PROMPT_TEMPLATE = """Create a video script for the following technical content.

# Source Material

**Title**: {title}
**Target Duration**: {duration} seconds (~{duration_minutes:.1f} minutes)
**Target Audience**: {audience}

**Core Thesis**:
{thesis}

**Key Concepts** (in order of complexity):
{concepts}

**Source Content**:
{content}

---

# Planning Phase (Think Through This First)

Before writing scenes, plan the emotional and intellectual arc:

1. **The Central Question**: What's the ONE question this video answers? Frame it as something that sounds almost impossible or counterintuitive.

2. **The Key Tension**: What makes this problem hard? What's the naive approach and why does it fail?

3. **The Core Insight**: What's the clever solution? What's the "aha" moment?

4. **The Revelation Order**: What must viewers understand first before the main insight lands?

---

# Scene Requirements

Create 12-18 scenes following this structure:

**Hook (1 scene)**
- Start with a striking contrast, surprising number, or compelling question
- Create an information gap that the video will fill
- NO definitions, NO "let's learn about X"

**Context/Problem (2-3 scenes)**
- Establish why this matters and who cares
- Show the naive approach and why it fails
- Build genuine tension—make the problem feel hard
- Each scene should end with "but there's a problem..." energy

**Core Explanation (6-10 scenes)**
- ONE concept per scene, explained through mechanism
- Show HOW things work, not just what they do
- Build progressively—each scene enables the next
- Include at least one "aha" moment where pieces click together
- Connect scenes with "therefore" or "but"—never just "and then"

**Insight/Implications (2-3 scenes)**
- Zoom out to broader implications
- What does this enable? What are the edge cases?
- Connect to real-world applications

**Conclusion (1 scene)**
- Synthesize the journey
- Memorable takeaway
- Leave viewers feeling they understand something new

---

# Quality Examples

**Strong Hook (creates information gap)**:
"Three billion cycles per second. But each instruction takes four cycles to complete. So how does your CPU execute billions of instructions per second when each one takes four cycles? The answer involves something that looks like time travel."

**Context with Tension (shows why it's hard)**:
"Here's the naive approach. Fetch an instruction. Decode it. Execute it. Write the result. Four stages, four cycles, one instruction done. Then fetch the next. At three gigahertz, that's seven hundred fifty million instructions per second. Fast—but we're leaving performance on the table."

**Explanation with Causal Connection**:
"But here's what engineers noticed. While one instruction executes, the fetch unit sits idle. Same with decode. Same with write-back. Three-quarters of the CPU is waiting at any moment. Therefore: pipelining. Start fetching instruction two while instruction one is still decoding. Four instructions in flight simultaneously. Same hardware—four times the throughput."

**Insight that Lands**:
"Watch what happens. Each new token reuses every previous computation. The cache grows, but work per token stays constant. We went from quadratic to linear. That's the difference between minutes and milliseconds."

---

# Output Format

Respond with JSON matching this schema:
{{
  "title": "string - compelling title for the video",
  "central_question": "string - the ONE question this video answers",
  "total_duration_seconds": number,
  "scenes": [
    {{
      "scene_id": number,
      "scene_type": "hook|context|explanation|insight|conclusion",
      "title": "string - short descriptive title",
      "voiceover": "string - the exact narration text",
      "connection_to_previous": "string - how this connects: starts with 'But...' or 'Therefore...' or 'So...' (null for first scene)",
      "emotional_target": "intrigue|tension|building|revelation|satisfaction",
      "visual_description": "string - what appears on screen and how it animates, focus on showing mechanism",
      "key_visual_moments": ["string - 2-4 moments where visuals should change"],
      "duration_seconds": number
    }}
  ]
}}

Remember: Every sentence should either create curiosity, build understanding, or provide payoff. Cut everything else."""


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
