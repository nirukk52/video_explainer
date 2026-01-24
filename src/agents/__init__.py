"""
Agent modules for the video production pipeline.

Each agent handles a specific phase of the evidence-based video workflow:
- Investigator: Primary source URL discovery via Exa.ai
- Witness: Visual asset capture (screenshots, recordings, DOM crops)
- Editor: Asset packaging for render pipelines

Note: Director logic is integrated into src/script/generator.py (ScriptGenerator class)
"""

from src.agents.base import BaseAgent
from src.agents.investigator import Investigator
from src.agents.witness import Witness
from src.agents.editor import Editor

__all__ = ["BaseAgent", "Investigator", "Witness", "Editor"]
