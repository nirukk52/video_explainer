#!/usr/bin/env python3
"""
Director MCP Server - Varun Mayya-style Short-Form Video Planning

This MCP server provides four skills for creating high-retention shorts:
1. plan_short: Transform topics into scripted scenes
2. analyze_hook: Evaluate and improve the first 3 seconds
3. generate_beat_sheet: Create timed visual beats with stakes escalation
4. validate_retention: Score retention potential and flag drop-off risks

Usage:
    # stdio transport (local)
    python -m src.server

    # HTTP transport (remote)
    python -m src.server --http --port 8001
"""

import json
import sys
from typing import Optional

from mcp.server.fastmcp import FastMCP

from .models import (
    AnalyzeHookInput,
    GenerateBeatSheetInput,
    PlanShortInput,
    ValidateRetentionInput,
)
from .skills import analyze_hook, generate_beat_sheet, plan_short, validate_retention

# Initialize the MCP server
mcp = FastMCP("director_mcp")


@mcp.tool(
    name="director_plan_short",
    annotations={
        "title": "Plan Short-Form Video",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def director_plan_short(params: PlanShortInput) -> str:
    """
    Create a complete short-form video script from a topic.

    Transforms any topic into a Varun Mayya-style script with:
    - Hook (first 3 seconds, scroll-stopper)
    - Evidence scenes (proof shots with visuals)
    - Analysis (avatar explaining implications)
    - CTA/Close (final punch)

    Args:
        params (PlanShortInput): Input parameters containing:
            - topic (str): The topic to create a short about
            - style (VideoStyle): Style preset (varun_mayya, johnny_harris, generic)
            - duration_seconds (int): Target duration (15-60s typical)
            - evidence_urls (Optional[list]): URLs to use as evidence sources
            - num_scenes (int): Number of scenes to generate (4-8 typical)

    Returns:
        str: JSON-formatted ScriptOutput with scenes, visual plans, and evidence needs.

    Examples:
        - "Create a 45-second short about DeepSeek's pricing crash"
        - "Plan a 30-second explainer on why NVIDIA stock is up"
    """
    try:
        result = await plan_short(params)
        return json.dumps(result.model_dump(), indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool(
    name="director_analyze_hook",
    annotations={
        "title": "Analyze Video Hook",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def director_analyze_hook(params: AnalyzeHookInput) -> str:
    """
    Evaluate the hook (first 3 seconds) of a script for scroll-stopping potential.

    Analyzes:
    - Pattern interrupt strength (weak/moderate/strong)
    - Specificity of claims (numbers, names, outcomes)
    - Visual-audio match
    - Open loop creation

    Args:
        params (AnalyzeHookInput): Input parameters containing:
            - script_json (str): Script content as JSON string or file path
            - scene_id (int): Which scene to analyze (default: 1)

    Returns:
        str: JSON-formatted HookAnalysis with score, suggestions, and improved hook.

    Examples:
        - Analyze hook: "Is my opening strong enough to stop scrolling?"
        - Improve hook: "How can I make my first 3 seconds more engaging?"
    """
    try:
        result = await analyze_hook(params)
        return json.dumps(result.model_dump(), indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool(
    name="director_generate_beats",
    annotations={
        "title": "Generate Beat Sheet",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def director_generate_beats(params: GenerateBeatSheetInput) -> str:
    """
    Break a script into timed visual beats with escalating stakes.

    Creates a beat sheet with:
    - Time ranges for each beat (5-7 seconds typical)
    - Beat types (hook, setup, proof, escalation, cta)
    - Stakes level (attention → credibility → consequence → action)
    - Visual specifications

    Args:
        params (GenerateBeatSheetInput): Input parameters containing:
            - script_json (str): Script content as JSON string or file path
            - beat_interval_seconds (int): Target beat interval (5-7s typical)

    Returns:
        str: JSON-formatted BeatSheet with beats, stakes curve, and pacing score.

    Examples:
        - "Break my script into beats for editing"
        - "What's the pacing structure of my video?"
    """
    try:
        result = await generate_beat_sheet(params)
        return json.dumps(result.model_dump(), indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool(
    name="director_validate_retention",
    annotations={
        "title": "Validate Retention Potential",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def director_validate_retention(params: ValidateRetentionInput) -> str:
    """
    Score a script's retention potential and identify drop-off risks.

    Evaluates:
    - Visual change frequency (target: 2-4 seconds)
    - Stakes escalation (must be ascending)
    - Drop-off risks (timestamps with severity)
    - Predicted average view percentage

    Args:
        params (ValidateRetentionInput): Input parameters containing:
            - script_json (str): Script content as JSON string or file path
            - target_retention_pct (int): Target avg view % (default: 70%)

    Returns:
        str: JSON-formatted RetentionValidation with score, risks, recommendations.

    Examples:
        - "Will viewers watch to the end?"
        - "Where might viewers drop off?"
        - "How does my script compare to top performers?"
    """
    try:
        result = await validate_retention(params)
        return json.dumps(result.model_dump(), indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def main():
    """Run the Director MCP server."""
    # Check for HTTP transport flag
    if "--http" in sys.argv:
        port = 8001
        for i, arg in enumerate(sys.argv):
            if arg == "--port" and i + 1 < len(sys.argv):
                port = int(sys.argv[i + 1])
        print(f"Starting Director MCP on HTTP port {port}...")
        mcp.run(transport="streamable_http", port=port)
    else:
        # Default: stdio transport
        mcp.run()


if __name__ == "__main__":
    main()
