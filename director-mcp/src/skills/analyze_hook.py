"""
Skill 2: analyze_hook - Hook & Loop Instincts

Evaluates and improves the first 3 seconds of a script.
Checks for scroll-stopping elements, pattern interrupts, and hook strength.
"""

import json
import sys
from pathlib import Path
from typing import Optional

from openai import AsyncOpenAI

# Import from centralized prompts (single source of truth)
# Add parent directory to path for imports from main src/
_parent_dir = Path(__file__).parent.parent.parent.parent
if str(_parent_dir) not in sys.path:
    sys.path.insert(0, str(_parent_dir))

try:
    from src.prompts import HOOK_ANALYSIS_PROMPT
except ImportError:
    # Fallback prompt if main src is not available
    HOOK_ANALYSIS_PROMPT = """You are an expert short-form video hook analyst.
Your job is to evaluate the first 3 seconds of a video script and score its "scroll-stopping" potential.

WHAT MAKES A GREAT HOOK:
1. Pattern Interrupt: Something visually/aurally unexpected that breaks the scroll
2. Specificity: Numbers, names, outcomes ("$0.14" not "cheap")
3. Stakes: Why should I care RIGHT NOW?
4. Open Loop: Creates curiosity that demands resolution
5. Visual Match: The first frame supports the hook energy

OUTPUT JSON:
{
  "hook_score": 1-10,
  "pattern_interrupt": "weak" | "moderate" | "strong",
  "scroll_stop_potential": "description",
  "suggestions": ["list", "of", "improvements"],
  "improved_hook": "rewritten hook text if score < 8",
  "visual_match": true/false
}"""

from ..models import AnalyzeHookInput, HookAnalysis


async def analyze_hook(
    params: AnalyzeHookInput,
    openai_api_key: Optional[str] = None,
) -> HookAnalysis:
    """
    Analyze the hook (first scene) of a script for scroll-stopping potential.

    Evaluates pattern interrupt strength, specificity, and suggests improvements.

    Args:
        params: Input with script content and scene to analyze.
        openai_api_key: Optional API key (uses env var if not provided).

    Returns:
        HookAnalysis with score, suggestions, and improved hook.
    """
    import os

    api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")

    client = AsyncOpenAI(api_key=api_key)

    # Parse script (could be JSON string or file path)
    script_content = params.script_json
    if script_content.endswith(".json"):
        # It's a file path
        with open(script_content, "r") as f:
            script_data = json.load(f)
    else:
        # It's JSON content
        script_data = json.loads(script_content)

    # Find the target scene
    scenes = script_data.get("scenes", [])
    target_scene = None
    for scene in scenes:
        if scene.get("scene_id") == params.scene_id:
            target_scene = scene
            break

    if not target_scene:
        raise ValueError(f"Scene {params.scene_id} not found in script")

    user_prompt = f"""Analyze this hook scene:

VOICEOVER: "{target_scene.get('voiceover_script', '')}"

VISUAL TYPE: {target_scene.get('visual_plan', {}).get('type', 'unknown')}
VISUAL DESCRIPTION: {target_scene.get('visual_plan', {}).get('description', 'none')}

SCENE ROLE: {target_scene.get('role', 'hook')}
DURATION: {target_scene.get('duration_seconds', 3)} seconds

Evaluate and output JSON analysis."""

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": HOOK_ANALYSIS_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.5,
    )

    raw_content = response.choices[0].message.content
    if not raw_content:
        raise ValueError("Empty response from LLM")

    data = json.loads(raw_content)

    return HookAnalysis(
        hook_score=data.get("hook_score", 5),
        pattern_interrupt=data.get("pattern_interrupt", "moderate"),
        scroll_stop_potential=data.get("scroll_stop_potential", "Unknown"),
        suggestions=data.get("suggestions", []),
        improved_hook=data.get("improved_hook"),
        visual_match=data.get("visual_match", True),
    )
