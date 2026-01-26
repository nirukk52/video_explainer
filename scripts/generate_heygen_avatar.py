#!/usr/bin/env python3
"""Generate HeyGen avatar video with lip-sync.

This script generates a lip-synced avatar video using HeyGen's V2 API.
Supports two modes:
1. Text input with built-in TTS (HeyGen handles voice generation)
2. Audio URL input for pre-recorded audio

Usage:
    # Text mode (HeyGen TTS):
    python scripts/generate_heygen_avatar.py --text "Your text here" --voice-id VOICE_ID --output path/to/output.mp4
    
    # Audio URL mode:
    python scripts/generate_heygen_avatar.py --audio-url URL --output path/to/output.mp4
    
    # With motion prompt:
    python scripts/generate_heygen_avatar.py --text "Your text" --voice-id VOICE_ID --output out.mp4 --motion-prompt "Talking naturally"
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import httpx


# Predefined aspect ratio dimensions (HeyGen supported resolutions)
ASPECT_RATIOS = {
    "9:16": (1080, 1920),   # Vertical/portrait - default for shorts
    "16:9": (1920, 1080),   # Horizontal/landscape  
    "1:1": (1080, 1080),    # Square
}


def generate_avatar_video(
    avatar_id: str,
    output_path: Path,
    audio_url: str | None = None,
    text: str | None = None,
    voice_id: str | None = None,
    width: int = 1080,
    height: int = 1920,
    motion_prompt: str | None = None,
    api_key: str | None = None,
) -> Path:
    """Generate avatar video with lip-sync.
    
    Supports two modes:
    1. Text + voice_id: HeyGen generates TTS and lip-sync
    2. audio_url: Use pre-recorded audio for lip-sync
    
    Args:
        avatar_id: HeyGen avatar ID
        output_path: Path to save the video
        audio_url: Public URL to the audio file (mode 2)
        text: Text for HeyGen to speak (mode 1)
        voice_id: HeyGen voice ID for TTS (required for mode 1)
        width: Video width
        height: Video height
        motion_prompt: Optional motion/animation instructions for natural movement
        api_key: HeyGen API key
        
    Returns:
        Path to the generated video
    """
    # Validate inputs
    if text and audio_url:
        raise ValueError("Cannot specify both --text and --audio-url")
    if not text and not audio_url:
        raise ValueError("Must specify either --text or --audio-url")
    if text and not voice_id:
        raise ValueError("--voice-id required when using --text")
    
    api_key = api_key or os.environ.get("HEYGEN_API_KEY")
    if not api_key:
        raise ValueError("HEYGEN_API_KEY environment variable required")
    
    headers = {
        "X-Api-Key": api_key,
        "Content-Type": "application/json"
    }
    
    # Build character config with optional motion prompt
    character_config = {
        "type": "avatar",
        "avatar_id": avatar_id,
        "avatar_style": "normal"
    }
    
    # Add motion prompt for natural animation if provided
    if motion_prompt:
        character_config["motion_prompt"] = motion_prompt
    
    # Build voice config based on mode
    if text:
        voice_config = {
            "type": "text",
            "input_text": text,
            "voice_id": voice_id
        }
    else:
        voice_config = {
            "type": "audio",
            "audio_url": audio_url
        }
    
    # Create video generation request
    payload = {
        "video_inputs": [{
            "character": character_config,
            "voice": voice_config
        }],
        "dimension": {
            "width": width,
            "height": height
        }
    }
    
    print(f"Creating avatar video...")
    print(f"  Avatar ID: {avatar_id}")
    if text:
        print(f"  Text: {text}")
        print(f"  Voice ID: {voice_id}")
    else:
        print(f"  Audio URL: {audio_url}")
    print(f"  Dimensions: {width}x{height}")
    if motion_prompt:
        print(f"  Motion prompt: {motion_prompt}")
    
    with httpx.Client(timeout=60.0) as client:
        # Submit video generation request
        response = client.post(
            "https://api.heygen.com/v2/video/generate",
            headers=headers,
            json=payload
        )
        
        if response.status_code != 200:
            print(f"Error: {response.status_code}")
            print(response.text)
            return None
            
        data = response.json()
        
        if data.get("error"):
            print(f"API Error: {data['error']}")
            return None
            
        video_id = data.get("data", {}).get("video_id")
        if not video_id:
            print(f"No video_id in response: {data}")
            return None
            
        print(f"  Video ID: {video_id}")
        print(f"  Waiting for generation...")
        
        # Poll for completion
        max_wait = 300  # 5 minutes
        poll_interval = 5
        elapsed = 0
        
        while elapsed < max_wait:
            status_response = client.get(
                f"https://api.heygen.com/v1/video_status.get?video_id={video_id}",
                headers=headers
            )
            
            status_data = status_response.json()
            status = status_data.get("data", {}).get("status")
            
            if status == "completed":
                video_url = status_data.get("data", {}).get("video_url")
                print(f"  Video completed!")
                print(f"  Downloading...")
                
                # Download video
                video_response = client.get(video_url)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(video_response.content)
                    
                print(f"  Saved to: {output_path}")
                return output_path
                
            elif status == "failed":
                error = status_data.get("data", {}).get("error")
                print(f"  Generation failed: {error}")
                return None
                
            else:
                print(f"  Status: {status} ({elapsed}s)")
                time.sleep(poll_interval)
                elapsed += poll_interval
        
        print(f"  Timeout after {max_wait}s")
        return None


def main():
    parser = argparse.ArgumentParser(description="Generate HeyGen avatar video with lip-sync")
    
    # Input mode: either text+voice_id OR audio_url
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--text", help="Text for HeyGen to speak (uses built-in TTS)")
    input_group.add_argument("--audio-url", help="Public URL to audio file")
    
    parser.add_argument("--voice-id", help="HeyGen voice ID (required with --text)")
    parser.add_argument("--avatar-id", default="a247c0b271f0447088bac6043903cf16", help="HeyGen avatar ID")
    parser.add_argument("--output", required=True, type=Path, help="Output video path")
    parser.add_argument("--width", type=int, default=1280, help="Video width (ignored if --aspect-ratio set)")
    parser.add_argument("--height", type=int, default=720, help="Video height (ignored if --aspect-ratio set)")
    parser.add_argument("--aspect-ratio", choices=["9:16", "16:9", "1:1"], 
                       help="Aspect ratio preset (overrides width/height)")
    parser.add_argument("--motion-prompt", type=str, 
                       help="Motion/animation instructions for natural movement")
    
    args = parser.parse_args()
    
    # Validate text mode requires voice_id
    if args.text and not args.voice_id:
        parser.error("--voice-id is required when using --text")
    
    # Determine dimensions from aspect ratio or explicit values
    if args.aspect_ratio:
        width, height = ASPECT_RATIOS[args.aspect_ratio]
    else:
        width, height = args.width, args.height
    
    result = generate_avatar_video(
        avatar_id=args.avatar_id,
        output_path=args.output,
        audio_url=args.audio_url,
        text=args.text,
        voice_id=args.voice_id,
        width=width,
        height=height,
        motion_prompt=args.motion_prompt,
    )
    
    if result is None:
        sys.exit(1)


if __name__ == "__main__":
    main()
