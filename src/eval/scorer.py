"""
Template Scorer - Scores completed templates to identify winners.

Scoring dimensions:
- Hook Score (25%): From director_analyze_hook
- Retention Score (25%): From director_validate_retention
- Pacing Score (20%): From director_generate_beats
- Evidence Quality (15%): Screenshot resolution, relevance
- User Rating (15%): Upvote/downvote history

Winners (score >= 7.0) are added to the winner library for RAG retrieval.
"""

import json
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path

from src.factory.artifact_store import ArtifactStore, ArtifactType


@dataclass
class ScoreBreakdown:
    """Breakdown of individual scoring dimensions."""
    
    hook_score: float = 0.0
    retention_score: float = 0.0
    pacing_score: float = 0.0
    evidence_score: float = 0.0
    user_rating: float = 5.0  # Default neutral rating
    
    def to_dict(self) -> dict:
        return {
            "hook_score": self.hook_score,
            "retention_score": self.retention_score,
            "pacing_score": self.pacing_score,
            "evidence_score": self.evidence_score,
            "user_rating": self.user_rating,
        }


@dataclass
class TemplateScore:
    """Complete template score with breakdown and winner status."""
    
    project_id: str
    overall_score: float
    breakdown: ScoreBreakdown
    is_winner: bool
    
    # Metadata
    topic: Optional[str] = None
    script_summary: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "overall_score": round(self.overall_score, 2),
            "breakdown": self.breakdown.to_dict(),
            "is_winner": self.is_winner,
            "topic": self.topic,
            "script_summary": self.script_summary,
        }


class TemplateScorer:
    """
    Scores completed templates to identify winners.
    
    Winners are stored in the template library for RAG retrieval,
    improving future script generation.
    """
    
    # Scoring weights
    HOOK_WEIGHT = 0.25
    RETENTION_WEIGHT = 0.25
    PACING_WEIGHT = 0.20
    EVIDENCE_WEIGHT = 0.15
    USER_RATING_WEIGHT = 0.15
    
    # Winner threshold
    WINNER_THRESHOLD = 7.0
    
    def __init__(self, store: ArtifactStore):
        """
        Initialize the scorer.
        
        Args:
            store: ArtifactStore for retrieving artifacts.
        """
        self.store = store
    
    async def score_template(self, project_id: str) -> TemplateScore:
        """
        Score a completed template.
        
        Args:
            project_id: The project ID to score.
        
        Returns:
            TemplateScore with overall score and breakdown.
        """
        # Get the locked script
        script_artifact = self.store.get_locked_script()
        if not script_artifact:
            raise ValueError("No locked script found - template not complete")
        
        script_data = script_artifact.data
        topic = script_data.get("project_title", "Unknown")
        
        # Run analysis tools (these would call the actual LLM in production)
        hook_score = await self._analyze_hook(script_data)
        retention_score = await self._analyze_retention(script_data)
        pacing_score = await self._analyze_pacing(script_data)
        evidence_score = self._score_evidence()
        user_rating = self._get_user_rating(project_id)
        
        # Create breakdown
        breakdown = ScoreBreakdown(
            hook_score=hook_score,
            retention_score=retention_score,
            pacing_score=pacing_score,
            evidence_score=evidence_score,
            user_rating=user_rating,
        )
        
        # Calculate weighted overall score
        overall_score = (
            breakdown.hook_score * self.HOOK_WEIGHT +
            breakdown.retention_score * self.RETENTION_WEIGHT +
            breakdown.pacing_score * self.PACING_WEIGHT +
            breakdown.evidence_score * self.EVIDENCE_WEIGHT +
            breakdown.user_rating * self.USER_RATING_WEIGHT
        )
        
        is_winner = overall_score >= self.WINNER_THRESHOLD
        
        # Store the score as an artifact
        self.store.put(
            ArtifactType.RETENTION_SCORE,  # Reusing this type for overall scores
            {
                "project_id": project_id,
                "overall_score": overall_score,
                "breakdown": breakdown.to_dict(),
                "is_winner": is_winner,
            },
            created_by="eval_service",
        )
        
        return TemplateScore(
            project_id=project_id,
            overall_score=overall_score,
            breakdown=breakdown,
            is_winner=is_winner,
            topic=topic,
            script_summary=self._summarize_script(script_data),
        )
    
    async def _analyze_hook(self, script_data: dict) -> float:
        """
        Analyze hook quality.
        
        In production, this calls director_analyze_hook.
        For now, returns a heuristic score based on script structure.
        """
        scenes = script_data.get("scenes", [])
        if not scenes:
            return 5.0
        
        hook_scene = scenes[0]
        voiceover = hook_scene.get("voiceover", "")
        
        # Heuristics for hook quality
        score = 5.0
        
        # Specific numbers are good
        if any(char.isdigit() for char in voiceover):
            score += 1.0
        
        # Short, punchy hooks are better
        word_count = len(voiceover.split())
        if word_count <= 15:
            score += 1.0
        elif word_count <= 20:
            score += 0.5
        
        # Check for hook patterns
        hook_patterns = ["what if", "this is", "look at", "breaking"]
        if any(pattern in voiceover.lower() for pattern in hook_patterns):
            score += 1.0
        
        return min(score, 10.0)
    
    async def _analyze_retention(self, script_data: dict) -> float:
        """
        Analyze retention potential.
        
        In production, this calls director_validate_retention.
        """
        scenes = script_data.get("scenes", [])
        if not scenes:
            return 5.0
        
        score = 6.0
        
        # Check scene variety
        visual_types = set(s.get("visual_type") for s in scenes)
        if len(visual_types) >= 3:
            score += 1.0
        
        # Check for evidence scenes
        evidence_scenes = [s for s in scenes if s.get("needs_evidence")]
        if evidence_scenes:
            score += 1.0
        
        # Check for good pacing (2-7 second scenes)
        good_pacing = all(
            2 <= s.get("duration_seconds", 5) <= 7
            for s in scenes
        )
        if good_pacing:
            score += 1.0
        
        return min(score, 10.0)
    
    async def _analyze_pacing(self, script_data: dict) -> float:
        """
        Analyze pacing and stakes escalation.
        
        In production, this calls director_generate_beats.
        """
        scenes = script_data.get("scenes", [])
        if not scenes:
            return 5.0
        
        score = 6.0
        
        # Check for proper role progression
        roles = [s.get("role") for s in scenes]
        expected_flow = ["hook", "evidence", "analysis", "conclusion"]
        
        if roles and roles[0] == "hook":
            score += 1.0
        
        if roles and roles[-1] in ["conclusion", "cta"]:
            score += 1.0
        
        # Check for role variety
        if len(set(roles)) >= 3:
            score += 1.0
        
        return min(score, 10.0)
    
    def _score_evidence(self) -> float:
        """
        Score evidence quality based on screenshots.
        """
        screenshots = self.store.get_locked_screenshots()
        
        if not screenshots:
            return 5.0
        
        score = 6.0
        
        # More screenshots = better evidence
        if len(screenshots) >= 2:
            score += 1.0
        if len(screenshots) >= 3:
            score += 1.0
        
        # Check for file paths (actual captures)
        actual_captures = [s for s in screenshots if s.file_path]
        if actual_captures:
            score += 1.0
        
        return min(score, 10.0)
    
    def _get_user_rating(self, project_id: str) -> float:
        """
        Get user rating for the project.
        
        In production, this reads from the database.
        """
        # Default neutral rating
        return 5.0
    
    def _summarize_script(self, script_data: dict) -> str:
        """Create a brief summary of the script."""
        scenes = script_data.get("scenes", [])
        if not scenes:
            return "Empty script"
        
        voiceovers = [s.get("voiceover", "") for s in scenes[:2]]
        return " | ".join(voiceovers)[:100]
