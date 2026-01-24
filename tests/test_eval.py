"""
Tests for the Eval Service (Template Scoring and Winner Library).
"""

import pytest
import tempfile
from pathlib import Path

from src.eval.scorer import TemplateScorer, TemplateScore
from src.eval.winner_library import WinnerLibrary, WinnerTemplate
from src.factory.artifact_store import ArtifactStore, ArtifactType


class TestTemplateScorer:
    """Tests for the TemplateScorer class."""
    
    def test_scorer_requires_locked_script(self, tmp_path):
        """Scorer should require a locked script to score."""
        store = ArtifactStore(tmp_path)
        scorer = TemplateScorer(store)
        
        # No script - should raise error
        with pytest.raises(ValueError, match="No locked script"):
            import asyncio
            asyncio.run(scorer.score_template("test_project"))
    
    @pytest.mark.asyncio
    async def test_scorer_calculates_weighted_score(self, tmp_path):
        """Scorer should calculate weighted score from all dimensions."""
        store = ArtifactStore(tmp_path)
        
        # Add and lock a script
        script = store.put(
            ArtifactType.SCRIPT,
            {
                "project_title": "DeepSeek Pricing",
                "scenes": [
                    {
                        "scene_id": 1,
                        "role": "hook",
                        "voiceover": "DeepSeek just dropped API pricing that's 95% cheaper.",
                        "visual_type": "full_avatar",
                        "needs_evidence": False,
                        "duration_seconds": 5,
                    },
                    {
                        "scene_id": 2,
                        "role": "evidence",
                        "voiceover": "Look at this pricing page.",
                        "visual_type": "static_highlight",
                        "needs_evidence": True,
                        "duration_seconds": 5,
                    },
                    {
                        "scene_id": 3,
                        "role": "analysis",
                        "voiceover": "This means startups can build AI products cheaper.",
                        "visual_type": "full_avatar",
                        "needs_evidence": False,
                        "duration_seconds": 6,
                    },
                    {
                        "scene_id": 4,
                        "role": "conclusion",
                        "voiceover": "Follow for more AI updates.",
                        "visual_type": "full_avatar",
                        "needs_evidence": False,
                        "duration_seconds": 4,
                    },
                ],
            },
            created_by="test",
        )
        store.lock(script.id, "test")
        
        # Add and lock a screenshot
        screenshot = store.put(
            ArtifactType.SCREENSHOT,
            {"path": "pricing.png"},
            scene_id="2",
            created_by="test",
        )
        store.lock(screenshot.id, "test")
        
        # Score the template
        scorer = TemplateScorer(store)
        score = await scorer.score_template("test_project")
        
        # Should have calculated a score
        assert score.overall_score > 0
        assert score.overall_score <= 10
        
        # Breakdown should have all dimensions
        assert score.breakdown.hook_score > 0
        assert score.breakdown.retention_score > 0
        assert score.breakdown.pacing_score > 0
        assert score.breakdown.evidence_score > 0
    
    @pytest.mark.asyncio
    async def test_winner_threshold(self, tmp_path):
        """Templates scoring >= 7 should be winners."""
        store = ArtifactStore(tmp_path)
        
        # Add a good script
        script = store.put(
            ArtifactType.SCRIPT,
            {
                "project_title": "AI Market Crash",
                "scenes": [
                    {
                        "scene_id": 1,
                        "role": "hook",
                        "voiceover": "This is going to blow your mind. DeepSeek costs $0.14 per million tokens.",
                        "visual_type": "full_avatar",
                        "needs_evidence": False,
                        "duration_seconds": 4,
                    },
                    {
                        "scene_id": 2,
                        "role": "evidence",
                        "voiceover": "Look at this official pricing page.",
                        "visual_type": "static_highlight",
                        "needs_evidence": True,
                        "duration_seconds": 5,
                    },
                    {
                        "scene_id": 3,
                        "role": "analysis",
                        "voiceover": "The implications are massive for startups.",
                        "visual_type": "full_avatar",
                        "needs_evidence": False,
                        "duration_seconds": 5,
                    },
                    {
                        "scene_id": 4,
                        "role": "conclusion",
                        "voiceover": "Follow for more breaking AI news.",
                        "visual_type": "full_avatar",
                        "needs_evidence": False,
                        "duration_seconds": 3,
                    },
                ],
            },
            created_by="test",
        )
        store.lock(script.id, "test")
        
        # Add multiple screenshots
        for i in range(3):
            ss = store.put(
                ArtifactType.SCREENSHOT,
                {"path": f"evidence_{i}.png"},
                scene_id="2",
                file_path=f"/tmp/evidence_{i}.png",
                created_by="test",
            )
            store.lock(ss.id, "test")
        
        scorer = TemplateScorer(store)
        score = await scorer.score_template("test_project")
        
        # With good structure and evidence, should score well
        assert score.overall_score >= 6.0


class TestWinnerLibrary:
    """Tests for the WinnerLibrary class."""
    
    @pytest.mark.asyncio
    async def test_add_winner(self, tmp_path):
        """Should add winners to the library."""
        library = WinnerLibrary(tmp_path / "winners.json")
        
        winner = await library.add_winner(
            project_id="project_123",
            topic="DeepSeek pricing crash",
            script_json={"title": "Test", "scenes": []},
            score=8.5,
        )
        
        assert winner.id == "project_123"
        assert winner.score == 8.5
        assert library.count() == 1
    
    @pytest.mark.asyncio
    async def test_get_similar_winners(self, tmp_path):
        """Should find similar winners by topic."""
        library = WinnerLibrary(tmp_path / "winners.json")
        
        # Add some winners
        await library.add_winner(
            project_id="ai_pricing",
            topic="AI API pricing comparison",
            script_json={"title": "Pricing", "scenes": []},
            score=8.0,
        )
        await library.add_winner(
            project_id="nvidia_stock",
            topic="NVIDIA stock performance",
            script_json={"title": "NVIDIA", "scenes": []},
            score=7.5,
        )
        await library.add_winner(
            project_id="openai_news",
            topic="OpenAI announcement news",
            script_json={"title": "OpenAI", "scenes": []},
            score=9.0,
        )
        
        # Search for AI-related winners
        similar = await library.get_similar_winners("DeepSeek AI pricing", limit=2)
        
        assert len(similar) <= 2
        assert all(isinstance(w, WinnerTemplate) for w in similar)
    
    @pytest.mark.asyncio
    async def test_persistence(self, tmp_path):
        """Winners should persist across library instances."""
        storage_path = tmp_path / "winners.json"
        
        # Add a winner
        library1 = WinnerLibrary(storage_path)
        await library1.add_winner(
            project_id="test_123",
            topic="Test Topic",
            script_json={"title": "Test"},
            score=7.5,
        )
        
        # Load in new instance
        library2 = WinnerLibrary(storage_path)
        
        assert library2.count() == 1
        winner = library2.get_winner("test_123")
        assert winner is not None
        assert winner.topic == "Test Topic"
    
    def test_list_winners_sorted_by_score(self, tmp_path):
        """list_winners should return winners sorted by score."""
        library = WinnerLibrary(tmp_path / "winners.json")
        
        import asyncio
        
        async def add_all():
            await library.add_winner("low", "Low score", {}, 7.0)
            await library.add_winner("mid", "Mid score", {}, 8.0)
            await library.add_winner("high", "High score", {}, 9.0)
        
        asyncio.run(add_all())
        
        winners = library.list_winners()
        
        assert len(winners) == 3
        assert winners[0].id == "high"
        assert winners[1].id == "mid"
        assert winners[2].id == "low"
