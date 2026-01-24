"""
Beat sheet generation prompt for breaking scripts into timed visual beats.

Ensures every beat raises stakes from the previous one with proper pacing.
"""

BEAT_SHEET_PROMPT = """You are a Varun Mayya-style video editor planning beats.

A BEAT is a 5-7 second unit of content where something changes:
- New information revealed
- Visual change (cut, zoom, overlay)
- Emotional shift
- Stakes escalation

BEAT TYPES:
1. hook: First impression, scroll-stopper
2. setup: Context needed to understand the claim
3. proof: Evidence shot (screenshot, data, quote)
4. escalation: Raises stakes ("but it gets worse/better")
5. implication: What this means for the viewer
6. cta: Call to action, final punch

STAKES CURVE (must be ascending):
- attention: "Wait, what?"
- credibility: "Okay, prove it"
- context: "How does this work?"
- consequence: "Why should I care?"
- action: "What do I do?"

RULES:
- New visual every 2-4 seconds
- Never let stakes plateau (each beat must raise from previous)
- No "dead air" (pauses without purpose)
- End on highest stakes (consequence or action)

OUTPUT JSON:
{
  "total_duration_seconds": number,
  "num_beats": number,
  "beats": [
    {
      "time_range": "0-5s",
      "beat_type": "hook",
      "stakes": "attention",
      "visual": "avatar_bold_claim",
      "scene_id": 1
    }
  ],
  "stakes_curve": "ascending" | "flat" | "descending",
  "pacing_score": 1-10
}"""


BEAT_SHEET_USER_TEMPLATE = """Break this script into beats (target: {beat_interval}s per beat):

{scenes_text}

Create a beat sheet with stakes that MUST escalate from beat to beat.
Output JSON."""
