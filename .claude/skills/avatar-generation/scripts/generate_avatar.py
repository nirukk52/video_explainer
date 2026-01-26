#!/usr/bin/env python3
"""Generate HeyGen avatar video with audio lip-sync and optional cropping.

This script handles the full avatar generation workflow:
1. Upload audio to Supabase Storage (or use existing URL)
2. Generate avatar video via HeyGen API with motion prompts
3. Optionally crop to target aspect ratio using ffmpeg

Usage:
    # With local audio file (uploads to Supabase)
    python generate_avatar.py --audio-file path/to/audio.mp3 --output avatar.mp4
    
    # With public audio URL
    python generate_avatar.py --audio-url https://example.com/audio.mp3 --output avatar.mp4
    
    # With motion prompt and aspect ratio
    python generate_avatar.py --audio-file audio.mp3 --output avatar.mp4 \
        --motion-prompt "Talking naturally with eye contact" \
        --aspect-ratio 16:9 --crop-to 9:16

Environment Variables:
    HEYGEN_API_KEY: HeyGen API key (required)
    SUPABASE_URL: Supabase project URL (for audio upload)
    SUPABASE_ANON_KEY: Supabase anon key (for audio upload)
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx


# Predefined aspect ratio dimensions
ASPECT_RATIOS = {
    "9:16": (1080, 1920),   # Vertical/portrait - shorts
    "16:9": (1920, 1080),   # Horizontal/landscape (1080p limited on basic plan)
    "16:9-720": (1280, 720),  # 720p landscape (works on basic plan)
    "1:1": (1080, 1080),    # Square
}


def upload_to_supabase(
    file_path: Path,
    supabase_url: str,
    supabase_key: str,
    bucket: str = "audio"
) -> str:
    """Upload file to Supabase Storage and return public URL.
    
    Args:
        file_path: Path to local file
        supabase_url: Supabase project URL
        supabase_key: Supabase anon key
        bucket: Storage bucket name
        
    Returns:
        Public URL for the uploaded file
    """
    headers = {
        "Authorization": f"Bearer {supabase_key}",
        "apikey": supabase_key,
        "Content-Type": "audio/mpeg",
    }
    
    file_name = file_path.name
    file_content = file_path.read_bytes()
    
    with httpx.Client() as client:
        # Upload file
        resp = client.post(
            f"{supabase_url}/storage/v1/object/{bucket}/{file_name}",
            headers=headers,
            content=file_content
        )
        
        if resp.status_code not in [200, 201]:
            raise Exception(f"Upload failed: {resp.status_code} - {resp.text}")
        
        return f"{supabase_url}/storage/v1/object/public/{bucket}/{file_name}"


def generate_heygen_video(
    audio_url: str,
    avatar_id: str,
    output_path: Path,
    width: int = 1280,
    height: int = 720,
    motion_prompt: str | None = None,
    api_key: str | None = None,
) -> Path | None:
    """Generate avatar video with audio lip-sync via HeyGen API.
    
    Args:
        audio_url: Public URL to the audio file
        avatar_id: HeyGen avatar ID
        output_path: Path to save the video
        width: Video width
        height: Video height
        motion_prompt: Optional motion/animation instructions
        api_key: HeyGen API key
        
    Returns:
        Path to the generated video, or None on failure
    """
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
    
    if motion_prompt:
        character_config["motion_prompt"] = motion_prompt
    
    payload = {
        "video_inputs": [{
            "character": character_config,
            "voice": {
                "type": "audio",
                "audio_url": audio_url
            }
        }],
        "dimension": {
            "width": width,
            "height": height
        }
    }
    
    print(f"Creating avatar video...")
    print(f"  Avatar ID: {avatar_id}")
    print(f"  Audio URL: {audio_url}")
    print(f"  Dimensions: {width}x{height}")
    if motion_prompt:
        print(f"  Motion prompt: {motion_prompt[:50]}...")
    
    with httpx.Client(timeout=60.0) as client:
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
        max_wait = 300
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


def crop_video(
    input_path: Path,
    output_path: Path,
    target_aspect: str
) -> Path | None:
    """Crop video to target aspect ratio using ffmpeg.
    
    Extracts center portion to achieve target aspect ratio.
    
    Args:
        input_path: Path to input video
        output_path: Path to save cropped video
        target_aspect: Target aspect ratio (e.g., "9:16")
        
    Returns:
        Path to cropped video, or None on failure
    """
    # Get input video dimensions
    probe_cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=p=0",
        str(input_path)
    ]
    
    result = subprocess.run(probe_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ffprobe error: {result.stderr}")
        return None
    
    in_w, in_h = map(int, result.stdout.strip().split(","))
    
    # Calculate crop dimensions for target aspect ratio
    target_w, target_h = target_aspect.split(":")
    target_ratio = int(target_w) / int(target_h)
    
    in_ratio = in_w / in_h
    
    if in_ratio > target_ratio:
        # Input is wider, crop width
        crop_h = in_h
        crop_w = int(in_h * target_ratio)
        crop_x = (in_w - crop_w) // 2
        crop_y = 0
    else:
        # Input is taller, crop height
        crop_w = in_w
        crop_h = int(in_w / target_ratio)
        crop_x = 0
        crop_y = (in_h - crop_h) // 2
    
    print(f"Cropping {in_w}x{in_h} to {crop_w}x{crop_h} (aspect {target_aspect})")
    
    crop_cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-vf", f"crop={crop_w}:{crop_h}:{crop_x}:{crop_y}",
        "-c:a", "copy",
        str(output_path)
    ]
    
    result = subprocess.run(crop_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ffmpeg error: {result.stderr}")
        return None
    
    print(f"Cropped video saved to: {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Generate HeyGen avatar video with audio lip-sync"
    )
    
    # Audio source (one required)
    audio_group = parser.add_mutually_exclusive_group(required=True)
    audio_group.add_argument("--audio-url", help="Public URL to audio file")
    audio_group.add_argument("--audio-file", type=Path, help="Local audio file (will upload to Supabase)")
    
    # Output
    parser.add_argument("--output", required=True, type=Path, help="Output video path")
    
    # Avatar config
    parser.add_argument("--avatar-id", default="a247c0b271f0447088bac6043903cf16",
                       help="HeyGen avatar ID")
    parser.add_argument("--motion-prompt", type=str,
                       help="Motion/animation instructions for natural movement")
    
    # Video dimensions
    parser.add_argument("--aspect-ratio", choices=list(ASPECT_RATIOS.keys()),
                       default="16:9-720", help="Output aspect ratio preset")
    parser.add_argument("--width", type=int, help="Custom width (overrides aspect-ratio)")
    parser.add_argument("--height", type=int, help="Custom height (overrides aspect-ratio)")
    
    # Post-processing
    parser.add_argument("--crop-to", type=str,
                       help="Crop to different aspect ratio after generation (e.g., 9:16)")
    
    # Supabase config (for audio upload)
    parser.add_argument("--supabase-url", help="Supabase project URL")
    parser.add_argument("--supabase-key", help="Supabase anon key")
    
    args = parser.parse_args()
    
    # Determine audio URL
    if args.audio_file:
        supabase_url = args.supabase_url or os.environ.get("SUPABASE_URL")
        supabase_key = args.supabase_key or os.environ.get("SUPABASE_ANON_KEY")
        
        if not supabase_url or not supabase_key:
            print("Error: SUPABASE_URL and SUPABASE_ANON_KEY required for audio upload")
            sys.exit(1)
        
        print(f"Uploading audio to Supabase...")
        audio_url = upload_to_supabase(args.audio_file, supabase_url, supabase_key)
        print(f"  Uploaded: {audio_url}")
    else:
        audio_url = args.audio_url
    
    # Determine dimensions
    if args.width and args.height:
        width, height = args.width, args.height
    else:
        width, height = ASPECT_RATIOS[args.aspect_ratio]
    
    # Generate avatar video
    video_path = generate_heygen_video(
        audio_url=audio_url,
        avatar_id=args.avatar_id,
        output_path=args.output if not args.crop_to else args.output.with_suffix(".tmp.mp4"),
        width=width,
        height=height,
        motion_prompt=args.motion_prompt,
    )
    
    if video_path is None:
        sys.exit(1)
    
    # Crop if requested
    if args.crop_to:
        final_path = crop_video(video_path, args.output, args.crop_to)
        if final_path is None:
            sys.exit(1)
        # Clean up temp file
        video_path.unlink()
        print(f"\nFinal video: {args.output}")
    else:
        print(f"\nFinal video: {video_path}")


if __name__ == "__main__":
    main()
