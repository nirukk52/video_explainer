"""Plan generator - creates video plans from content analysis."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ..config import Config, load_config
from ..models import (
    ContentAnalysis,
    ParsedDocument,
    PlannedScene,
    VideoPlan,
)
from ..understanding.llm_provider import LLMProvider, get_llm_provider
from .prompts import (
    PLAN_SYSTEM_PROMPT,
    PLAN_USER_PROMPT_TEMPLATE,
    PLAN_REFINE_PROMPT_TEMPLATE,
)


class PlanGenerator:
    """Generates video plans from content analysis."""

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
    ) -> VideoPlan:
        """Generate a video plan from analyzed content.

        Args:
            document: The parsed source document
            analysis: Content analysis with key concepts
            target_duration: Target duration in seconds (uses analysis suggestion if None)

        Returns:
            VideoPlan with scenes and visual approaches
        """
        duration = target_duration or analysis.suggested_duration_seconds
        duration_minutes = duration / 60

        # Calculate target scene count based on duration (roughly 1-2 minutes per scene)
        target_scenes = max(4, min(8, int(duration_minutes * 0.8)))

        # Format concepts for the prompt
        concepts_text = "\n".join(
            f"{i+1}. **{c.name}** (complexity: {c.complexity}/10)\n"
            f"   {c.explanation}\n"
            f"   Prerequisites: {', '.join(c.prerequisites) if c.prerequisites else 'None'}\n"
            f"   Visual potential: {c.visual_potential}"
            for i, c in enumerate(analysis.key_concepts)
        )

        # Get content from document
        content_parts = []
        for section in document.sections[:15]:
            content_parts.append(f"## {section.heading}\n{section.content[:1500]}")
        content_text = "\n\n".join(content_parts)

        # Build the prompt
        prompt = PLAN_USER_PROMPT_TEMPLATE.format(
            title=document.title,
            duration_minutes=duration_minutes,
            audience=analysis.target_audience,
            thesis=analysis.core_thesis,
            concepts=concepts_text,
            content=content_text[:30000],
            target_scenes=target_scenes,
        )

        # Generate plan via LLM
        result = self.llm.generate_json(prompt, PLAN_SYSTEM_PROMPT)

        # Parse into VideoPlan model
        return self._parse_plan_result(result, document.source_path)

    def refine(self, plan: VideoPlan, user_feedback: str) -> VideoPlan:
        """Refine an existing plan based on user feedback.

        Args:
            plan: The current video plan
            user_feedback: Natural language feedback from the user

        Returns:
            Updated VideoPlan
        """
        # Convert plan to JSON for the prompt
        plan_json = plan.model_dump_json(indent=2)

        # Build the refinement prompt
        prompt = PLAN_REFINE_PROMPT_TEMPLATE.format(
            current_plan_json=plan_json,
            user_feedback=user_feedback,
        )

        # Generate refined plan via LLM
        result = self.llm.generate_json(prompt, PLAN_SYSTEM_PROMPT)

        # Parse and preserve metadata
        refined_plan = self._parse_plan_result(result, plan.source_document)
        refined_plan.created_at = plan.created_at
        refined_plan.user_notes = (plan.user_notes + "\n" + user_feedback).strip()

        return refined_plan

    def _parse_plan_result(self, result: dict, source_path: str) -> VideoPlan:
        """Parse LLM result into a VideoPlan model."""
        scenes = []
        for s in result.get("scenes", []):
            scene = PlannedScene(
                scene_number=s.get("scene_number", len(scenes) + 1),
                scene_type=s.get("scene_type", "explanation"),
                title=s.get("title", ""),
                concept_to_cover=s.get("concept_to_cover", ""),
                visual_approach=s.get("visual_approach", ""),
                ascii_visual=s.get("ascii_visual", ""),
                estimated_duration_seconds=s.get("estimated_duration_seconds", 60.0),
                key_points=s.get("key_points", []),
            )
            scenes.append(scene)

        total_duration = sum(s.estimated_duration_seconds for s in scenes)

        return VideoPlan(
            status="draft",
            created_at=datetime.now().isoformat(),
            title=result.get("title", "Untitled"),
            central_question=result.get("central_question", ""),
            target_audience=result.get("target_audience", "Technical audience"),
            estimated_total_duration_seconds=total_duration,
            core_thesis=result.get("core_thesis", ""),
            key_concepts=result.get("key_concepts", []),
            complexity_score=result.get("complexity_score", 5),
            scenes=scenes,
            visual_style=result.get("visual_style", "Clean diagrams with animations"),
            source_document=source_path,
        )

    def format_for_display(self, plan: VideoPlan) -> str:
        """Format a plan for terminal display.

        Args:
            plan: The video plan to format

        Returns:
            Formatted string with ASCII art and styling
        """
        lines = []
        width = 60

        # Header
        lines.append("═" * width)
        lines.append(f"VIDEO PLAN: {plan.title}")
        lines.append("═" * width)

        # Metadata
        duration_mins = plan.estimated_total_duration_seconds / 60
        lines.append(f"Central Question: {plan.central_question}")
        lines.append(f"Target Audience: {plan.target_audience}")
        lines.append(f"Duration: ~{duration_mins:.0f} minutes | Complexity: {plan.complexity_score}/10")
        lines.append(f"Status: {plan.status.upper()}")
        lines.append("")

        # Visual style
        lines.append(f"Visual Style: {plan.visual_style}")
        lines.append("")

        # Key concepts
        if plan.key_concepts:
            lines.append("Key Concepts: " + ", ".join(plan.key_concepts[:5]))
            if len(plan.key_concepts) > 5:
                lines.append(f"  ... and {len(plan.key_concepts) - 5} more")
        lines.append("")

        lines.append("SCENES:")
        lines.append("─" * width)

        # Scenes
        for scene in plan.scenes:
            scene_type_upper = scene.scene_type.upper()
            duration = scene.estimated_duration_seconds

            lines.append(f"{scene.scene_number}. [{scene_type_upper}] {scene.title} ({duration:.0f}s)")
            lines.append(f"   Cover: {scene.concept_to_cover}")
            lines.append("")

            # ASCII visual
            if scene.ascii_visual:
                ascii_lines = scene.ascii_visual.split("\n")
                for ascii_line in ascii_lines:
                    lines.append(f"   {ascii_line}")
                lines.append("")

            # Key points
            if scene.key_points:
                lines.append("   Key Points:")
                for point in scene.key_points[:3]:
                    lines.append(f"   • {point}")
                lines.append("")

            lines.append("─" * width)

        # Footer
        lines.append("")
        lines.append("═" * width)
        lines.append("Commands: [a]pprove | [r]efine <feedback> | [s]ave | [q]uit")

        return "\n".join(lines)

    def save_plan(self, plan: VideoPlan, plan_dir: Path) -> tuple[Path, Path]:
        """Save a plan to JSON and markdown files.

        Args:
            plan: The plan to save
            plan_dir: Directory to save the plan files

        Returns:
            Tuple of (json_path, markdown_path)
        """
        plan_dir.mkdir(parents=True, exist_ok=True)

        # Save JSON
        json_path = plan_dir / "plan.json"
        with open(json_path, "w") as f:
            json.dump(plan.model_dump(), f, indent=2)

        # Save markdown
        md_path = plan_dir / "plan.md"
        with open(md_path, "w") as f:
            f.write(self.format_for_display(plan))

        return json_path, md_path

    @staticmethod
    def load_plan(plan_path: Path) -> VideoPlan:
        """Load a plan from a JSON file.

        Args:
            plan_path: Path to the plan.json file

        Returns:
            Loaded VideoPlan object
        """
        with open(plan_path) as f:
            data = json.load(f)
        return VideoPlan(**data)
