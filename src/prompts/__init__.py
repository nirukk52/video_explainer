"""
Centralized prompt templates for video production.

All LLM prompts are stored here to:
- Keep prompts maintainable and version-controlled
- Enable easy A/B testing of prompt variations
- Separate prompt engineering from business logic

CORE PHILOSOPHY: Every LLM in this pipeline serves ONE goal:
Creating scroll-stopping 9:16 vertical ads through authentic storytelling.
"""

from src.prompts.core_philosophy import (
    GREATER_PURPOSE,
    MODERN_EDITING_STYLE,
    TEMPLATE_GUIDE,
    PLATFORM_GUIDE,
    FULL_CONTEXT,
    SUGGESTION_GUIDE,
)
from src.prompts.director_short import (
    SHORT_SYSTEM_PROMPT,
    SHORT_USER_PROMPT_TEMPLATE,
    VARUN_MAYYA_PROMPT,
    JOHNNY_HARRIS_PROMPT,
)
from src.prompts.director_explainer import (
    EXPLAINER_SYSTEM_PROMPT,
    EXPLAINER_USER_PROMPT_TEMPLATE,
)
from src.prompts.hook_analysis import HOOK_ANALYSIS_PROMPT
from src.prompts.beat_sheet import BEAT_SHEET_PROMPT
from src.prompts.retention_validation import RETENTION_PROMPT
from src.prompts.anchor_picker import ANCHOR_PICKER_PROMPT

__all__ = [
    # Core philosophy (shared across all LLMs)
    "GREATER_PURPOSE",
    "MODERN_EDITING_STYLE",
    "TEMPLATE_GUIDE",
    "PLATFORM_GUIDE",
    "FULL_CONTEXT",
    "SUGGESTION_GUIDE",
    # Director prompts
    "SHORT_SYSTEM_PROMPT",
    "SHORT_USER_PROMPT_TEMPLATE",
    "VARUN_MAYYA_PROMPT",
    "JOHNNY_HARRIS_PROMPT",
    "EXPLAINER_SYSTEM_PROMPT",
    "EXPLAINER_USER_PROMPT_TEMPLATE",
    # Analysis prompts
    "HOOK_ANALYSIS_PROMPT",
    "BEAT_SHEET_PROMPT",
    "RETENTION_PROMPT",
    # Witness prompts
    "ANCHOR_PICKER_PROMPT",
]
