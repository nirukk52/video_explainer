"""
Skill 4: validate_retention - Retention Engineering

Scores a script's retention potential and flags drop-off risks.
Checks visual change frequency, stakes escalation, and pacing.
"""

import json
from typing import Optional

from openai import AsyncOpenAI

from ..models import DropOffRisk, DropOffSeverity, RetentionValidation, ValidateRetentionInput

RETENTION_PROMPT = """You are a YouTube Shorts retention analyst.

Your job is to predict Average View Percentage and flag drop-off risks.

RETENTION KILLERS (flag these):
1. No visual change for >4 seconds
2. Filler words or "dead air"
3. Stakes plateau (no new information)
4. Weak CTA (viewer leaves before end)
5. Audio/visual mismatch
6. Too long without payoff

VISUAL CHANGE FREQUENCY:
- Excellent: Every 1-2 seconds
- Good: Every 2-3 seconds
- Average: Every 3-4 seconds
- Poor: >4 seconds

RETENTION BENCHMARKS (tech/AI shorts):
- Top 10%: 75%+ avg view
- Top 25%: 65-75%
- Average: 50-65%
- Below average: <50%

DROP-OFF RISK SEVERITY:
- low: Minor issue, <5% impact
- medium: Noticeable, 5-15% impact
- high: Significant, >15% impact

OUTPUT JSON:
{
  "retention_score": 0-10,
  "predicted_avg_view_pct": 0-100,
  "drop_off_risks": [
    {
      "time_seconds": 12,
      "reason": "No visual change for 5 seconds",
      "severity": "high"
    }
  ],
  "recommendations": ["Add pattern interrupt at 12s"],
  "visual_change_frequency": 3.5,
  "stakes_escalation_valid": true/false,
  "benchmark_comparison": "Top 25% for tech/AI shorts"
}"""


async def validate_retention(
    params: ValidateRetentionInput,
    openai_api_key: Optional[str] = None,
) -> RetentionValidation:
    """
    Validate a script's retention potential and identify drop-off risks.

    Checks visual pacing, stakes escalation, and predicts avg view percentage.

    Args:
        params: Input with script content and target retention.
        openai_api_key: Optional API key (uses env var if not provided).

    Returns:
        RetentionValidation with score, risks, and recommendations.
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

    # Build timeline for analysis
    timeline_text = ""
    current_time = 0
    for scene in scenes:
        duration = scene.get("duration_seconds", 5)
        end_time = current_time + duration
        timeline_text += f"""
{current_time}s - {end_time}s:
  Voiceover: "{scene.get('voiceover_script', '')}"
  Visual: {scene.get('visual_plan', {}).get('type')}
  Evidence needed: {scene.get('needs_evidence', False)}
"""
        current_time = end_time

    user_prompt = f"""Analyze this script for retention:

TARGET: {params.target_retention_pct}% average view

TIMELINE:
{timeline_text}

TOTAL DURATION: {current_time}s

Evaluate retention potential and flag all drop-off risks.
Output JSON."""

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": RETENTION_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.5,
    )

    raw_content = response.choices[0].message.content
    if not raw_content:
        raise ValueError("Empty response from LLM")

    data = json.loads(raw_content)

    drop_off_risks = [
        DropOffRisk(
            time_seconds=r.get("time_seconds", 0),
            reason=r.get("reason", "Unknown"),
            severity=DropOffSeverity(r.get("severity", "medium")),
        )
        for r in data.get("drop_off_risks", [])
    ]

    return RetentionValidation(
        retention_score=data.get("retention_score", 5),
        predicted_avg_view_pct=data.get("predicted_avg_view_pct", 50),
        drop_off_risks=drop_off_risks,
        recommendations=data.get("recommendations", []),
        visual_change_frequency=data.get("visual_change_frequency", 3.0),
        stakes_escalation_valid=data.get("stakes_escalation_valid", True),
        benchmark_comparison=data.get("benchmark_comparison", "Average"),
    )
