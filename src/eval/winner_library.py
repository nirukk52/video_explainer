"""
Winner Library - Stores winning templates with embeddings for RAG retrieval.

Winners (templates scoring >= 7.0) are embedded and stored for:
- Few-shot prompting in future script generation
- Finding similar successful templates
- Continuous improvement through learning from winners
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional
import os


@dataclass
class WinnerTemplate:
    """A winning template stored in the library."""
    
    id: str
    topic: str
    script_json: dict
    score: float
    embedding: Optional[list[float]] = None
    usage_count: int = 0
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "topic": self.topic,
            "script_json": self.script_json,
            "score": self.score,
            "usage_count": self.usage_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "WinnerTemplate":
        return cls(
            id=data["id"],
            topic=data["topic"],
            script_json=data["script_json"],
            score=data["score"],
            embedding=data.get("embedding"),
            usage_count=data.get("usage_count", 0),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
        )


class WinnerLibrary:
    """
    Stores winning templates with embeddings for RAG retrieval.
    
    In production, this would use:
    - Vercel Postgres with pgvector for storage
    - OpenAI embeddings for similarity search
    
    For local development, uses JSON file storage.
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize the winner library.
        
        Args:
            storage_path: Path to JSON storage file (defaults to output/winners.json)
        """
        self.storage_path = storage_path or Path("output/winners.json")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._winners: dict[str, WinnerTemplate] = {}
        self._load()
    
    def _load(self) -> None:
        """Load winners from storage."""
        if self.storage_path.exists():
            with open(self.storage_path) as f:
                data = json.load(f)
            for winner_data in data.get("winners", []):
                winner = WinnerTemplate.from_dict(winner_data)
                self._winners[winner.id] = winner
    
    def _save(self) -> None:
        """Save winners to storage."""
        data = {
            "winners": [w.to_dict() for w in self._winners.values()],
            "updated_at": datetime.now().isoformat(),
        }
        with open(self.storage_path, "w") as f:
            json.dump(data, f, indent=2)
    
    async def add_winner(
        self,
        project_id: str,
        topic: str,
        script_json: dict,
        score: float,
    ) -> WinnerTemplate:
        """
        Add a winning template to the library.
        
        Args:
            project_id: Unique project ID
            topic: Topic of the template
            script_json: Full script data
            score: Overall score (should be >= 7.0)
        
        Returns:
            The created WinnerTemplate.
        """
        # Generate embedding (in production, use OpenAI embeddings)
        embedding = await self._generate_embedding(topic, script_json)
        
        winner = WinnerTemplate(
            id=project_id,
            topic=topic,
            script_json=script_json,
            score=score,
            embedding=embedding,
        )
        
        self._winners[project_id] = winner
        self._save()
        
        return winner
    
    async def get_similar_winners(
        self,
        topic: str,
        limit: int = 3,
    ) -> list[WinnerTemplate]:
        """
        Find similar winning templates for a topic.
        
        Uses embedding similarity search in production.
        For local dev, uses simple keyword matching.
        
        Args:
            topic: Topic to search for
            limit: Maximum number of winners to return
        
        Returns:
            List of similar WinnerTemplate objects.
        """
        if not self._winners:
            return []
        
        # Generate embedding for query
        query_embedding = await self._generate_embedding(topic, {})
        
        # Score all winners by similarity
        scored_winners = []
        for winner in self._winners.values():
            similarity = self._compute_similarity(query_embedding, winner)
            scored_winners.append((similarity, winner))
        
        # Sort by similarity (descending) and return top N
        scored_winners.sort(key=lambda x: x[0], reverse=True)
        
        # Increment usage count for returned winners
        results = []
        for _, winner in scored_winners[:limit]:
            winner.usage_count += 1
            results.append(winner)
        
        self._save()
        return results
    
    async def _generate_embedding(
        self,
        topic: str,
        script_json: dict,
    ) -> list[float]:
        """
        Generate embedding for a topic/script.
        
        In production, uses OpenAI embeddings API.
        For local dev, returns a simple keyword-based vector.
        """
        # Combine topic and voiceovers for embedding
        text = topic.lower()
        
        scenes = script_json.get("scenes", [])
        for scene in scenes:
            voiceover = scene.get("voiceover", "")
            text += " " + voiceover.lower()
        
        # Simple keyword-based embedding (replace with OpenAI in production)
        keywords = [
            "ai", "pricing", "cost", "api", "deepseek", "openai", "nvidia",
            "tech", "startup", "business", "money", "growth", "market",
            "news", "breaking", "announcement", "launch", "update",
        ]
        
        embedding = []
        for keyword in keywords:
            count = text.count(keyword)
            embedding.append(min(count / 5.0, 1.0))  # Normalize to 0-1
        
        return embedding
    
    def _compute_similarity(
        self,
        query_embedding: list[float],
        winner: WinnerTemplate,
    ) -> float:
        """
        Compute similarity between query and winner.
        
        Uses cosine similarity in production.
        For local dev, uses simple dot product.
        """
        if not winner.embedding:
            # Fallback to keyword matching
            return self._keyword_similarity(query_embedding, winner)
        
        # Simple dot product (replace with cosine similarity in production)
        similarity = 0.0
        for q, w in zip(query_embedding, winner.embedding):
            similarity += q * w
        
        return similarity
    
    def _keyword_similarity(
        self,
        query_embedding: list[float],
        winner: WinnerTemplate,
    ) -> float:
        """Fallback keyword-based similarity."""
        query_text = " ".join(str(q) for q in query_embedding)
        winner_text = winner.topic.lower()
        
        # Count matching words
        query_words = set(query_text.split())
        winner_words = set(winner_text.split())
        
        if not winner_words:
            return 0.0
        
        overlap = len(query_words & winner_words)
        return overlap / len(winner_words)
    
    def get_winner(self, project_id: str) -> Optional[WinnerTemplate]:
        """Get a specific winner by ID."""
        return self._winners.get(project_id)
    
    def list_winners(self, limit: int = 10) -> list[WinnerTemplate]:
        """List all winners, sorted by score."""
        winners = sorted(
            self._winners.values(),
            key=lambda w: w.score,
            reverse=True,
        )
        return winners[:limit]
    
    def count(self) -> int:
        """Get total number of winners."""
        return len(self._winners)
