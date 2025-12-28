#!/usr/bin/env python3
"""CLI entry point for video generation using the pipeline.

This script uses the VideoPipeline with configuration from config.yaml.
Providers are determined by config:
- LLM: config.llm.provider (default: mock)
- TTS: config.tts.provider (default: elevenlabs)
- Animation: Uses pre-rendered from animations/output/ if available

Usage:
    # Generate from the default inference document
    python generate_video.py

    # Generate from a specific document
    python generate_video.py --source path/to/document.md

    # Generate from an existing script
    python generate_video.py --script path/to/script.json

    # Run a quick test
    python generate_video.py --test
"""

import argparse
import sys
from pathlib import Path

from src.config import load_config
from src.pipeline import VideoPipeline


def main():
    parser = argparse.ArgumentParser(
        description="Generate explainer videos from technical documents."
    )
    parser.add_argument(
        "--source",
        type=str,
        default="/Users/prajwal/Desktop/Learning/inference/website/post.md",
        help="Path to source document (default: inference article)",
    )
    parser.add_argument(
        "--script",
        type=str,
        help="Path to existing script JSON (skips parsing/analysis)",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=180,
        help="Target video duration in seconds (default: 180)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="output",
        help="Output directory (default: output)",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run a quick test with minimal content",
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Path to config file (default: config.yaml)",
    )

    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config)

    print("=" * 60)
    print("Video Explainer Pipeline")
    print("=" * 60)
    print(f"LLM Provider:       {config.llm.provider}")
    print(f"TTS Provider:       {config.tts.provider}")
    print(f"Output Directory:   {args.output}")

    # Check for pre-rendered animation
    animation_path = Path("animations/output/project.mp4")
    if animation_path.exists():
        print(f"Animation:          Pre-rendered ({animation_path})")
    else:
        print("Animation:          Mock (no pre-render found)")

    print("=" * 60)

    # Initialize pipeline
    pipeline = VideoPipeline(config=config, output_dir=args.output)

    # Progress callback
    def on_progress(stage: str, progress: float):
        print(f"  [{stage}] {progress:.0f}%")

    pipeline.set_progress_callback(on_progress)

    # Run appropriate mode
    if args.test:
        print("\nRunning quick test...")
        print("-" * 40)
        result = pipeline.quick_test()

    elif args.script:
        print(f"\nGenerating from script: {args.script}")
        print("-" * 40)
        result = pipeline.generate_from_script(args.script)

    else:
        print(f"\nGenerating from document: {args.source}")
        print(f"Target duration: {args.duration}s")
        print("-" * 40)
        result = pipeline.generate_from_document(
            args.source,
            target_duration=args.duration,
        )

    print("-" * 40)

    # Display results
    if result.success:
        print("\n[SUCCESS] Video generated!")
        print(f"  Output:   {result.output_path}")
        print(f"  Duration: {result.duration_seconds:.1f}s")
        print(f"  Stages:   {', '.join(result.stages_completed)}")

        if result.metadata:
            print("\n  Metadata:")
            for key, value in result.metadata.items():
                print(f"    {key}: {value}")

        print(f"\n  Play with: open {result.output_path}")
    else:
        print("\n[FAILED] Video generation failed")
        print(f"  Error:  {result.error_message}")
        print(f"  Stages: {', '.join(result.stages_completed)}")
        return 1

    print("\n" + "=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
