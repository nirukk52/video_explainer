#!/usr/bin/env python3
"""Script to generate AI video using fal.ai API.

This script reads the ai_video_config.json from a project's backgrounds folder
and generates the AI video using fal.ai's text-to-video API.

No input image required - pure text-to-video generation!

Supports multiple models:
    - fal-ai/veo3: High quality Google Veo3
    - fal-ai/veo3/fast: Cost-effective Veo3
    - fal-ai/kling-video/v1.5/pro/text-to-video: Kling 1.5 Pro (supports 1:1 aspect ratio)

Prerequisites:
    - FAL_KEY environment variable set

Usage:
    python scripts/generate_ai_video.py projects/first-draft
    python scripts/generate_ai_video.py projects/first-draft --scene scene_001
    python scripts/generate_ai_video.py projects/first-draft --dry-run
    python scripts/generate_ai_video.py projects/first-draft --model fal-ai/kling-video/v1.5/pro/text-to-video
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from video_gen import FalVideoGenerator, FalVideoConfig, AspectRatio, Duration, Resolution


def load_config(project_path: Path) -> dict:
    """Load the AI video configuration from the project."""
    config_path = project_path / "backgrounds" / "ai_video_config.json"
    
    if not config_path.exists():
        raise FileNotFoundError(f"AI video config not found: {config_path}")
    
    with open(config_path) as f:
        return json.load(f)


async def generate_video(
    project_path: Path,
    scene_id: str = "scene_001",
    model: str | None = None,
    dry_run: bool = False,
) -> Path:
    """Generate AI video for a scene.
    
    Args:
        project_path: Path to the project directory
        scene_id: ID of the scene to generate video for
        model: fal.ai model to use
        dry_run: If True, just print what would be done
        
    Returns:
        Path to the generated video
    """
    config = load_config(project_path)
    
    # Support both old (word_group_001) and new (scene_001) config formats
    scene_config = config.get(scene_id) or config.get(f"word_group_{scene_id.split('_')[-1]}")
    if not scene_config:
        # List available scenes
        available = [k for k in config.keys() if not k.startswith("_")]
        raise ValueError(f"Scene '{scene_id}' not found. Available: {available}")
    
    prompt = scene_config["prompt"]["main"]
    # Include context in prompt if available
    prompt_context = scene_config["prompt"].get("context", "")
    if prompt_context:
        prompt = f"{prompt}\n\nContext: {prompt_context}"
    
    gen_config = scene_config.get("generation", {})
    output_filename = scene_config["output"]["filename"]
    output_path = project_path / "backgrounds" / output_filename
    
    # Get aspect ratio - support "1:1" for Kling
    aspect_ratio = gen_config.get("aspect_ratio", "9:16")
    
    # Get duration - Kling uses "5" or "10", others use "5s", "6s", etc.
    duration = gen_config.get("duration", "5")
    if isinstance(duration, int):
        duration = str(duration)
    
    resolution = gen_config.get("resolution", "1080p")
    generate_audio = gen_config.get("generate_audio", False)
    negative_prompt = gen_config.get("negative_prompt", "")
    seed = gen_config.get("seed")
    
    # Model from config or override
    model = model or gen_config.get("model", "fal-ai/kling-video/v1.5/pro/text-to-video")
    
    # Detect model type for display
    model_name = "Kling 1.5 Pro" if "kling" in model else "Google Veo3"
    
    print(f"Scene: {scene_id}")
    print(f"Narration: {scene_config['narration']}")
    timing = scene_config.get("timing", {})
    print(f"Timing: {timing.get('start_seconds', 0)}s - {timing.get('end_seconds', '?')}s")
    print()
    print(f"=== {model_name} Configuration ===")
    print(f"Model: {model}")
    print(f"Aspect Ratio: {aspect_ratio}")
    print(f"Duration: {duration}s")
    print(f"Resolution: {resolution}")
    if negative_prompt:
        print(f"Negative: {negative_prompt[:50]}...")
    print()
    print(f"Prompt: {prompt[:200]}...")
    print(f"Output: {output_path}")
    
    # Estimate cost
    pricing = {
        "fal-ai/veo3": {"no_audio": 0.50, "with_audio": 0.75},
        "fal-ai/veo3/fast": {"no_audio": 0.25, "with_audio": 0.40},
        "fal-ai/kling-video/v1.5/pro/text-to-video": {"no_audio": 0.10, "with_audio": 0.10},
    }
    duration_seconds = int(duration.replace("s", ""))
    rate = pricing.get(model, {"no_audio": 0.10})["with_audio" if generate_audio else "no_audio"]
    cost = duration_seconds * rate
    print(f"\nEstimated cost: ${cost:.2f}")
    
    if dry_run:
        print("\n[DRY RUN] Would generate video with above settings")
        return output_path
    
    # Check for API key
    if not os.environ.get("FAL_KEY"):
        print("\n⚠️  FAL_KEY environment variable not set!")
        print("Set it with: export FAL_KEY='your-api-key'")
        print("\nGet your API key from: https://fal.ai/dashboard/keys")
        return None
    
    # Map aspect ratio string to enum value
    ar_map = {"16:9": AspectRatio.LANDSCAPE, "9:16": AspectRatio.PORTRAIT, "1:1": AspectRatio.SQUARE}
    aspect_enum = ar_map.get(aspect_ratio, AspectRatio.SQUARE)
    
    # Map duration - handle both "5" and "5s" formats
    dur_normalized = duration.replace("s", "")
    dur_map = {"4": Duration.SHORT, "5": Duration.FIVE, "6": Duration.MEDIUM, "8": Duration.LONG, "10": Duration.TEN}
    dur_enum = dur_map.get(dur_normalized, Duration.FIVE)
    
    # Initialize generator
    generator_config = FalVideoConfig(
        model=model,
        aspect_ratio=aspect_enum,
        duration=dur_enum,
        resolution=Resolution(resolution) if resolution in ("720p", "1080p") else Resolution.FULL_HD,
        generate_audio=generate_audio,
        seed=seed,
    )
    
    generator = FalVideoGenerator(config=generator_config)
    
    print(f"\n🎬 Generating video with {model_name}...")
    print("   This may take 2-6 minutes...")
    
    result = await generator.generate(
        prompt=prompt,
        output_path=output_path,
        negative_prompt=negative_prompt if negative_prompt else None,
        aspect_ratio=aspect_enum,
        duration=dur_enum,
        resolution=Resolution(resolution) if resolution in ("720p", "1080p") else Resolution.FULL_HD,
        generate_audio=generate_audio,
        model=model,
        seed=seed,
    )
    
    print(f"\n✅ Video generated successfully!")
    print(f"   Path: {result.video_path}")
    print(f"   Duration: {result.duration_seconds}s")
    print(f"   Generation time: {result.generation_time_seconds:.1f}s")
    print(f"   Request ID: {result.request_id}")
    
    return result.video_path


def main():
    parser = argparse.ArgumentParser(
        description="Generate AI video using fal.ai API"
    )
    parser.add_argument(
        "project_path",
        type=Path,
        help="Path to the project directory (e.g., projects/first-draft)",
    )
    parser.add_argument(
        "--scene",
        default="scene_001",
        help="Scene ID to generate video for (default: scene_001)",
    )
    parser.add_argument(
        "--model",
        help="fal.ai model to use (e.g., fal-ai/kling-video/v1.5/pro/text-to-video)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print configuration without generating video",
    )
    
    args = parser.parse_args()
    
    # Resolve project path relative to script location if needed
    project_path = args.project_path
    if not project_path.is_absolute():
        # Try relative to current directory first
        if not project_path.exists():
            # Try relative to project root
            project_path = Path(__file__).parent.parent / project_path
    
    if not project_path.exists():
        print(f"Error: Project path not found: {args.project_path}")
        sys.exit(1)
    
    print(f"Project: {project_path}")
    print("=" * 60)
    
    try:
        result = asyncio.run(
            generate_video(
                project_path=project_path,
                scene_id=args.scene,
                model=args.model,
                dry_run=args.dry_run,
            )
        )
        
        if result is None:
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
