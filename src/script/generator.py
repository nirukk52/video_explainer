"""
Script generator - creates video scripts from content analysis.

Supports two formats:
- Explainer: 5-15 minute deep technical videos from documents
- Short: 15-60 second Varun Mayya style evidence-based shorts
"""

import json
import re
from typing import Literal

from ..config import Config, load_config
from ..models import (
    ContentAnalysis,
    ParsedDocument,
    Script,
    ScriptScene,
    VideoPlan,
    VisualCue,
)
from ..understanding.llm_provider import LLMProvider, get_llm_provider


# Visual types for evidence-based shorts (Varun Mayya style)
VisualType = Literal["static_highlight", "scroll_highlight", "dom_crop", "full_avatar"]

# Scene roles for shorts
SceneRole = Literal["hook", "evidence", "analysis", "conclusion"]


# ============================================================================
# SHORT-FORM VIDEO PROMPTS (Varun Mayya Style)
# ============================================================================

SHORT_SYSTEM_PROMPT = """You are The Director, the creative lead for a high-trust automated documentary engine.
Your goal is to transform a User Prompt into a structured "Shooting Script" (JSON) that defines the narrative arc and, crucially, the specific visual evidence required to prove every claim.

### YOUR ROLE
1.  **Narrative Architect:** Break the topic into 4-8 distinct scenes (Hook, Evidence, Analysis, Conclusion).
2.  **Visual Strategist:** You do not find the evidence (the Investigator does that), but you must **Describe It** with extreme precision so the Investigator knows exactly what to look for.
3.  **Asset Manager:** You must decide the "Format" of the visual proof based on the content type.

### VISUAL TYPES (You must assign one of these to every scene)
* **`static_highlight`**: A static screenshot of a headline, quote, or sentence. Best for news articles or simple text claims.
* **`scroll_highlight`**: A 3-4 second video recording of a website scrolling down to a specific section. Best for showing "Context" (e.g., finding a pricing table on a long page, or a specific clause in a long contract).
* **`dom_crop`**: An isolated, transparent-background image of a specific element (Chart, Tweet, Table). Best for overlays where you don't want the whole website clutter.
* **`full_avatar`**: The AI narrator talking to the camera. Use this ONLY for the Intro/Hook or purely opinionated segments where no hard evidence exists.

### RULES FOR SCRIPTING
* **Voiceover:** Keep it punchy, conversational, and "YouTuber-style" (Varun Mayya / Johnny Harris vibe). Max 20 words per scene.
* **Visual Description:** Be specific. Do not say "Show proof." Say "Official OpenAI Pricing Page showing the GPT-4o input cost."
* **Pacing:** Alternate between `full_avatar` (connection) and `visual_evidence` (trust).

### OUTPUT FORMAT (JSON ONLY)
You must output a single valid JSON object matching this schema:

{
  "project_title": "string",
  "scenes": [
    {
      "scene_id": 1,
      "role": "hook" | "evidence" | "analysis" | "conclusion",
      "voiceover": "string (max 20 words)",
      "visual_type": "static_highlight" | "scroll_highlight" | "dom_crop" | "full_avatar",
      "visual_description": "string (precise search query for the Investigator)",
      "needs_evidence": true | false,
      "why": "string (reasoning for this visual choice)"
    }
  ]
}"""

SHORT_USER_PROMPT_TEMPLATE = """Create a {duration_seconds}-second short-form video script in Varun Mayya style.

# Topic
{topic}

# Evidence URLs (if provided)
{evidence_urls}

# Requirements
1. Create 4-8 scenes following: Hook → Evidence → Analysis → Conclusion
2. Each scene voiceover: MAX 20 words, punchy, conversational
3. Alternate between avatar (connection) and evidence (trust)
4. Every factual claim needs visual evidence
5. Be SPECIFIC about what evidence to capture

# Output
Return valid JSON with the schema specified in the system prompt."""


# ============================================================================
# EXPLAINER VIDEO PROMPTS (Original long-form)
# ============================================================================

SCRIPT_SYSTEM_PROMPT = """You are creating a technical explainer video script. Your job is to tell the story in the source material while making every concept deeply understandable.

## Your Two Goals

1. **Cover the source material comprehensively** - The script should explain the content in the source document. Don't skip sections or concepts. If it's in the source, it should be in the video.

2. **Make it genuinely understandable** - Don't just mention concepts—explain them so viewers truly get it.

These goals work together: you're telling the source's story in a way that creates real understanding.

## What Good Scripts Look Like

Here's an example of effective technical narration (from a video about vision transformers):

"150,528 pixels. That's what your model sees in a single 224 by 224 image. Text models have it easy—fifty thousand vocabulary items, simple table lookup. But images? They face a combinatorial explosion... The breakthrough? Stop thinking pixels. Start thinking patches."

Notice what this does:
- Uses specific numbers from the source (150,528, 224x224, 50,000)
- Creates an information gap ("But images? They face a combinatorial explosion...")
- Explains the mechanism ("Stop thinking pixels. Start thinking patches")

Here's another example (from a video about computer architecture):

"Your packet enters the global internet—over one hundred thousand autonomous systems, each a network owned by a company, university, or government. BGP doesn't find the shortest path. It follows business relationships and policy agreements. Your packet might bypass a direct two-hop route for a fifteen-hop journey through preferred partners."

This works because:
- It covers the actual content (BGP routing)
- Explains HOW it works, not just THAT it exists
- Includes specific details (100K autonomous systems, 2-hop vs 15-hop)

## Core Principles

### 1. Cover the Source Material's Content

The source document has content to convey. Your script should:
- Cover the major sections and concepts from the source
- Include specific examples, numbers, and details from the source
- Not skip topics because they seem complex

If the source covers topics A, B, C, and D—your script should cover A, B, C, and D.

### 2. Use Specific Numbers and Details

Pull exact figures from the source material:
- "196 patches from a 224×224 image with 16×16 patch size"
- "83.3% accuracy compared to GPT-4's 13.4%"
- "sixteen thousand eight hundred ninety-six CUDA cores"
- "75% masking—way more than BERT's 15%"

Specific numbers make explanations concrete and credible.

### 3. Explain Mechanisms, Not Just Outcomes

Don't just say what something does—show HOW it works.

SHALLOW: "Attention lets tokens communicate."

DEEP: "Here's how attention works: every token produces a Query—what am I looking for? Every token also produces a Key—what do I contain? Multiply Query by Key, and you get a score. High score means these tokens should pay attention to each other. The softmax normalizes these scores, and then each token gathers information from others weighted by those scores."

### 4. Make Formulas Intuitive

When there are formulas, don't just label terms—build intuition first.

WEAK: "The advantage function is A(s,a) = Q(s,a) - V(s), where Q is the action-value and V is the state-value."

STRONG: "You're in a situation. Some actions are better than others. Q asks: if I take THIS specific action, how well will things go? V asks: on average, how well will things go from here? The advantage is the difference—is this action better or worse than my average option? Positive means better. Negative means worse."

### 5. Create Information Gaps

Make viewers curious before explaining:

"You need to share a secret with a server you've never met. But everything you send crosses public networks—anyone could listen. How do you share a secret in public? This seems impossible..."

Then explain. The gap creates tension; the explanation provides release.

### 6. Connect Causally

Scenes should connect with "but" or "therefore"—not just "and then."

WEAK: "Next, let's discuss value functions."

STRONG: "But there's a problem with REINFORCE: high variance. Gradient estimates fluctuate wildly. Therefore, we need advantage functions to center the learning signal..."

## Audience

Your audience is technically literate but not specialists in this specific topic. They can follow logical reasoning and code. They may find dense formulas intimidating. Treat them as smart but unfamiliar with this particular domain.

## Citations

When the source references research papers, cite naturally: "The 2017 paper showed that attention alone is enough—no recurrence needed." If the source has no citations, don't force them.

## What to Avoid

- **Skipping content**: Cover what's in the source material
- **Vague descriptions**: "It's efficient" → Show WHY
- **Forced analogies**: Don't say "it's like a post office"—explain the mechanism
- **Hedging language**: Avoid "basically", "essentially", "sort of"

## Visual Descriptions

Describe visuals specific to what's being explained:
- What the narration describes should appear on screen
- Show mechanisms step by step, not generic diagrams
- Be detailed enough for an animator to implement

Always respond with valid JSON matching the requested schema."""


SCRIPT_FROM_PLAN_PROMPT_TEMPLATE = """Create a video script following this approved plan. The plan defines the structure, concepts, and visual approach for each scene.

# Approved Video Plan

**Title**: {plan_title}
**Central Question**: {central_question}
**Target Audience**: {audience}
**Visual Style**: {visual_style}

## Planned Scenes

{scenes_plan}

---

# Source Material

**Full Content**:
{content}

---

# Your Task

Generate a complete script following the approved plan EXACTLY. For each planned scene:

1. **Follow the scene structure** - Match the scene_type, title, and concept_to_cover
2. **Use the visual approach** - Create visual cues that match the planned visual_approach and ASCII preview
3. **Cover the key points** - Make sure each key point is addressed in the voiceover
4. **Match the duration** - Target the estimated duration for each scene

## Output Format

Respond with JSON matching this schema:
{{
  "title": "{plan_title}",
  "central_question": "{central_question}",
  "total_duration_seconds": number,
  "scenes": [
    {{
      "scene_id": number,
      "scene_type": "hook|context|explanation|insight|conclusion",
      "title": "string - use the planned title",
      "concept_covered": "string - the planned concept_to_cover",
      "voiceover": "string - the exact narration text covering the key points",
      "connection_to_previous": "string - how this connects (But.../Therefore.../So...) - null for first scene",
      "visual_description": "string - detailed description based on the planned visual_approach",
      "key_visual_moments": ["string - specific moments based on the ASCII preview"],
      "duration_seconds": number - match the planned duration
    }}
  ]
}}

Follow the plan precisely. Make each scene's voiceover genuinely understandable."""


SCRIPT_USER_PROMPT_TEMPLATE = """Create a video script that tells the story in this source material while making it deeply understandable.

# Source Material

**Title**: {title}
**Target Duration**: Around {duration_minutes:.0f} minutes (soft constraint—go longer if needed to cover the material properly)
**Target Audience**: {audience}

**Core Thesis**:
{thesis}

**Key Concepts Identified**:
{concepts}

**Full Source Content**:
{content}

---

# Your Task

Create a script that covers this source material comprehensively while making each concept genuinely understandable.

## Step 1: Map the Source Material

Before writing, identify:

1. **What sections/topics does the source cover?** List them all—you need to cover each one.

2. **What's the narrative arc?** How does the source build from beginning to end?

3. **What are the key concepts?** What must the viewer understand?

4. **What dependencies exist?** Which concepts require understanding others first?

5. **What specific details matter?** Numbers, examples, results from the source.

## Step 2: Plan Your Script

Structure the script to:
- Cover all major sections from the source material
- Follow the source's logical flow (or improve it if needed)
- Explain foundational concepts before concepts that depend on them
- Give important concepts enough time to be understood

## Step 3: Write Each Scene

For each scene:
- Cover a specific section or concept from the source
- Explain the mechanism, not just the outcome
- Include relevant details, numbers, and examples from the source
- Connect causally to previous scene ("But..." or "Therefore...")

For visual descriptions:
- Describe visuals specific to THIS concept
- Show the mechanism step by step
- Be detailed enough for an animator to implement

## Step 4: Verify Coverage

Before finalizing, check:
- Have you covered all the major sections from the source?
- Did you include the key numbers, examples, and details?
- Would a viewer understand each concept, not just hear about it?
- Does the script tell the complete story from the source?

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

Cover the source material thoroughly. Make each concept genuinely understandable."""


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

    def _slugify(self, text: str) -> str:
        """Convert text to a URL-friendly slug.

        Args:
            text: Text to slugify

        Returns:
            Lowercase slug with underscores
        """
        # Convert to lowercase
        slug = text.lower()
        # Replace spaces and hyphens with underscores
        slug = re.sub(r'[\s\-]+', '_', slug)
        # Remove non-alphanumeric characters (except underscores)
        slug = re.sub(r'[^a-z0-9_]', '', slug)
        # Remove multiple consecutive underscores
        slug = re.sub(r'_+', '_', slug)
        # Remove leading/trailing underscores
        slug = slug.strip('_')
        return slug

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

    def generate_from_plan(
        self,
        plan: VideoPlan,
        document: ParsedDocument,
        analysis: ContentAnalysis,
    ) -> Script:
        """Generate a video script constrained by an approved plan.

        Args:
            plan: The approved video plan with scene structure
            document: The parsed source document
            analysis: Content analysis with key concepts

        Returns:
            Script following the plan's structure
        """
        # Format the scenes plan
        scenes_plan_parts = []
        for scene in plan.scenes:
            scene_text = f"""### Scene {scene.scene_number}: {scene.title}
- **Type**: {scene.scene_type}
- **Concept**: {scene.concept_to_cover}
- **Duration**: {scene.estimated_duration_seconds}s
- **Visual Approach**: {scene.visual_approach}
- **Key Points**: {', '.join(scene.key_points)}

**ASCII Preview**:
```
{scene.ascii_visual}
```
"""
            scenes_plan_parts.append(scene_text)

        scenes_plan = "\n".join(scenes_plan_parts)

        # Get content from document
        content_parts = []
        for section in document.sections[:15]:
            content_parts.append(f"## {section.heading}\n{section.content[:2000]}")
        content_text = "\n\n".join(content_parts)

        # Build the prompt
        prompt = SCRIPT_FROM_PLAN_PROMPT_TEMPLATE.format(
            plan_title=plan.title,
            central_question=plan.central_question,
            audience=plan.target_audience,
            visual_style=plan.visual_style,
            scenes_plan=scenes_plan,
            content=content_text[:50000],
        )

        # Generate script via LLM
        result = self.llm.generate_json(prompt, SCRIPT_SYSTEM_PROMPT)

        # Parse into Script model
        return self._parse_script_result(result, document.source_path)

    def generate_short(
        self,
        topic: str,
        duration_seconds: int = 45,
        evidence_urls: list[str] | None = None,
        style: str = "varun_mayya",
    ) -> Script:
        """
        Generate a short-form video script (Varun Mayya style).

        Creates a 15-60 second script with evidence-based scenes:
        - Hook (first 3 seconds, scroll-stopper)
        - Evidence scenes (proof shots with visuals)
        - Analysis (avatar explaining implications)
        - Conclusion/CTA (final punch)

        Args:
            topic: The topic or claim to create a short about
            duration_seconds: Target duration (15-60 seconds typical)
            evidence_urls: Optional list of URLs to use as evidence sources
            style: Style preset (varun_mayya, johnny_harris, generic)

        Returns:
            Script with evidence-based scenes ready for Investigator
        """
        # Format evidence URLs
        urls_text = "None provided - Investigator will search automatically"
        if evidence_urls:
            urls_text = "\n".join(f"- {url}" for url in evidence_urls)

        # Build the prompt
        prompt = SHORT_USER_PROMPT_TEMPLATE.format(
            duration_seconds=duration_seconds,
            topic=topic,
            evidence_urls=urls_text,
        )

        # Generate script via LLM
        result = self.llm.generate_json(prompt, SHORT_SYSTEM_PROMPT)

        # Parse into Script model
        return self._parse_short_result(result, topic)

    def _parse_short_result(self, result: dict, topic: str) -> Script:
        """Parse LLM result from short-form generation into a Script model."""
        scenes = []
        for idx, s in enumerate(result.get("scenes", [])):
            # Map short-form visual_type to VisualCue
            visual_type = s.get("visual_type", "full_avatar")
            visual_description = s.get("visual_description", "")
            needs_evidence = s.get("needs_evidence", visual_type != "full_avatar")

            visual_cue = VisualCue(
                description=visual_description,
                visual_type=visual_type,  # Use the evidence-based type
                elements=[],
                duration_seconds=s.get("duration_seconds", 5.0),
            )

            # Generate scene_id from role and index
            role = s.get("role", "evidence")
            scene_id = f"{role}_{idx + 1}"

            # Build notes with evidence info
            notes_parts = []
            notes_parts.append(f"Role: {role}")
            if needs_evidence:
                notes_parts.append("Needs Evidence: YES")
            if s.get("why"):
                notes_parts.append(f"Visual Reasoning: {s['why']}")
            notes = " | ".join(notes_parts)

            scene = ScriptScene(
                scene_id=scene_id,
                scene_type=role,  # Use role as scene_type for shorts
                title=f"Scene {idx + 1}: {role.title()}",
                voiceover=s.get("voiceover", ""),
                visual_cue=visual_cue,
                duration_seconds=s.get("duration_seconds", 5.0),
                notes=notes,
            )
            scenes.append(scene)

        total_duration = sum(s.duration_seconds for s in scenes)

        return Script(
            title=result.get("project_title", topic[:50]),
            total_duration_seconds=total_duration,
            scenes=scenes,
            source_document=f"prompt:{topic[:100]}",
        )

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

            # Handle scene_id - use slug-based ID
            scene_id = s.get("scene_id")
            if scene_id is None or isinstance(scene_id, int):
                # Generate slug from title
                title = s.get("title", f"scene_{idx + 1}")
                scene_id_str = self._slugify(title)
            elif isinstance(scene_id, str):
                # If it has a numeric prefix like "scene1_title", strip it
                if re.match(r'^scene\d+_', scene_id):
                    scene_id_str = re.sub(r'^scene\d+_', '', scene_id)
                else:
                    scene_id_str = scene_id
            else:
                scene_id_str = self._slugify(s.get("title", f"scene_{idx + 1}"))

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
                scene_id=scene_id_str,
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

        cumulative_time = 0.0
        for idx, scene in enumerate(script.scenes):
            timestamp = cumulative_time
            minutes = int(timestamp // 60)
            seconds = int(timestamp % 60)

            # Word count for reference
            word_count = len(scene.voiceover.split())

            lines.extend([
                f"## Scene {idx + 1} ({scene.scene_id}): {scene.title}",
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
            cumulative_time += scene.duration_seconds

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
        import re
        from pathlib import Path

        with open(Path(path)) as f:
            data = json.load(f)

        # Convert old numeric scene_ids to string format
        for scene in data.get("scenes", []):
            scene_id = scene.get("scene_id")
            if isinstance(scene_id, int):
                # Convert int to slug based on title
                title = scene.get("title", f"scene_{scene_id}")
                slug = title.lower()
                slug = re.sub(r'[\s\-]+', '_', slug)
                slug = re.sub(r'[^a-z0-9_]', '', slug)
                slug = re.sub(r'_+', '_', slug)
                slug = slug.strip('_')
                scene["scene_id"] = slug
            elif isinstance(scene_id, str) and re.match(r'^scene\d+_', scene_id):
                # Strip "sceneN_" prefix from old format
                scene["scene_id"] = re.sub(r'^scene\d+_', '', scene_id)

        return Script(**data)
