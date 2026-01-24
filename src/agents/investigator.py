"""
The Investigator Agent - Researcher for evidence-based videos.

Takes visual descriptions from scripts and finds verified primary
source URLs. Filters out SEO spam, blog aggregators, and secondary sources
to locate the single source of truth for each factual claim.

Uses Exa.ai neural search for authoritative source discovery.
"""

import os
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from exa_py import Exa

from src.agents.base import BaseAgent

if TYPE_CHECKING:
    from src.models import ScriptScene, VideoProject


# Domains considered high-credibility primary sources
PRIMARY_SOURCE_DOMAINS = {
    # Official company/product domains (prioritized)
    "openai.com",
    "deepseek.com",
    "anthropic.com",
    "google.com",
    "microsoft.com",
    "apple.com",
    "amazon.com",
    "github.com",
    # News/journalism
    "reuters.com",
    "bbc.com",
    "nytimes.com",
    "wsj.com",
    "theverge.com",
    "arstechnica.com",
    "techcrunch.com",
    # Social (direct sources)
    "twitter.com",
    "x.com",
    "linkedin.com",
}

# Domains to deprioritize (secondary sources, aggregators)
SECONDARY_SOURCE_DOMAINS = {
    "medium.com",
    "substack.com",
    "reddit.com",
    "quora.com",
    "wikipedia.org",
    "youtube.com",
}


class Investigation:
    """
    Research results from the Investigator agent.

    Contains the verified primary source URL, fallback alternatives,
    and credibility assessment. Multiple URLs enable retry on capture failure.
    """

    def __init__(
        self,
        status: str = "pending",
        verified_url: str | None = None,
        fallback_urls: list[str] | None = None,
        source_title: str | None = None,
        credibility_score: float | None = None,
        error_message: str | None = None,
    ):
        self.status = status  # "found", "not_found", "error"
        self.verified_url = verified_url
        self.fallback_urls = fallback_urls or []
        self.source_title = source_title
        self.credibility_score = credibility_score
        self.error_message = error_message


class Investigator(BaseAgent):
    """
    Discovers and verifies primary source URLs for evidence claims.

    Uses Exa.ai neural search to find authoritative sources:
    official documentation, original news articles, direct social posts.
    Assigns credibility scores to each source.
    """

    def __init__(self, exa_api_key: str | None = None):
        """
        Initialize the Investigator agent.

        Args:
            exa_api_key: Exa.ai API key. Falls back to EXA_API_KEY env var.
        """
        api_key = exa_api_key or os.getenv("EXA_API_KEY", "")
        if not api_key:
            raise ValueError("EXA_API_KEY not configured")
        self._client = Exa(api_key=api_key)

    @property
    def name(self) -> str:
        return "Investigator"

    async def run(self, project: "VideoProject") -> "VideoProject":
        """
        Find verified URLs for scenes that need evidence.

        For each scene with needs_evidence=True, queries Exa.ai with the
        visual_description and selects the highest-credibility primary source.

        Args:
            project: Video project with script containing scenes.

        Returns:
            Project enriched with investigation results per scene.
        """
        if not project.script:
            self.log("No script found, skipping investigation")
            return project

        self.log("Sourcing primary evidence URLs...")

        for scene in project.script.scenes:
            # Check if scene needs evidence (has visual_cue with evidence type)
            if not self._scene_needs_evidence(scene):
                self.log(f"Scene {scene.scene_id}: Skipping (no evidence needed)")
                continue

            query = scene.visual_cue.description
            self.log(f"Scene {scene.scene_id}: Searching for '{query[:50]}...'")

            try:
                investigation = await self._search_and_verify(query)

                # Store investigation result in scene notes (temporary storage)
                # In extended models, this would be a proper field
                scene.notes = f"Investigation: {investigation.status}"
                if investigation.verified_url:
                    scene.notes += f" | URL: {investigation.verified_url}"
                    scene.notes += f" | Credibility: {investigation.credibility_score:.2f}"

                if investigation.status == "found":
                    self.log(
                        f"Scene {scene.scene_id}: Found {investigation.verified_url} "
                        f"(credibility: {investigation.credibility_score:.2f}, "
                        f"+{len(investigation.fallback_urls)} fallbacks)"
                    )
                else:
                    self.log(f"Scene {scene.scene_id}: {investigation.error_message}")

            except Exception as e:
                self.log(f"Scene {scene.scene_id}: ERROR - {e}")

        self.log("Source verification complete.")
        return project

    def _scene_needs_evidence(self, scene: "ScriptScene") -> bool:
        """Check if a scene requires evidence capture."""
        # Evidence needed for visual types that reference external sources
        evidence_types = {"screenshot", "static_highlight", "scroll_highlight", "dom_crop"}
        return scene.visual_cue.visual_type.lower() in evidence_types

    async def _search_and_verify(self, query: str) -> Investigation:
        """
        Search Exa.ai and return top 3 primary sources for retry resilience.

        Returns the best URL as verified_url, with 2 fallback alternatives.
        If capture fails on the primary URL, the orchestrator can retry with fallbacks.
        """
        # Exa.ai search - synchronous SDK, but fast enough for our use
        results = self._client.search(
            query=query,
            num_results=10,
            type="auto",
        )

        if not results.results:
            return Investigation(
                status="not_found",
                error_message="No results found for query",
            )

        # Score and rank results by credibility
        scored_results = []
        for i, result in enumerate(results.results):
            score = self._calculate_credibility(result.url, rank=i)
            scored_results.append((result, score))

        # Sort by credibility score descending
        scored_results.sort(key=lambda x: x[1], reverse=True)

        # Take top 3 results: best as primary, rest as fallbacks
        best_result, best_score = scored_results[0]
        fallback_urls = [r.url for r, _ in scored_results[1:3]]  # Next 2 best URLs

        return Investigation(
            status="found",
            verified_url=best_result.url,
            fallback_urls=fallback_urls,
            source_title=best_result.title,
            credibility_score=best_score,
        )

    def _calculate_credibility(self, url: str, rank: int) -> float:
        """
        Calculate a credibility score for a URL.

        Factors:
        - Domain authority (primary vs secondary source)
        - Search rank (higher rank = more relevant)
        """
        # Base score from rank (0.5 to 1.0 for top 10)
        rank_score = 1.0 - (rank * 0.05)

        # Extract domain
        domain = urlparse(url).netloc.replace("www.", "")

        # Boost for primary sources
        if domain in PRIMARY_SOURCE_DOMAINS:
            domain_score = 1.0
        elif domain in SECONDARY_SOURCE_DOMAINS:
            domain_score = 0.5
        else:
            # Unknown domain - moderate score
            domain_score = 0.7

        # Check if it's an official/docs subdomain (high trust)
        if any(sub in url for sub in ["/docs", "/pricing", "/api", "/blog"]):
            domain_score = min(1.0, domain_score + 0.1)

        # Weighted combination
        final_score = (rank_score * 0.3) + (domain_score * 0.7)
        return round(final_score, 2)

    async def search_urls(self, query: str) -> Investigation:
        """
        Public method to search for URLs without full pipeline context.

        Useful for standalone URL discovery or testing.
        """
        return await self._search_and_verify(query)
