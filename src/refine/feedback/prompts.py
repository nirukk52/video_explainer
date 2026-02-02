"""LLM prompts for feedback processing.

CORE PHILOSOPHY: Feedback refinement serves the greater purpose of creating
scroll-stopping 9:16 ads through authentic storytelling.
Every change should improve: hook strength, stakes escalation, or retention.
"""

PARSE_FEEDBACK_SYSTEM_PROMPT = """You are analyzing user feedback for a 9:16 ad factory project.

## Your Role in the Pipeline
You interpret feedback to generate precise patches that improve the video.
Every change should ultimately serve: authentic storytelling that converts.

Your task is to:
1. Determine what KIND of change is being requested (intent)
2. Identify which SCENES are affected
3. Provide a clear INTERPRETATION that considers storytelling impact
4. Flag if the change might hurt hook/retention/story arc

Be precise and specific. The feedback will be used to generate patches that modify project files."""


PARSE_FEEDBACK_PROMPT = """Analyze this user feedback for a 9:16 ad project.

## Project: {project_id}

## Greater Purpose Context
This project creates scroll-stopping vertical ads. Every change should improve:
- Hook strength (first 3 seconds grab attention)
- Stakes escalation (each beat raises stakes)
- Story completeness (problem → solution → resolution)
- Retention (visual change every 1.5-3s, no dead air)

## Available Scenes:
{scene_list}

## User Feedback:
"{feedback_text}"

## Intent Categories
Choose the most specific intent:
- script_content: Changing what is SAID in the narration (voiceover text)
- script_structure: Adding, removing, or reordering SCENES
- visual_cue: Changing the DESCRIPTION of what should be visualized
- visual_impl: Changing the ACTUAL CODE that renders the scene
- timing: Adjusting scene DURATIONS or pacing
- transition: Changing transition types between scenes
- style: Changing visual STYLING patterns
- mixed: Multiple types of changes (specify sub_intents)

## Instructions
1. Read the feedback carefully
2. Identify the primary intent
3. List affected scene IDs
4. Consider how this change impacts storytelling
5. Provide a clear interpretation

Respond with JSON:
{{
    "intent": "script_content|script_structure|visual_cue|visual_impl|timing|transition|style|mixed",
    "sub_intents": ["intent1", "intent2"],  // Only if intent is "mixed"
    "affected_scene_ids": ["scene_id_1", "scene_id_2"],  // Empty list for project-wide
    "scope": "scene|multi_scene|project",
    "interpretation": "Clear, actionable description of what the user wants changed",
    "storytelling_impact": "How this change affects hook/stakes/retention (positive/neutral/negative)",
    "suggested_improvements": ["additional changes that would enhance the feedback's intent"]
}}
"""


GENERATE_SCRIPT_PATCH_PROMPT = """Generate patches to modify the narration/script based on this feedback.

## Greater Purpose
This is a 9:16 ad. Every word must earn its place. No filler, no fluff.
Goal: Authentic storytelling that converts.

## Scene Information
Scene ID: {scene_id}
Scene Title: {scene_title}
Current Narration:
"{current_narration}"

## Feedback:
"{feedback_text}"

## Interpretation:
{interpretation}

## Narration Quality Guidelines (9:16 Ad Standard)
When revising narration, follow these principles:

1. **SPECIFIC NUMBERS** - Never vague qualifiers
   - BAD: "improved dramatically", "much better"
   - GOOD: "$0.14 vs $30", "3,000% growth", "17% to 78%"

2. **MAX 15 WORDS PER SCENE** - Every word earns its place
   - Cut filler: "basically", "you know", "sort of", "like"
   - Cut hedging: "I think", "maybe", "probably"
   - Be direct and punchy

3. **RAISE STAKES** - Each scene must escalate
   - Hook: "Wait, what?"
   - Evidence: "Prove it"
   - Implication: "Why should I care?"
   - CTA: "What do I do?"

4. **CREATE CURIOSITY GAPS** - Problem before solution
   - Build tension, then release
   - "Here's the problem..." → "But here's what changed..."

5. **CONVERSATIONAL TONE** - Like talking to a friend
   - Not formal, not scripted
   - Real, relatable, authentic

## Instructions
Generate specific text changes. Be precise.
Every change should make the narration more:
- Specific (numbers, names, outcomes)
- Punchy (short, direct, no filler)
- Engaging (raises stakes, creates curiosity)

Respond with JSON:
{{
    "changes": [
        {{
            "field": "voiceover",  // or "title"
            "old_text": "exact text to find (or null for additions)",
            "new_text": "replacement text",
            "reason": "why this change improves the ad",
            "word_count_before": number,
            "word_count_after": number
        }}
    ],
    "stakes_impact": "how this change affects stakes escalation"
}}
"""


GENERATE_VISUAL_CUE_PATCH_PROMPT = """Generate patches to update the visual_cue specification.

## Scene Information
Scene ID: {scene_id}
Scene Title: {scene_title}
Scene Type: {scene_type}
Narration: "{narration}"

## Current Visual Cue:
{current_visual_cue}

## Feedback:
"{feedback_text}"

## Interpretation:
{interpretation}

## Visual Styling Guidelines
- BACKGROUND: Scene canvas/backdrop - use LIGHT colors (#f0f0f5, #fafafa, #ffffff)
- UI COMPONENTS: Floating dark glass panels with:
  - Dark glass: rgba(18,20,25,0.98) backgrounds
  - Multi-layer shadows (5-7 layers) for depth
  - Bezel borders: light top/left, dark bottom/right
  - Inner shadows for recessed depth
  - Colored accent glows based on content

## Text Styling (CRITICAL)
- All text on dark panels MUST be white (#ffffff) or light gray
- NEVER use black/dark text on dark backgrounds - it will be invisible
- Minimum font sizes: titles 22-28px, body 16-18px, annotations 14-16px

## Layout Constraints
- Content panels start at LAYOUT.title.y + 140 (not crowding the header)
- Leave 100px at bottom for Reference component
- All labels/badges must stay INSIDE their containers (no overflow)
- Gap between panels: 25-50px

## Instructions
Generate an improved visual_cue that addresses the feedback while following styling guidelines.

Respond with JSON:
{{
    "needs_update": true,
    "new_visual_cue": {{
        "description": "BACKGROUND: [describe backdrop]. UI COMPONENTS: [describe panels].",
        "visual_type": "animation",
        "elements": [
            "BACKGROUND: description",
            "UI Component 1 with styling details",
            "UI Component 2 with styling details"
        ],
        "duration_seconds": {duration}
    }},
    "reason": "Why this change addresses the feedback"
}}
"""


GENERATE_STRUCTURE_PATCH_PROMPT = """Generate patches to modify the scene structure.

## Current Scenes:
{scene_list}

## Feedback:
"{feedback_text}"

## Interpretation:
{interpretation}

## Instructions
Determine what structural changes are needed:
- Adding a new scene (provide title, narration, visual description)
- Removing a scene (specify which one)
- Reordering scenes (provide new order)

Respond with JSON:
{{
    "action": "add|remove|reorder",
    "details": {{
        // For "add":
        "insert_after": "scene_id or null for beginning",
        "new_scene": {{
            "title": "Scene Title",
            "scene_type": "hook|context|explanation|insight|conclusion",
            "narration": "The voiceover text...",
            "visual_description": "What should be visualized",
            "duration_seconds": 25
        }},
        // For "remove":
        "scene_id": "scene_to_remove",
        // For "reorder":
        "new_order": ["scene_id_1", "scene_id_2", ...]
    }},
    "reason": "Why this structural change addresses the feedback"
}}
"""
