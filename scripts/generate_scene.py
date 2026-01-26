#!/usr/bin/env python3
"""Generate a complete scene with voiceover, avatar, and update script.json.

This script handles the full pipeline for adding a new scene:
1. Generate voiceover with ElevenLabs (word timestamps)
2. Upload audio to Supabase for public URL
3. Generate HeyGen avatar video
4. Crop avatar for template (SplitProof)
5. Update script.json and voiceover manifest

Usage:
    python scripts/generate_scene.py \
        --project first-draft \
        --scene-id scene_002 \
        --text "looks like something straight out of a sci-fi movie except its real" \
        --template SplitProof
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables from .env file
load_dotenv(Path(__file__).parent.parent / ".env")

from src.audio.tts import ElevenLabsTTS
from src.config import TTSConfig


def upload_to_supabase(audio_path: Path, filename: str) -> str:
    """Upload audio file to Supabase storage and return public URL."""
    supabase_url = os.environ.get("SUPABASE_PROJECT_URL") or os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_ANON_KEY")
    
    if not supabase_url or not supabase_key:
        raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY required")
    
    headers = {
        "Authorization": f"Bearer {supabase_key}",
        "apikey": supabase_key,
        "Content-Type": "audio/mpeg",
    }
    
    with open(audio_path, "rb") as f:
        audio_bytes = f.read()
    
    with httpx.Client(timeout=60.0) as client:
        # Upload to Supabase storage
        resp = client.post(
            f"{supabase_url}/storage/v1/object/audio/{filename}",
            headers=headers,
            content=audio_bytes
        )
        
        if resp.status_code not in (200, 201):
            # Try upsert if file exists
            resp = client.put(
                f"{supabase_url}/storage/v1/object/audio/{filename}",
                headers=headers,
                content=audio_bytes
            )
            
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"Upload failed: {resp.status_code} - {resp.text}")
    
    # Return public URL
    public_url = f"{supabase_url}/storage/v1/object/public/audio/{filename}"
    return public_url


def generate_heygen_avatar(
    audio_url: str,
    avatar_id: str,
    output_path: Path,
    width: int = 1280,
    height: int = 720,
    motion_prompt: str | None = None,
) -> Path | None:
    """Generate HeyGen avatar video with audio lip-sync."""
    api_key = os.environ.get("HEYGEN_API_KEY")
    if not api_key:
        raise ValueError("HEYGEN_API_KEY required")
    
    headers = {
        "X-Api-Key": api_key,
        "Content-Type": "application/json"
    }
    
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
    
    print(f"  Creating HeyGen avatar...")
    print(f"    Avatar ID: {avatar_id}")
    print(f"    Dimensions: {width}x{height}")
    
    with httpx.Client(timeout=60.0) as client:
        response = client.post(
            "https://api.heygen.com/v2/video/generate",
            headers=headers,
            json=payload
        )
        
        if response.status_code != 200:
            print(f"  Error: {response.status_code} - {response.text}")
            return None
            
        data = response.json()
        
        if data.get("error"):
            print(f"  API Error: {data['error']}")
            return None
            
        video_id = data.get("data", {}).get("video_id")
        if not video_id:
            print(f"  No video_id: {data}")
            return None
            
        print(f"    Video ID: {video_id}")
        print(f"    Waiting for generation...")
        
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
                print(f"    Completed! Downloading...")
                
                video_response = client.get(video_url)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(video_response.content)
                    
                print(f"    Saved: {output_path}")
                return output_path
                
            elif status == "failed":
                error = status_data.get("data", {}).get("error")
                print(f"    Failed: {error}")
                return None
                
            else:
                print(f"    Status: {status} ({elapsed}s)")
                time.sleep(poll_interval)
                elapsed += poll_interval
        
        print(f"    Timeout after {max_wait}s")
        return None


def crop_for_template(input_path: Path, output_path: Path, template: str) -> Path:
    """Crop avatar video for specific template aspect ratio."""
    # Crop settings for different templates
    crops = {
        "SplitProof": "crop=1012:720:134:0",  # 1080/768 = 1.406 aspect
        "FullAvatar": "crop=405:720:437:0",   # 9:16 vertical
        "PiP": "crop=405:720:437:0",          # 9:16 vertical
    }
    
    crop_filter = crops.get(template, crops["SplitProof"])
    
    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-vf", crop_filter,
        "-c:a", "copy",
        str(output_path)
    ]
    
    print(f"  Cropping for {template}...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"  FFmpeg error: {result.stderr}")
        raise RuntimeError("Crop failed")
    
    print(f"    Saved: {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Generate complete scene with voiceover and avatar")
    parser.add_argument("--project", required=True, help="Project ID (e.g., first-draft)")
    parser.add_argument("--scene-id", required=True, help="Scene ID (e.g., scene_002)")
    parser.add_argument("--text", required=True, help="Voiceover text")
    parser.add_argument("--template", default="SplitProof", help="Template type")
    parser.add_argument("--avatar-id", help="HeyGen avatar ID (overrides config)")
    parser.add_argument("--voice-id", help="ElevenLabs voice ID (overrides config)")
    
    args = parser.parse_args()
    
    # Paths
    project_dir = Path(f"projects/{args.project}")
    config_path = project_dir / "config.json"
    script_path = project_dir / "script" / "script.json"
    manifest_path = project_dir / "voiceover" / "manifest.json"
    voiceover_dir = project_dir / "voiceover"
    avatar_dir = project_dir / "avatar"
    
    # Load project config
    with open(config_path) as f:
        config = json.load(f)
    
    voice_id = args.voice_id or config.get("tts", {}).get("voice_id", "21m00Tcm4TlvDq8ikWAM")
    avatar_id = args.avatar_id or config.get("avatar", {}).get("avatar_id", "a247c0b271f0447088bac6043903cf16")
    
    print(f"\n=== Generating {args.scene_id} ===")
    print(f"Text: \"{args.text}\"")
    print(f"Template: {args.template}")
    
    # Step 1: Generate voiceover with timestamps
    print(f"\n[1/5] Generating voiceover...")
    audio_path = voiceover_dir / f"{args.scene_id}.mp3"
    
    tts_config = TTSConfig(
        provider="elevenlabs",
        voice_id=voice_id,
        model="eleven_multilingual_v2"
    )
    tts = ElevenLabsTTS(tts_config)
    
    result = tts.generate_with_timestamps(args.text, audio_path)
    print(f"  Audio: {audio_path}")
    print(f"  Duration: {result.duration_seconds:.2f}s")
    print(f"  Words: {len(result.word_timestamps)}")
    
    # Step 2: Upload to Supabase
    print(f"\n[2/5] Uploading to Supabase...")
    audio_url = upload_to_supabase(audio_path, f"{args.project}_{args.scene_id}.mp3")
    print(f"  URL: {audio_url}")
    
    # Step 3: Generate HeyGen avatar (16:9 720p for cropping)
    print(f"\n[3/5] Generating HeyGen avatar...")
    avatar_16x9_path = avatar_dir / f"{args.scene_id}_16x9.mp4"
    
    motion_prompt = "Talking Naturally: Subject talks animatedly while maintaining direct eye contact with the camera. Background elements subtly move to enhance realism. Camera remains absolutely static."
    
    avatar_result = generate_heygen_avatar(
        audio_url=audio_url,
        avatar_id=avatar_id,
        output_path=avatar_16x9_path,
        width=1280,
        height=720,
        motion_prompt=motion_prompt,
    )
    
    if avatar_result is None:
        print("  Avatar generation failed!")
        sys.exit(1)
    
    # Step 4: Crop for template
    print(f"\n[4/5] Cropping for {args.template}...")
    avatar_cropped_path = avatar_dir / f"{args.scene_id}_bottom.mp4"
    crop_for_template(avatar_16x9_path, avatar_cropped_path, args.template)
    
    # Step 5: Update script.json and manifest.json
    print(f"\n[5/5] Updating script files...")
    
    # Load existing script
    with open(script_path) as f:
        script = json.load(f)
    
    # Calculate start time from previous scene end
    scenes = script.get("scenes", [])
    if scenes:
        start_seconds = scenes[-1].get("end_seconds", 0)
    else:
        start_seconds = 0
    
    end_seconds = start_seconds + result.duration_seconds
    
    # Create new scene
    new_scene = {
        "id": args.scene_id,
        "template": args.template,
        "start_seconds": round(start_seconds, 3),
        "end_seconds": round(end_seconds, 3),
        "background": {
            "type": "ai_video",
            "src": "backgrounds/drone_swarm_veo3.mp4"
        },
        "avatar": {
            "visible": True,
            "position": "bottom",
            "src": f"avatar/{args.scene_id}_bottom.mp4"
        },
        "text": {
            "caption_style": "word_by_word"
        },
        "audio": {
            "text": args.text,
            "file": f"voiceover/{args.scene_id}.mp3",
            "word_timestamps": [
                {
                    "word": wt.word,
                    "start": round(wt.start_seconds, 3),
                    "end": round(wt.end_seconds, 3)
                }
                for wt in result.word_timestamps
            ]
        }
    }
    
    # Add to script
    scenes.append(new_scene)
    script["scenes"] = scenes
    script["duration_seconds"] = round(end_seconds, 3)
    
    # Save script
    with open(script_path, "w") as f:
        json.dump(script, f, indent=2)
    print(f"  Updated: {script_path}")
    
    # Update manifest
    with open(manifest_path) as f:
        manifest = json.load(f)
    
    manifest_scene = {
        "scene_id": args.scene_id,
        "audio_path": str(audio_path.absolute()),
        "duration_seconds": result.duration_seconds,
        "word_timestamps": [
            {
                "word": wt.word,
                "start_seconds": wt.start_seconds,
                "end_seconds": wt.end_seconds
            }
            for wt in result.word_timestamps
        ]
    }
    
    manifest["scenes"].append(manifest_scene)
    manifest["total_duration_seconds"] = end_seconds
    
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"  Updated: {manifest_path}")
    
    print(f"\n=== Done! ===")
    print(f"Scene {args.scene_id} added to script.json")
    print(f"  Start: {start_seconds:.2f}s")
    print(f"  End: {end_seconds:.2f}s")
    print(f"  Duration: {result.duration_seconds:.2f}s")


if __name__ == "__main__":
    main()
