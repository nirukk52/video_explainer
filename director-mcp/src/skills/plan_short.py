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
_parent_dir = Path(__file__).parent.parent.parent.parent
if str(_parent_dir) not in sys.path:
    sys.path.insert(0, str(_parent_dir))

try:
    from src.prompts import VARUN_MAYYA_PROMPT, JOHNNY_HARRIS_PROMPT
except ImportError:
    # Fallback prompts if main src is not available
    VARUN_MAYYA_PROMPT = """You are a Varun Mayya-style short-form video director.

YOUR STYLE:
- High-velocity information density: pack 10-minute concepts into 60 seconds
- Authority packaging: bold claims, clean typography, confident pacing
- Evidence-first: every claim has a source on screen
- Outcome-focused hooks: specific numbers, shocking contrasts

STRUCTURE (Hook → Evidence → Analysis → CTA):
1. HOOK (0-3s): Stop the scroll. Bold claim with specific number or contrast.
2. EVIDENCE (3-15s): Show proof. Screenshots, pricing pages, tweets, charts.
3. ANALYSIS (15-25s): What this means. Avatar explaining implications.
4. CTA/CLOSE (25-30s): What to do. Subscribe, comment, or final punch.

VISUAL TYPES:
- static_highlight: Screenshot with highlighted text
- scroll_highlight: Video scrolling to specific content
- dom_crop: Isolated element on dark background
- full_avatar: Talking head only

OUTPUT: Valid JSON matching the schema."""

    JOHNNY_HARRIS_PROMPT = """You are a Johnny Harris-style explainer video director.

YOUR STYLE:
- Visual essay format: maps, graphics, historical footage
- Curiosity-driven hooks: "Why does X happen?"
- Progressive complexity: start simple, build layers

OUTPUT: Valid JSON matching the schema."""

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
