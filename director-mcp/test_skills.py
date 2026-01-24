#!/usr/bin/env python3
"""
Test script for Director MCP skills.

Run with: python test_skills.py
Requires: OPENAI_API_KEY environment variable
"""

import asyncio
import json
import os

# Ensure we have API key
if not os.environ.get("OPENAI_API_KEY"):
    print("Error: OPENAI_API_KEY not set")
    print("Run: export $(cat ../.env | xargs)")
    exit(1)

from src.models import (
    AnalyzeHookInput,
    GenerateBeatSheetInput,
    PlanShortInput,
    ValidateRetentionInput,
    VideoStyle,
)
from src.skills import analyze_hook, generate_beat_sheet, plan_short, validate_retention


async def test_plan_short():
    """Test Skill 1: plan_short"""
    print("\n" + "=" * 60)
    print("SKILL 1: plan_short")
    print("=" * 60)

    params = PlanShortInput(
        topic="Why DeepSeek is disrupting OpenAI's pricing",
        style=VideoStyle.VARUN_MAYYA,
        duration_seconds=30,
        num_scenes=4,
    )

    result = await plan_short(params)

    print(f"Title: {result.project_title}")
    print(f"Style: {result.style}")
    print(f"Duration: {result.total_duration_seconds}s")
    print(f"Scenes: {len(result.scenes)}")
    print(f"Evidence needed: {len(result.evidence_needed)} items")

    for scene in result.scenes:
        print(f"\n  Scene {scene.scene_id} [{scene.role}]")
        print(f"    VO: {scene.voiceover_script}")
        print(f"    Visual: {scene.visual_plan.type}")
        print(f"    Evidence: {scene.needs_evidence}")

    return result


async def test_analyze_hook(script_output):
    """Test Skill 2: analyze_hook"""
    print("\n" + "=" * 60)
    print("SKILL 2: analyze_hook")
    print("=" * 60)

    # Convert script output to JSON string
    script_json = json.dumps(script_output.model_dump())

    params = AnalyzeHookInput(script_json=script_json, scene_id=1)

    result = await analyze_hook(params)

    print(f"Hook Score: {result.hook_score}/10")
    print(f"Pattern Interrupt: {result.pattern_interrupt}")
    print(f"Scroll Stop: {result.scroll_stop_potential}")
    print(f"Visual Match: {result.visual_match}")
    print(f"\nSuggestions:")
    for s in result.suggestions:
        print(f"  - {s}")
    if result.improved_hook:
        print(f"\nImproved Hook: {result.improved_hook}")

    return result


async def test_generate_beats(script_output):
    """Test Skill 3: generate_beat_sheet"""
    print("\n" + "=" * 60)
    print("SKILL 3: generate_beat_sheet")
    print("=" * 60)

    script_json = json.dumps(script_output.model_dump())

    params = GenerateBeatSheetInput(script_json=script_json, beat_interval_seconds=5)

    result = await generate_beat_sheet(params)

    print(f"Total Duration: {result.total_duration_seconds}s")
    print(f"Num Beats: {result.num_beats}")
    print(f"Stakes Curve: {result.stakes_curve}")
    print(f"Pacing Score: {result.pacing_score}/10")
    print(f"\nBeats:")
    for beat in result.beats:
        print(f"  {beat.time_range}: {beat.beat_type} ({beat.stakes}) - {beat.visual}")

    return result


async def test_validate_retention(script_output):
    """Test Skill 4: validate_retention"""
    print("\n" + "=" * 60)
    print("SKILL 4: validate_retention")
    print("=" * 60)

    script_json = json.dumps(script_output.model_dump())

    params = ValidateRetentionInput(script_json=script_json, target_retention_pct=70)

    result = await validate_retention(params)

    print(f"Retention Score: {result.retention_score}/10")
    print(f"Predicted Avg View: {result.predicted_avg_view_pct}%")
    print(f"Visual Change Freq: {result.visual_change_frequency}s")
    print(f"Stakes Valid: {result.stakes_escalation_valid}")
    print(f"Benchmark: {result.benchmark_comparison}")

    if result.drop_off_risks:
        print(f"\nDrop-off Risks:")
        for risk in result.drop_off_risks:
            print(f"  {risk.time_seconds}s [{risk.severity}]: {risk.reason}")

    if result.recommendations:
        print(f"\nRecommendations:")
        for rec in result.recommendations:
            print(f"  - {rec}")

    return result


async def main():
    print("=" * 60)
    print("DIRECTOR MCP SKILLS TEST")
    print("=" * 60)

    # Test Skill 1: plan_short
    script = await test_plan_short()

    # Test Skill 2: analyze_hook (uses script from Skill 1)
    await test_analyze_hook(script)

    # Test Skill 3: generate_beat_sheet
    await test_generate_beats(script)

    # Test Skill 4: validate_retention
    await test_validate_retention(script)

    print("\n" + "=" * 60)
    print("ALL SKILLS TESTED SUCCESSFULLY")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
