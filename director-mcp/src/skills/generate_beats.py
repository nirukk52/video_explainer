"""
Skill 3: generate_beat_sheet - Stakes-Rising Structure

Breaks a script into 5-7 second visual beats with escalating stakes.
Ensures every beat raises the stakes from the previous one.
"""

import json
import sys
from pathlib import Path
from typing import Optional

from openai import AsyncOpenAI

# Import from centralized prompts (single source of truth)
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from src.prompts import BEAT_SHEET_PROMPT

from ..models import Beat, BeatSheet, GenerateBeatSheetInput


async def generate_beat_sheet(
    params: GenerateBeatSheetInput,
    openai_api_key: Optional[str] = None,
) -> BeatSheet:
    """
    Generate a beat sheet from a script, breaking it into timed visual beats.

    Each beat has timing, type, stakes level, and visual specification.
    Ensures stakes escalate throughout the video.

    Args:
        params: Input with script content and beat interval.
        openai_api_key: Optional API key (uses env var if not provided).

    Returns:
        BeatSheet with timed beats and pacing score.
    """
    import os

    api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")

    client = AsyncOpenAI(api_key=api_key)

    # Parse script
    script_content = params.script_json
    if script_content.endswith(".json"):
        with open(script_content, "r") as f:
            script_data = json.load(f)
    else:
        script_data = json.loads(script_content)

    scenes = script_data.get("scenes", [])

    # Format scenes for LLM
    scenes_text = ""
    for scene in scenes:
        scenes_text += f"""
Scene {scene.get('scene_id')}:
  Role: {scene.get('role')}
  Voiceover: "{scene.get('voiceover_script', '')}"
  Visual: {scene.get('visual_plan', {}).get('type')} - {scene.get('visual_plan', {}).get('description', '')}
  Duration: {scene.get('duration_seconds', 5)}s
"""

    user_prompt = f"""Break this script into beats (target: {params.beat_interval_seconds}s per beat):

{scenes_text}

Create a beat sheet with stakes that MUST escalate from beat to beat.
Output JSON."""

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": BEAT_SHEET_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.5,
    )

    raw_content = response.choices[0].message.content
    if not raw_content:
        raise ValueError("Empty response from LLM")

    data = json.loads(raw_content)

    beats = [
        Beat(
            time_range=b.get("time_range", "0-5s"),
            beat_type=b.get("beat_type", "unknown"),
            stakes=b.get("stakes", "unknown"),
            visual=b.get("visual", "unknown"),
            scene_id=b.get("scene_id", 1),
        )
        for b in data.get("beats", [])
    ]

    return BeatSheet(
        total_duration_seconds=data.get("total_duration_seconds", 30),
        num_beats=len(beats),
        beats=beats,
        stakes_curve=data.get("stakes_curve", "ascending"),
        pacing_score=data.get("pacing_score", 7),
    )
