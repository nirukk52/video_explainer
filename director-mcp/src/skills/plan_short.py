"""
Skill 1: plan_short - Ultra-Tight Visual Storytelling

Transforms any topic into a 15-60 second script with proof beats.
Follows Varun Mayya style: Hook → Evidence → Analysis → CTA.
"""

import json
import sys
from pathlib import Path
from typing import Optional

from openai import AsyncOpenAI

# Import from centralized prompts (single source of truth)
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from src.prompts import VARUN_MAYYA_PROMPT, JOHNNY_HARRIS_PROMPT

from ..models import (
    PlanShortInput,
    Scene,
    SceneRole,
    ScriptOutput,
    VideoStyle,
    VisualPlan,
    VisualType,
)


async def plan_short(
    params: PlanShortInput,
    openai_api_key: Optional[str] = None,
) -> ScriptOutput:
    """
    Generate a complete short-form video script from a topic.

    Uses LLM to create scenes following the specified style (Varun Mayya default).
    Each scene has voiceover, visual plan, and evidence requirements.

    Args:
        params: Input parameters including topic, style, duration.
        openai_api_key: Optional API key (uses env var if not provided).

    Returns:
        ScriptOutput with complete script ready for production.
    """
    import os

    api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")

    client = AsyncOpenAI(api_key=api_key)

    # Select system prompt based on style
    if params.style == VideoStyle.VARUN_MAYYA:
        system_prompt = VARUN_MAYYA_PROMPT
    elif params.style == VideoStyle.JOHNNY_HARRIS:
        system_prompt = JOHNNY_HARRIS_PROMPT
    else:
        system_prompt = VARUN_MAYYA_PROMPT  # Default

    # Build user prompt
    user_prompt = f"""Create a {params.duration_seconds}-second short-form video script about:

TOPIC: {params.topic}

TARGET: {params.num_scenes} scenes

"""

    if params.evidence_urls:
        user_prompt += f"EVIDENCE SOURCES (use these URLs):\n"
        for url in params.evidence_urls:
            user_prompt += f"- {url}\n"

    user_prompt += """
Output a JSON object with this exact structure:
{
  "project_title": "string",
  "scenes": [
    {
      "scene_id": 1,
      "role": "hook" | "evidence" | "analysis" | "conclusion",
      "voiceover_script": "string (max 20 words)",
      "visual_plan": {
        "type": "static_highlight" | "scroll_highlight" | "dom_crop" | "full_avatar",
        "description": "string (specific search query for evidence)",
        "why": "string (reasoning)"
      },
      "duration_seconds": number
    }
  ]
}"""

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.7,
    )

    raw_content = response.choices[0].message.content
    if not raw_content:
        raise ValueError("Empty response from LLM")

    data = json.loads(raw_content)

    # Parse into structured output
    scenes: list[Scene] = []
    evidence_needed: list[str] = []

    for scene_data in data.get("scenes", []):
        visual_plan = VisualPlan(
            type=VisualType(scene_data["visual_plan"]["type"]),
            description=scene_data["visual_plan"]["description"],
            why=scene_data["visual_plan"].get("why"),
        )

        needs_evidence = visual_plan.type != VisualType.FULL_AVATAR

        scene = Scene(
            scene_id=scene_data["scene_id"],
            role=SceneRole(scene_data["role"]),
            voiceover_script=scene_data["voiceover_script"],
            visual_plan=visual_plan,
            needs_evidence=needs_evidence,
            duration_seconds=scene_data.get("duration_seconds", 5.0),
        )
        scenes.append(scene)

        if needs_evidence:
            evidence_needed.append(visual_plan.description)

    total_duration = sum(s.duration_seconds for s in scenes)

    return ScriptOutput(
        project_title=data.get("project_title", params.topic),
        style=params.style,
        total_duration_seconds=total_duration,
        scenes=scenes,
        evidence_needed=evidence_needed,
    )
