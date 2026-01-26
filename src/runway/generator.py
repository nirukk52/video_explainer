"""Runway AI video generation for creating dynamic backgrounds.

This module integrates with Runway's API to generate AI videos from images and prompts.
Videos are used as backgrounds in SplitProof and other templates.
"""

import asyncio
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import httpx


@dataclass
class RunwayResult:
    """Result of Runway video generation."""

    video_path: Path
    duration_seconds: float
    prompt: str
    model: str
    task_id: str
    generation_time_seconds: float = 0.0


@dataclass
class RunwayConfig:
    """Configuration for Runway video generation."""

    model: str = "gen3a_turbo"
    duration: int = 5  # 2-10 seconds
    ratio: str = "720:1280"  # Vertical for shorts (width:height)
    seed: int | None = None  # For reproducibility


class RunwayGenerator:
    """Generator for AI videos using Runway API.

    Runway's API generates videos from images + text prompts.
    For pure text-to-video, first generate a reference frame image.
    """

    BASE_URL = "https://api.dev.runwayml.com/v1"
    API_VERSION = "2024-11-06"

    # Available models
    MODELS = {
        "gen3a_turbo": "Fast generation, good quality",
        "gen4_turbo": "Latest model, highest quality",
    }

    def __init__(self, api_key: str | None = None, config: RunwayConfig | None = None):
        """Initialize Runway generator.

        Args:
            api_key: Runway API key (defaults to RUNWAY_API_KEY env var)
            config: Generation configuration
        """
        self.api_key = api_key or os.environ.get("RUNWAY_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Runway API key required. Set RUNWAY_API_KEY environment variable "
                "or pass api_key parameter."
            )
        self.config = config or RunwayConfig()

    def _get_headers(self) -> dict[str, str]:
        """Get request headers for Runway API."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "X-Runway-Version": self.API_VERSION,
            "Content-Type": "application/json",
        }

    async def generate_from_image(
        self,
        prompt: str,
        image_url: str,
        output_path: str | Path,
        duration: int | None = None,
        model: str | None = None,
        ratio: str | None = None,
    ) -> RunwayResult:
        """Generate video from an image and text prompt.

        Args:
            prompt: Text description of desired video motion/content
            image_url: HTTPS URL to the starting image
            output_path: Path to save the generated video
            duration: Video duration in seconds (2-10)
            model: Model to use (gen3a_turbo, gen4_turbo)
            ratio: Aspect ratio as width:height

        Returns:
            RunwayResult with video path and metadata
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        duration = duration or self.config.duration
        model = model or self.config.model
        ratio = ratio or self.config.ratio

        # Create generation task
        start_time = time.time()
        task_id = await self._create_task(prompt, image_url, duration, model, ratio)

        # Poll for completion
        video_url = await self._wait_for_completion(task_id)

        # Download video
        await self._download_video(video_url, output_path)

        generation_time = time.time() - start_time

        return RunwayResult(
            video_path=output_path,
            duration_seconds=duration,
            prompt=prompt,
            model=model,
            task_id=task_id,
            generation_time_seconds=generation_time,
        )

    async def _create_task(
        self,
        prompt: str,
        image_url: str,
        duration: int,
        model: str,
        ratio: str,
    ) -> str:
        """Create a video generation task.

        Returns:
            Task ID for polling
        """
        url = f"{self.BASE_URL}/image_to_video"

        payload = {
            "model": model,
            "promptImage": image_url,
            "promptText": prompt[:1000],  # Max 1000 chars
            "ratio": ratio,
            "duration": duration,
        }

        if self.config.seed is not None:
            payload["seed"] = self.config.seed

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                url,
                headers=self._get_headers(),
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        return data["id"]

    async def _wait_for_completion(
        self,
        task_id: str,
        max_wait_seconds: int = 600,
        poll_interval: float = 5.0,
    ) -> str:
        """Poll for task completion and return video URL.

        Args:
            task_id: The task ID to poll
            max_wait_seconds: Maximum time to wait
            poll_interval: Seconds between polls

        Returns:
            URL of the generated video

        Raises:
            TimeoutError: If task doesn't complete in time
            RuntimeError: If task fails
        """
        url = f"{self.BASE_URL}/tasks/{task_id}"
        elapsed = 0

        async with httpx.AsyncClient(timeout=30.0) as client:
            while elapsed < max_wait_seconds:
                response = await client.get(url, headers=self._get_headers())
                response.raise_for_status()
                data = response.json()

                status = data.get("status")

                if status == "SUCCEEDED":
                    # Video URL is in the output
                    output = data.get("output", [])
                    if output:
                        return output[0]
                    raise RuntimeError("Task succeeded but no output URL found")

                elif status == "FAILED":
                    error = data.get("failure", "Unknown error")
                    raise RuntimeError(f"Runway generation failed: {error}")

                elif status in ("PENDING", "RUNNING"):
                    await asyncio.sleep(poll_interval)
                    elapsed += poll_interval
                else:
                    raise RuntimeError(f"Unknown task status: {status}")

        raise TimeoutError(
            f"Runway generation timed out after {max_wait_seconds} seconds"
        )

    async def _download_video(self, video_url: str, output_path: Path) -> None:
        """Download video from URL to local path."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.get(video_url)
            response.raise_for_status()

            with open(output_path, "wb") as f:
                f.write(response.content)

    def generate_from_image_sync(
        self,
        prompt: str,
        image_url: str,
        output_path: str | Path,
        **kwargs,
    ) -> RunwayResult:
        """Synchronous wrapper for generate_from_image.

        Args:
            prompt: Text description of desired video motion/content
            image_url: HTTPS URL to the starting image
            output_path: Path to save the generated video
            **kwargs: Additional arguments passed to generate_from_image

        Returns:
            RunwayResult with video path and metadata
        """
        return asyncio.run(
            self.generate_from_image(prompt, image_url, output_path, **kwargs)
        )

    def estimate_cost(self, duration: int = 5) -> dict[str, float]:
        """Estimate generation cost.

        Runway pricing (approximate, varies by plan):
        - Gen-3 Turbo: ~$0.05 per second
        - Gen-4 Turbo: ~$0.10 per second

        Args:
            duration: Video duration in seconds

        Returns:
            Dict with cost estimates per model
        """
        return {
            "gen3a_turbo": duration * 0.05,
            "gen4_turbo": duration * 0.10,
        }

    @staticmethod
    def get_optimal_prompt(
        narration: str,
        context: str = "",
        style: str = "cinematic",
    ) -> str:
        """Generate an optimal video prompt from narration text.

        This creates a prompt designed for Runway that describes the
        visual motion and style rather than just the content.

        Args:
            narration: The voiceover text for this segment
            context: Additional context about the video topic
            style: Visual style (cinematic, documentary, dramatic)

        Returns:
            Optimized prompt for Runway video generation
        """
        # Base style descriptors
        style_map = {
            "cinematic": "Cinematic quality, dramatic lighting, smooth camera movement",
            "documentary": "Documentary style, realistic, observational camera",
            "dramatic": "High contrast, dramatic angles, intense atmosphere",
            "tech": "Futuristic, clean lines, tech-forward aesthetic",
        }

        style_desc = style_map.get(style, style_map["cinematic"])

        # Build prompt focusing on motion and visuals
        prompt_parts = [
            style_desc,
            f"Visual representation of: {narration[:200]}",
        ]

        if context:
            prompt_parts.append(f"Context: {context[:200]}")

        prompt_parts.extend([
            "Smooth motion",
            "4K quality",
            "Professional production value",
        ])

        return ". ".join(prompt_parts)


def get_runway_generator(api_key: str | None = None) -> RunwayGenerator:
    """Factory function to get a Runway generator instance.

    Args:
        api_key: Optional API key (defaults to env var)

    Returns:
        Configured RunwayGenerator instance
    """
    return RunwayGenerator(api_key=api_key)
