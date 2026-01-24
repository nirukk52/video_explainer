"""
Eval Service - Scores completed templates and manages the winner library.

The Eval Service runs after Factory completion to:
- Auto-score templates using multiple dimensions
- Identify winners (score >= 7.0)
- Store winners with embeddings for RAG retrieval
- Track user ratings for continuous improvement
"""

from src.eval.scorer import TemplateScorer, TemplateScore
from src.eval.winner_library import WinnerLibrary

__all__ = ["TemplateScorer", "TemplateScore", "WinnerLibrary"]
