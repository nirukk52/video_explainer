"""fal.ai video generation for text-to-video.

This module integrates with fal.ai's API to generate videos from text prompts only.
No input image required - perfect for generating AI backgrounds for video shorts.

Supported models:
- fal-ai/veo3: High quality Google Veo3, $0.20/sec (no audio) or $0.40/sec (with audio)
- fal-ai/veo3/fast: Cost-effective Veo3, $0.10/sec (no audio) or $0.15/sec (with audio)
- fal-ai/kling-video/v1.5/pro/text-to-video: Kling 1.5 Pro, $0.10/sec, supports 1:1 aspect ratio
"""

import asyncio
import os
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Literal

import httpx


class AspectRatio(str, Enum):
    """Supported aspect ratios for video generation."""
    LANDSCAPE = "16:9"  # 1920x1080 or 1280x720
    PORTRAIT = "9:16"   # 1080x1920 or 720x1280 (for shorts)
    SQUARE = "1:1"      # 1080x1080 (Kling only)


class Duration(str, Enum):
    """Supported video durations."""
    SHORT = "4s"
    FIVE = "5"      # Kling uses "5" not "5s"
    MEDIUM = "6s"  
    LONG = "8s"
    TEN = "10"      # Kling uses "10" not "10s"


class Resolution(str, Enum):
    """Supported video resolutions."""
    HD = "720p"
    FULL_HD = "1080p"


@dataclass
class FalVideoConfig:
    """Configuration for fal.ai video generation."""
    
    model: str = "fal-ai/veo3/fast"  # or "fal-ai/veo3" for higher quality
    aspect_ratio: AspectRatio = AspectRatio.PORTRAIT  # 9:16 for shorts
    duration: Duration = Duration.MEDIUM  # 6 seconds
    resolution: Resolution = Resolution.FULL_HD  # 1080p
    generate_audio: bool = False  # Set to True for audio
    seed: int | None = None  # For reproducibility


@dataclass
class FalVideoResult:
    """Result of fal.ai video generation."""
    
    video_path: Path
    video_url: str
    duration_seconds: int
    prompt: str
    model: str
    request_id: str
    generation_time_seconds: float = 0.0


class FalVideoGenerator:
    """Generator for AI videos using fal.ai Veo3 API.
    
    Supports pure text-to-video generation - no input image required.
    Ideal for creating backgrounds, b-roll, and visual content for shorts.
    """
    
    BASE_URL = "https://queue.fal.run"
    
    # Model pricing per second
    PRICING = {
        "fal-ai/veo3": {"no_audio": 0.50, "with_audio": 0.75},
        "fal-ai/veo3/fast": {"no_audio": 0.25, "with_audio": 0.40},
        "fal-ai/kling-video/v1.5/pro/text-to-video": {"no_audio": 0.10, "with_audio": 0.10},
    }
    
    # Models that support different aspect ratios
    SUPPORTED_ASPECT_RATIOS = {
        "fal-ai/veo3": ["16:9"],
        "fal-ai/veo3/fast": ["16:9"],
        "fal-ai/kling-video/v1.5/pro/text-to-video": ["16:9", "9:16", "1:1"],
    }
    
    def __init__(self, api_key: str | None = None, config: FalVideoConfig | None = None):
        """Initialize fal.ai video generator.
        
        Args:
            api_key: fal.ai API key (defaults to FAL_KEY env var)
            config: Generation configuration
        """
        self.api_key = api_key or os.environ.get("FAL_KEY")
        if not self.api_key:
            raise ValueError(
                "fal.ai API key required. Set FAL_KEY environment variable "
                "or pass api_key parameter."
            )
        self.config = config or FalVideoConfig()
    
    def _get_headers(self) -> dict[str, str]:
        """Get request headers for fal.ai API."""
        return {
            "Authorization": f"Key {self.api_key}",
            "Content-Type": "application/json",
        }
    
    async def generate(
        self,
        prompt: str,
        output_path: str | Path,
        negative_prompt: str | None = None,
        aspect_ratio: AspectRatio | None = None,
        duration: Duration | None = None,
        resolution: Resolution | None = None,
        generate_audio: bool | None = None,
        model: str | None = None,
        seed: int | None = None,
    ) -> FalVideoResult:
        """Generate video from text prompt.
        
        Args:
            prompt: Text description of the video to generate
            output_path: Path to save the generated video
            negative_prompt: What to avoid in the video
            aspect_ratio: Video aspect ratio (16:9 or 9:16)
            duration: Video duration (4s, 6s, or 8s)
            resolution: Video resolution (720p or 1080p)
            generate_audio: Whether to generate audio
            model: fal.ai model to use
            seed: Random seed for reproducibility
            
        Returns:
            FalVideoResult with video path and metadata
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Use config defaults if not specified
        model = model or self.config.model
        aspect_ratio = aspect_ratio or self.config.aspect_ratio
        duration = duration or self.config.duration
        resolution = resolution or self.config.resolution
        generate_audio = generate_audio if generate_audio is not None else self.config.generate_audio
        seed = seed if seed is not None else self.config.seed
        
        # Submit generation request
        start_time = time.time()
        request_id = await self._submit_request(
            prompt=prompt,
            negative_prompt=negative_prompt,
            aspect_ratio=aspect_ratio.value if isinstance(aspect_ratio, AspectRatio) else aspect_ratio,
            duration=duration.value if isinstance(duration, Duration) else duration,
            resolution=resolution.value if isinstance(resolution, Resolution) else resolution,
            generate_audio=generate_audio,
            model=model,
            seed=seed,
        )
        
        # Poll for completion
        video_url = await self._wait_for_completion(model, request_id)
        
        # Download video
        await self._download_video(video_url, output_path)
        
        generation_time = time.time() - start_time
        
        # Parse duration to seconds
        duration_seconds = int(duration.value.replace("s", "") if isinstance(duration, Duration) else duration.replace("s", ""))
        
        return FalVideoResult(
            video_path=output_path,
            video_url=video_url,
            duration_seconds=duration_seconds,
            prompt=prompt,
            model=model,
            request_id=request_id,
            generation_time_seconds=generation_time,
        )
    
    async def _submit_request(
        self,
        prompt: str,
        negative_prompt: str | None,
        aspect_ratio: str,
        duration: str,
        resolution: str,
        generate_audio: bool,
        model: str,
        seed: int | None,
    ) -> str:
        """Submit video generation request to fal.ai queue.
        
        Returns:
            Request ID for polling
        """
        url = f"{self.BASE_URL}/{model}"
        
        # Build payload based on model type
        if "kling" in model:
            # Kling uses different payload structure
            payload = {
                "prompt": prompt,
                "aspect_ratio": aspect_ratio,
                "duration": duration.replace("s", ""),  # Kling uses "5" not "5s"
            }
            if negative_prompt:
                payload["negative_prompt"] = negative_prompt
        else:
            # Veo3 payload
            payload = {
                "prompt": prompt,
                "aspect_ratio": aspect_ratio,
                "duration": duration,
                "resolution": resolution,
                "generate_audio": generate_audio,
                "auto_fix": True,  # Auto-fix prompts that fail validation
            }
            
            if negative_prompt:
                payload["negative_prompt"] = negative_prompt
            
            if seed is not None:
                payload["seed"] = seed
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                url,
                headers=self._get_headers(),
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        
        return data["request_id"]
    
    async def _wait_for_completion(
        self,
        model: str,
        request_id: str,
        max_wait_seconds: int = 600,
        poll_interval: float = 5.0,
    ) -> str:
        """Poll for task completion and return video URL.
        
        Args:
            model: The model ID
            request_id: The request ID to poll
            max_wait_seconds: Maximum time to wait
            poll_interval: Seconds between polls
            
        Returns:
            URL of the generated video
            
        Raises:
            TimeoutError: If task doesn't complete in time
            RuntimeError: If task fails
        """
        # For all fal.ai models, use the base model path (first 2 segments)
        # e.g., fal-ai/veo3/fast -> fal-ai/veo3
        # e.g., fal-ai/kling-video/v1.5/pro/text-to-video -> fal-ai/kling-video
        parts = model.split("/")
        base_model = "/".join(parts[:2])  # fal-ai/veo3 or fal-ai/kling-video
        status_url = f"{self.BASE_URL}/{base_model}/requests/{request_id}/status"
        result_url = f"{self.BASE_URL}/{base_model}/requests/{request_id}"
        elapsed = 0
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            while elapsed < max_wait_seconds:
                # Check status with auth headers
                response = await client.get(
                    status_url, 
                    headers=self._get_headers(),
                    params={"logs": "1"}
                )
                response.raise_for_status()
                data = response.json()
                
                status = data.get("status")
                
                if status == "COMPLETED":
                    # Fetch the result with auth headers
                    result_response = await client.get(
                        result_url, 
                        headers=self._get_headers()
                    )
                    result_response.raise_for_status()
                    result_data = result_response.json()
                    
                    video = result_data.get("video", {})
                    video_url = video.get("url")
                    
                    if video_url:
                        return video_url
                    raise RuntimeError(f"Task completed but no video URL found. Response: {result_data}")
                
                elif status == "FAILED":
                    error = data.get("error", "Unknown error")
                    raise RuntimeError(f"fal.ai generation failed: {error}")
                
                elif status in ("IN_QUEUE", "IN_PROGRESS"):
                    # Log progress if available
                    logs = data.get("logs", [])
                    if logs:
                        last_log = logs[-1].get('message', '')
                        print(f"  Status: {status} | {last_log}")
                    else:
                        queue_pos = data.get("queue_position", "?")
                        print(f"  Status: {status} | Queue position: {queue_pos}")
                    
                    await asyncio.sleep(poll_interval)
                    elapsed += poll_interval
                else:
                    raise RuntimeError(f"Unknown task status: {status}")
        
        raise TimeoutError(
            f"fal.ai generation timed out after {max_wait_seconds} seconds"
        )
    
    async def _download_video(self, video_url: str, output_path: Path) -> None:
        """Download video from URL to local path."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.get(video_url)
            response.raise_for_status()
            
            with open(output_path, "wb") as f:
                f.write(response.content)
    
    def generate_sync(
        self,
        prompt: str,
        output_path: str | Path,
        **kwargs,
    ) -> FalVideoResult:
        """Synchronous wrapper for generate.
        
        Args:
            prompt: Text description of the video
            output_path: Path to save the video
            **kwargs: Additional arguments passed to generate
            
        Returns:
            FalVideoResult with video path and metadata
        """
        return asyncio.run(self.generate(prompt, output_path, **kwargs))
    
    def estimate_cost(
        self,
        duration: Duration | str = Duration.MEDIUM,
        generate_audio: bool = False,
        model: str | None = None,
    ) -> float:
        """Estimate generation cost.
        
        Args:
            duration: Video duration
            generate_audio: Whether audio is enabled
            model: Model to use (defaults to config model)
            
        Returns:
            Estimated cost in USD
        """
        model = model or self.config.model
        
        # Parse duration to seconds
        if isinstance(duration, Duration):
            seconds = int(duration.value.replace("s", ""))
        else:
            seconds = int(str(duration).replace("s", ""))
        
        # Get pricing
        pricing = self.PRICING.get(model, self.PRICING["fal-ai/veo3/fast"])
        rate = pricing["with_audio"] if generate_audio else pricing["no_audio"]
        
        return seconds * rate
    
    @staticmethod
    def get_optimal_prompt(
        narration: str,
        context: str = "",
        style: str = "cinematic",
    ) -> str:
        """Generate an optimal video prompt from narration text.
        
        Based on fal.ai's prompting guide for Veo3.
        
        Args:
            narration: The voiceover text for this segment
            context: Additional context about the video topic
            style: Visual style (cinematic, documentary, dramatic, tech)
            
        Returns:
            Optimized prompt for fal.ai video generation
        """
        # Style descriptors optimized for Veo3
        style_map = {
            "cinematic": "Cinematic film quality, dramatic lighting, smooth camera movement, professional cinematography",
            "documentary": "Documentary style, realistic lighting, observational camera, natural environment",
            "dramatic": "High contrast, dramatic angles, intense atmosphere, moody lighting",
            "tech": "Futuristic technology aesthetic, clean lines, neon accents, sci-fi atmosphere",
            "news": "News broadcast style, professional studio lighting, clean composition",
        }
        
        style_desc = style_map.get(style, style_map["cinematic"])
        
        # Build prompt following Veo3 best practices:
        # Subject, Context, Action, Style, Camera motion, Composition, Ambiance
        prompt_parts = []
        
        # Style and quality
        prompt_parts.append(style_desc)
        
        # Subject and action from narration
        prompt_parts.append(f"Visual depicting: {narration[:300]}")
        
        # Context if provided
        if context:
            prompt_parts.append(f"Setting: {context[:200]}")
        
        # Camera and technical
        prompt_parts.append("Smooth steady camera movement")
        prompt_parts.append("4K ultra high definition quality")
        
        return ". ".join(prompt_parts)


def get_video_generator(api_key: str | None = None) -> FalVideoGenerator:
    """Factory function to get a video generator instance.
    
    Args:
        api_key: Optional API key (defaults to FAL_KEY env var)
        
    Returns:
        Configured FalVideoGenerator instance
    """
    return FalVideoGenerator(api_key=api_key)
