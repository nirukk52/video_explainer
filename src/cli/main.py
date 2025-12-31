"""Main CLI entry point for video explainer pipeline.

Usage:
    python -m src.cli list                                    # List all projects
    python -m src.cli info <project>                          # Show project info
    python -m src.cli create <project_id>                     # Create new project
    python -m src.cli script <project>                        # Generate script from docs
    python -m src.cli narration <project>                     # Generate narrations
    python -m src.cli voiceover <project>                     # Generate voiceovers
    python -m src.cli storyboard <project> --view             # View storyboard
    python -m src.cli sound <project> plan                    # Plan sound effects
    python -m src.cli sound <project> library --list          # List sound library
    python -m src.cli sound <project> mix                     # Mix audio
    python -m src.cli render <project>                        # Render video
    python -m src.cli render <project> -r 4k                  # Render in 4K
    python -m src.cli feedback <project> add "<text>"         # Process feedback
    python -m src.cli feedback <project> list                 # List feedback

Pipeline workflow:
    1. create   - Create new project with config
    2. script   - Generate script from input documents (optional)
    3. narration - Generate narrations for each scene
    4. voiceover - Generate audio files from narrations
    5. sound    - Plan and mix sound effects and music
    6. render   - Render final video
    7. feedback - Iterate on video with natural language feedback
"""

import argparse
import json
import sys
from pathlib import Path


def cmd_list(args: argparse.Namespace) -> int:
    """List all available projects."""
    from ..project import list_projects

    projects = list_projects(args.projects_dir)

    if not projects:
        print(f"No projects found in {args.projects_dir}/")
        return 0

    print(f"Found {len(projects)} project(s):\n")
    for project in projects:
        print(f"  {project.id}")
        print(f"    Title: {project.title}")
        print(f"    Path: {project.root_dir}")
        print()

    return 0


def cmd_info(args: argparse.Namespace) -> int:
    """Show detailed project information."""
    from ..project import load_project

    try:
        project = load_project(Path(args.projects_dir) / args.project)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print(f"Project: {project.id}")
    print(f"Title: {project.title}")
    print(f"Description: {project.description}")
    print(f"Version: {project.version}")
    print(f"Path: {project.root_dir}")
    print()

    print("Video Settings:")
    print(f"  Resolution: {project.video.width}x{project.video.height}")
    print(f"  FPS: {project.video.fps}")
    print(f"  Target Duration: {project.video.target_duration_seconds}s")
    print()

    print("TTS Settings:")
    print(f"  Provider: {project.tts.provider}")
    print(f"  Voice ID: {project.tts.voice_id}")
    print()

    # Check what files exist
    print("Files:")
    narration_path = project.get_path("narration")
    print(f"  Narrations: {'[exists]' if narration_path.exists() else '[missing]'} {narration_path}")

    voiceover_files = project.get_voiceover_files()
    print(f"  Voiceovers: {len(voiceover_files)} audio files")

    storyboard_path = project.get_path("storyboard")
    print(f"  Storyboard: {'[exists]' if storyboard_path.exists() else '[missing]'} {storyboard_path}")

    output_files = list(project.output_dir.glob("*.mp4"))
    print(f"  Output: {len(output_files)} video files")

    return 0


def cmd_voiceover(args: argparse.Namespace) -> int:
    """Generate voiceovers for a project."""
    from ..project import load_project
    from ..audio import get_tts_provider, ManualVoiceoverProvider
    from ..config import Config, TTSConfig

    try:
        project = load_project(Path(args.projects_dir) / args.project)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Load narrations
    try:
        narrations = project.load_narrations()
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Handle --export-script: generate recording script and exit
    if args.export_script:
        return _export_recording_script(project, narrations, args)

    print(f"Generating voiceovers for {project.id}")
    print(f"Found {len(narrations)} scenes")
    print()

    # Determine TTS provider
    provider_name = args.provider or project.tts.provider
    if args.mock:
        provider_name = "mock"

    # Handle manual provider
    if provider_name == "manual":
        if not args.audio_dir:
            print("Error: --audio-dir is required when using manual provider", file=sys.stderr)
            return 1

        audio_dir = Path(args.audio_dir)
        if not audio_dir.exists():
            print(f"Error: Audio directory not found: {audio_dir}", file=sys.stderr)
            return 1

        print(f"Using manual voiceover provider")
        print(f"Audio directory: {audio_dir}")

        # Check for missing recordings
        config = Config()
        tts = ManualVoiceoverProvider(
            config.tts,
            audio_dir=audio_dir,
            whisper_model=args.whisper_model or "base",
        )

        scene_ids = [n.scene_id for n in narrations]
        missing = tts.list_missing_scenes(scene_ids)
        if missing:
            print(f"\nWarning: Missing audio files for {len(missing)} scene(s):")
            for scene_id in missing:
                print(f"  - {scene_id}.mp3 (or .wav, .m4a)")
            if not args.continue_on_error:
                print("\nUse --continue-on-error to skip missing scenes")
                return 1
            print()
    else:
        print(f"Using TTS provider: {provider_name}")

        # Create TTS config
        config = Config()
        config.tts.provider = provider_name
        if project.tts.voice_id:
            config.tts.voice_id = project.tts.voice_id

        tts = get_tts_provider(config)

    # Generate voiceovers
    output_dir = project.voiceover_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    results = []
    total_duration = 0.0

    for narration in narrations:
        print(f"  Processing: {narration.title}...")
        output_path = output_dir / f"{narration.scene_id}.mp3"

        try:
            # ManualVoiceoverProvider needs scene_id passed explicitly
            if provider_name == "manual":
                result = tts.generate_with_timestamps(
                    narration.narration,
                    output_path,
                    scene_id=narration.scene_id,
                )
            else:
                result = tts.generate_with_timestamps(narration.narration, output_path)

            results.append({
                "scene_id": narration.scene_id,
                "audio_path": str(output_path),
                "duration_seconds": result.duration_seconds,
                "word_timestamps": [
                    {
                        "word": ts.word,
                        "start_seconds": ts.start_seconds,
                        "end_seconds": ts.end_seconds,
                    }
                    for ts in result.word_timestamps
                ],
            })
            total_duration += result.duration_seconds
            print(f"    Duration: {result.duration_seconds:.2f}s")
            if provider_name == "manual":
                print(f"    Words transcribed: {len(result.word_timestamps)}")
        except FileNotFoundError as e:
            print(f"    Skipped: {e}", file=sys.stderr)
            if not args.continue_on_error:
                return 1
        except Exception as e:
            print(f"    Error: {e}", file=sys.stderr)
            if not args.continue_on_error:
                return 1

    # Save manifest
    manifest = {
        "scenes": results,
        "total_duration_seconds": total_duration,
        "output_dir": str(output_dir),
    }

    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print()
    print(f"Processed {len(results)} voiceovers")
    print(f"Total duration: {total_duration:.2f}s ({total_duration/60:.1f} min)")
    print(f"Manifest saved to: {manifest_path}")

    # Auto-sync storyboard durations with voiceover durations
    if not args.no_sync:
        sync_result = _sync_storyboard_durations(project, results)
        if sync_result > 0:
            print(f"\nSynced {sync_result} scene duration(s) in storyboard")

    return 0


def _sync_storyboard_durations(project, voiceover_results: list[dict]) -> int:
    """Sync storyboard scene durations with actual voiceover durations.

    Args:
        project: The project
        voiceover_results: List of voiceover results with scene_id and duration_seconds

    Returns:
        Number of scenes updated
    """
    storyboard_path = project.get_path("storyboard")
    if not storyboard_path.exists():
        return 0

    try:
        with open(storyboard_path) as f:
            storyboard = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return 0

    # Create lookup for voiceover durations
    vo_durations = {vo["scene_id"]: vo["duration_seconds"] for vo in voiceover_results}

    # Update storyboard scene durations
    updated_count = 0
    for scene in storyboard.get("scenes", []):
        scene_id = scene.get("id") or scene.get("scene_id")
        if scene_id and scene_id in vo_durations:
            old_dur = scene.get("audio_duration_seconds", 0)
            # Add a small buffer (0.5s) to ensure voiceover fits comfortably
            new_dur = round(vo_durations[scene_id] + 0.5, 2)

            # Only update if difference is significant (> 0.5s)
            if abs(new_dur - old_dur) > 0.5:
                scene["audio_duration_seconds"] = new_dur
                updated_count += 1

    if updated_count > 0:
        # Update total duration
        total_duration = sum(
            scene.get("audio_duration_seconds", 0)
            for scene in storyboard.get("scenes", [])
        )
        storyboard["total_duration_seconds"] = round(total_duration, 2)

        # Save updated storyboard
        with open(storyboard_path, "w") as f:
            json.dump(storyboard, f, indent=2)

    return updated_count


def _export_recording_script(project, narrations, args) -> int:
    """Export a recording script for manual voiceover recording."""
    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = project.root_dir / "recording_script.txt"

    # Calculate estimated durations (~150 words per minute)
    lines = []
    lines.append("=" * 70)
    lines.append(f"RECORDING SCRIPT: {project.title}")
    lines.append("=" * 70)
    lines.append("")
    lines.append("Instructions:")
    lines.append("1. Record each scene as a separate audio file")
    lines.append("2. Name files by scene_id (e.g., scene1_hook.mp3)")
    lines.append("3. Speak naturally - aim for conversational tone")
    lines.append("4. Leave ~0.5s silence at start and end of each recording")
    lines.append("")
    lines.append("-" * 70)
    lines.append("")

    total_words = 0
    for i, narration in enumerate(narrations, 1):
        words = len(narration.narration.split())
        total_words += words
        duration_estimate = (words / 150) * 60  # seconds

        lines.append(f"=== Scene {i}: {narration.scene_id} ===")
        lines.append(f"Title: {narration.title}")
        lines.append(f"Words: {words} (~{duration_estimate:.0f} seconds)")
        lines.append(f"Output file: {narration.scene_id}.mp3")
        lines.append("")
        lines.append(f'"{narration.narration}"')
        lines.append("")
        lines.append("-" * 70)
        lines.append("")

    total_duration = (total_words / 150) * 60
    lines.append(f"TOTAL: {len(narrations)} scenes, {total_words} words")
    lines.append(f"Estimated recording time: {total_duration:.0f} seconds ({total_duration/60:.1f} minutes)")

    # Write to file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write("\n".join(lines))

    print(f"Recording script exported to: {output_path}")
    print(f"Scenes: {len(narrations)}")
    print(f"Estimated duration: {total_duration/60:.1f} minutes")
    print()
    print("Next steps:")
    print(f"  1. Record audio files following the script")
    print(f"  2. Place files in a directory (e.g., ./recordings/)")
    print(f"  3. Import with: python -m src.cli voiceover {project.id} --provider manual --audio-dir ./recordings/")

    return 0


def cmd_storyboard(args: argparse.Namespace) -> int:
    """Generate or view storyboard for a project."""
    from ..project import load_project

    try:
        project = load_project(Path(args.projects_dir) / args.project)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    storyboard_path = project.get_path("storyboard")

    if args.view:
        # View existing storyboard
        if not storyboard_path.exists():
            print(f"Error: Storyboard not found: {storyboard_path}", file=sys.stderr)
            return 1

        with open(storyboard_path) as f:
            storyboard = json.load(f)

        print(f"Storyboard: {storyboard.get('title', 'Untitled')}")
        print(f"Duration: {storyboard.get('duration_seconds', 0)}s")
        print(f"Beats: {len(storyboard.get('beats', []))}")
        print()

        for i, beat in enumerate(storyboard.get("beats", []), 1):
            print(f"  Beat {i}: {beat.get('id', 'unnamed')}")
            print(f"    Time: {beat.get('start_seconds', 0):.1f}s - {beat.get('end_seconds', 0):.1f}s")
            print(f"    Elements: {len(beat.get('elements', []))}")

        return 0

    # Generate storyboard (placeholder - would use LLM)
    print("Storyboard generation from LLM not yet implemented.")
    print("Use --view to view existing storyboard.")
    return 0


def cmd_script(args: argparse.Namespace) -> int:
    """Generate a script from input documents."""
    from ..project import load_project
    from ..ingestion import parse_markdown
    from ..understanding import ContentAnalyzer
    from ..script import ScriptGenerator
    from ..config import Config

    try:
        project = load_project(Path(args.projects_dir) / args.project)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print(f"Generating script for {project.id}")

    # Find input documents
    input_dir = project.input_dir
    if not input_dir.exists():
        print(f"Error: Input directory not found: {input_dir}", file=sys.stderr)
        print("Add source documents to the input/ directory first.")
        return 1

    input_files = list(input_dir.glob("*.md"))
    if not input_files:
        print(f"Error: No markdown files found in {input_dir}", file=sys.stderr)
        return 1

    print(f"Found {len(input_files)} input file(s)")

    # Parse documents
    documents = []
    for f in input_files:
        print(f"  Parsing: {f.name}")
        doc = parse_markdown(f)
        documents.append(doc)

    # Analyze content
    print("\nAnalyzing content...")
    config = Config()
    if args.mock:
        config.llm.provider = "mock"

    analyzer = ContentAnalyzer(config)
    analysis = analyzer.analyze(documents[0])  # Use first document

    print(f"  Thesis: {analysis.core_thesis[:60]}...")
    print(f"  Concepts: {len(analysis.key_concepts)}")

    # Generate script
    print("\nGenerating script...")
    generator = ScriptGenerator(config)
    script = generator.generate(
        documents[0],
        analysis,
        target_duration=args.duration or project.video.target_duration_seconds,
    )

    print(f"  Generated {len(script.scenes)} scenes")
    print(f"  Total duration: {script.total_duration_seconds}s")

    # Save script
    script_path = project.root_dir / "script" / "script.json"
    script_path.parent.mkdir(parents=True, exist_ok=True)

    with open(script_path, "w") as f:
        json.dump(script.model_dump(), f, indent=2)

    print(f"\nScript saved to: {script_path}")

    # Show scenes
    if args.verbose:
        print("\nScenes:")
        for scene in script.scenes:
            print(f"  {scene.scene_id}. {scene.title} ({scene.duration_seconds}s)")
            print(f"      Type: {scene.scene_type}")
            print(f"      Voiceover: {scene.voiceover[:50]}...")
            print()

    return 0


def cmd_narration(args: argparse.Namespace) -> int:
    """Generate narrations for a project."""
    from ..project import load_project
    from ..understanding.llm_provider import ClaudeCodeLLMProvider
    from ..config import LLMConfig

    try:
        project = load_project(Path(args.projects_dir) / args.project)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print(f"Generating narrations for {project.id}")

    narration_path = project.get_path("narration")

    # Check if narrations already exist
    if narration_path.exists() and not args.force:
        print(f"Narrations already exist: {narration_path}")
        print("Use --force to regenerate.")
        return 0

    # If a script exists, use it as context
    script_path = project.root_dir / "script" / "script.json"
    script_context = ""
    if script_path.exists():
        with open(script_path) as f:
            script_data = json.load(f)
        script_context = f"\nExisting script to base narrations on:\n{json.dumps(script_data, indent=2)}"

    # If topic is provided, use it
    topic = args.topic or project.title

    # Generate narrations using Claude Code
    if args.mock:
        # Use mock narrations for testing
        narrations = _generate_mock_narrations(topic)
        # Write mock narrations to file
        narration_path.parent.mkdir(parents=True, exist_ok=True)
        with open(narration_path, "w") as f:
            json.dump(narrations, f, indent=2)
    else:
        # Use Claude Code to generate narrations
        print(f"Generating narrations for topic: {topic}")
        print("Using Claude Code to generate narrations...")

        llm_config = LLMConfig(provider="claude-code", model="claude-opus-4-5-20251101")
        llm = ClaudeCodeLLMProvider(
            llm_config,
            working_dir=project.root_dir.parent.parent,  # Repo root
            timeout=300,
        )

        prompt = f"""Generate narrations for a video about: {topic}

{script_context}

Create a narrations.json file with the following structure:
{{
  "scenes": [
    {{
      "scene_id": "scene1_hook",
      "title": "The Hook",
      "narration": "The voiceover text for this scene..."
    }},
    ...
  ]
}}

Requirements:
1. Write engaging, conversational narration (not academic)
2. Each scene should be 15-30 seconds when spoken
3. Include 8-12 scenes covering the topic comprehensively
4. Start with a hook that creates curiosity
5. End with a memorable conclusion

Write the JSON to: {narration_path}
"""

        try:
            result = llm.generate_with_file_access(prompt, allow_writes=True)
            if not result.success:
                print(f"Error: {result.error_message}", file=sys.stderr)
                return 1
        except Exception as e:
            print(f"Error generating narrations: {e}", file=sys.stderr)
            return 1

    # Verify narrations were created
    if narration_path.exists():
        with open(narration_path) as f:
            narrations = json.load(f)
        scene_count = len(narrations.get("scenes", []))
        print(f"\nGenerated {scene_count} narrations")
        print(f"Saved to: {narration_path}")

        if args.verbose:
            print("\nScenes:")
            for scene in narrations.get("scenes", []):
                print(f"  {scene.get('scene_id')}: {scene.get('title')}")
    else:
        print("Warning: Narrations file was not created.")

    return 0


def _generate_mock_narrations(topic: str) -> dict:
    """Generate mock narrations for testing."""
    return {
        "scenes": [
            {
                "scene_id": "scene1_hook",
                "title": "The Hook",
                "narration": f"What if I told you that {topic} could change everything you know about technology?",
            },
            {
                "scene_id": "scene2_context",
                "title": "Setting the Context",
                "narration": f"To understand {topic}, we need to first look at the bigger picture.",
            },
            {
                "scene_id": "scene3_explanation",
                "title": "How It Works",
                "narration": f"At its core, {topic} works by processing information in a fundamentally different way.",
            },
            {
                "scene_id": "scene4_conclusion",
                "title": "The Takeaway",
                "narration": f"So remember, {topic} isn't just a technology - it's a paradigm shift.",
            },
        ]
    }


# Resolution presets
RESOLUTION_PRESETS = {
    "4k": (3840, 2160),
    "1440p": (2560, 1440),
    "1080p": (1920, 1080),
    "720p": (1280, 720),
    "480p": (854, 480),
}


def cmd_render(args: argparse.Namespace) -> int:
    """Render video for a project."""
    import subprocess

    from ..project import load_project

    try:
        project = load_project(Path(args.projects_dir) / args.project)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print(f"Rendering video for {project.id}")

    # Determine composition and setup
    remotion_dir = Path(__file__).parent.parent.parent / "remotion"
    render_script = remotion_dir / "scripts" / "render.mjs"

    if not render_script.exists():
        print(f"Error: Render script not found: {render_script}", file=sys.stderr)
        return 1

    # Check for storyboard
    storyboard_path = project.get_path("storyboard")
    if not storyboard_path.exists():
        print(f"Error: Storyboard not found: {storyboard_path}", file=sys.stderr)
        print("Run storyboard generation first or create storyboard/storyboard.json")
        return 1

    # Check for voiceover files
    # SFX is now handled directly by Remotion via sfx_cues in storyboard.json
    voiceover_files = list(project.voiceover_dir.glob("*.mp3"))
    print(f"Found {len(voiceover_files)} voiceover files")
    audio_dir = "voiceover"

    # Determine resolution
    resolution_name = args.resolution or "1080p"
    if resolution_name not in RESOLUTION_PRESETS:
        print(f"Error: Unknown resolution '{resolution_name}'", file=sys.stderr)
        print(f"Available: {', '.join(RESOLUTION_PRESETS.keys())}", file=sys.stderr)
        return 1
    width, height = RESOLUTION_PRESETS[resolution_name]

    # Determine output path
    if args.preview:
        output_path = project.output_dir / "preview" / "preview.mp4"
    else:
        # Include resolution in filename for non-1080p renders
        if resolution_name != "1080p":
            output_path = project.output_dir / f"final-{resolution_name}.mp4"
        else:
            output_path = project.get_path("final_video")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Build render command using new data-driven architecture
    # The render script uses the project directory to serve static files (voiceovers/mixed audio)
    cmd = [
        "node",
        str(render_script),
        "--project", str(project.root_dir),
        "--output", str(output_path),
        "--width", str(width),
        "--height", str(height),
        "--voiceover-path", audio_dir,
    ]

    print(f"Project: {project.root_dir}")
    print(f"Audio: {audio_dir}")
    print(f"Resolution: {resolution_name} ({width}x{height})")
    print(f"Output: {output_path}")
    print(f"Running: {' '.join(cmd)}")
    print()

    try:
        result = subprocess.run(cmd, cwd=str(remotion_dir))
        if result.returncode != 0:
            print(f"Render failed with exit code {result.returncode}", file=sys.stderr)
            return result.returncode
    except FileNotFoundError:
        print("Error: Node.js not found. Please install Node.js.", file=sys.stderr)
        return 1

    print()
    print(f"Video rendered to: {output_path}")
    return 0


def cmd_feedback(args: argparse.Namespace) -> int:
    """Process or view feedback for a project."""
    from ..project import load_project
    from ..feedback import FeedbackProcessor, FeedbackStore

    try:
        project = load_project(Path(args.projects_dir) / args.project)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if not args.feedback_command:
        print("Usage: python -m src.cli feedback <project> <command>")
        print("\nCommands:")
        print("  add <text>     Add and process new feedback")
        print("  list           List all feedback for the project")
        print("  show <id>      Show details of a feedback item")
        return 1

    if args.feedback_command == "add":
        # Process new feedback
        processor = FeedbackProcessor(
            project,
            dry_run=args.dry_run,
            verbose=True,  # Always show detailed progress
        )

        print(f"Processing feedback for {project.id}...")
        print(f"Feedback: {args.feedback_text}")
        print()

        if args.dry_run:
            print("[DRY RUN] Analyzing feedback only, no changes will be made")
            print()

        item = processor.process_feedback(args.feedback_text)

        print(f"Feedback ID: {item.id}")
        print(f"Status: {item.status}")

        if item.interpretation:
            print(f"\nInterpretation:")
            print(f"  {item.interpretation}")

        if item.scope:
            print(f"\nScope: {item.scope}")
            if item.affected_scenes:
                print(f"Affected scenes: {', '.join(item.affected_scenes)}")

        if item.suggested_changes:
            print(f"\nSuggested changes:")
            desc = item.suggested_changes.get("description", "")
            if desc:
                print(f"  {desc}")
            files = item.suggested_changes.get("files_to_modify", [])
            if files:
                print(f"  Files: {', '.join(files)}")

        if item.files_modified:
            print(f"\nFiles modified:")
            for f in item.files_modified:
                print(f"  - {f}")

        if item.error_message:
            print(f"\nError: {item.error_message}", file=sys.stderr)

        return 0 if item.status != "failed" else 1

    elif args.feedback_command == "list":
        # List all feedback
        store = FeedbackStore(project.root_dir, project.id)
        history = store.load()

        if not history.items:
            print(f"No feedback found for {project.id}")
            return 0

        print(f"Feedback for {project.id} ({len(history.items)} items):\n")

        for item in history.items:
            status_icon = {
                "pending": "⏳",
                "processing": "🔄",
                "applied": "✅",
                "rejected": "❌",
                "failed": "💥",
            }.get(item.status, "?")

            print(f"  {status_icon} {item.id}")
            print(f"    Status: {item.status}")
            print(f"    Feedback: {item.feedback_text[:60]}{'...' if len(item.feedback_text) > 60 else ''}")
            if item.affected_scenes:
                print(f"    Scenes: {', '.join(item.affected_scenes)}")
            print()

        return 0

    elif args.feedback_command == "show":
        # Show detailed feedback
        store = FeedbackStore(project.root_dir, project.id)
        item = store.get_item(args.feedback_id)

        if not item:
            print(f"Error: Feedback not found: {args.feedback_id}", file=sys.stderr)
            return 1

        print(f"Feedback: {item.id}")
        print(f"Status: {item.status}")
        print(f"Timestamp: {item.timestamp}")
        print()
        print("Original feedback:")
        print(f"  {item.feedback_text}")
        print()

        if item.interpretation:
            print("Interpretation:")
            print(f"  {item.interpretation}")
            print()

        if item.scope:
            print(f"Scope: {item.scope}")
        if item.affected_scenes:
            print(f"Affected scenes: {', '.join(item.affected_scenes)}")
        print()

        if item.suggested_changes:
            print("Suggested changes:")
            print(json.dumps(item.suggested_changes, indent=2))
            print()

        if item.files_modified:
            print("Files modified:")
            for f in item.files_modified:
                print(f"  - {f}")

        if item.error_message:
            print(f"\nError: {item.error_message}")

        return 0

    return 0


def cmd_create(args: argparse.Namespace) -> int:
    """Create a new project."""
    from ..project.loader import create_project

    try:
        project = create_project(
            project_id=args.project_id,
            title=args.title or args.project_id.replace("-", " ").title(),
            projects_dir=args.projects_dir,
            description=args.description or "",
        )
        print(f"Created project: {project.id}")
        print(f"Path: {project.root_dir}")
        print()
        print("Next steps:")
        print(f"  1. Add source document to {project.input_dir}/")
        print(f"  2. Add narrations to {project.narration_dir}/narrations.json")
        print(f"  3. Run: python -m src.cli voiceover {project.id}")
        return 0
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_sound(args: argparse.Namespace) -> int:
    """Sound design commands: generate SFX library for Remotion."""
    from ..project import load_project
    from ..sound.library import SoundLibrary, SOUND_MANIFEST

    try:
        project = load_project(Path(args.projects_dir) / args.project)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # SFX files go in project's sfx/ directory (used by Remotion)
    sfx_dir = project.root_dir / "sfx"

    if not args.sound_command:
        print("Usage: python -m src.cli sound <project> <command>")
        print("\nCommands:")
        print("  library    Generate/manage SFX library")
        print("\nNote: SFX cues are defined in storyboard.json and rendered by Remotion.")
        return 1

    if args.sound_command == "library":
        library = SoundLibrary(sfx_dir)

        if args.list:
            print(f"Sound Library ({len(SOUND_MANIFEST)} sounds)")
            print("=" * 50)

            for name, info in SOUND_MANIFEST.items():
                status = "[ready]" if library.sound_exists(name) else "[missing]"
                print(f"  {status} {name}")
                print(f"         {info['description']}")

            missing = library.get_missing_sounds()
            if missing:
                print(f"\n{len(missing)} sounds need to be generated.")
                print("Run: python -m src.cli sound <project> library --generate")

            return 0

        elif args.download or args.generate:
            print(f"Generating SFX library for {project.id}")

            generated = library.generate_all()
            print(f"Generated {len(generated)} sounds to: {sfx_dir}")

            for name in generated:
                print(f"  - {name}.wav")

            return 0

        else:
            print("Usage: python -m src.cli sound <project> library [options]")
            print("\nOptions:")
            print("  --list       List all available sounds")
            print("  --generate   Generate all sound effect files")
            return 1

    else:
        print(f"Unknown sound command: {args.sound_command}")
        return 1

    return 0


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Video Explainer Pipeline CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--projects-dir",
        default="projects",
        help="Path to projects directory (default: projects)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # list command
    list_parser = subparsers.add_parser("list", help="List all projects")
    list_parser.set_defaults(func=cmd_list)

    # info command
    info_parser = subparsers.add_parser("info", help="Show project information")
    info_parser.add_argument("project", help="Project ID")
    info_parser.set_defaults(func=cmd_info)

    # create command
    create_parser = subparsers.add_parser("create", help="Create a new project")
    create_parser.add_argument("project_id", help="Project ID (used as directory name)")
    create_parser.add_argument("--title", help="Project title")
    create_parser.add_argument("--description", help="Project description")
    create_parser.set_defaults(func=cmd_create)

    # voiceover command
    voiceover_parser = subparsers.add_parser("voiceover", help="Generate voiceovers")
    voiceover_parser.add_argument("project", help="Project ID")
    voiceover_parser.add_argument(
        "--provider",
        choices=["elevenlabs", "edge", "mock", "manual"],
        help="TTS provider to use (manual = import your own recordings)",
    )
    voiceover_parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock TTS (for testing)",
    )
    voiceover_parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue even if some scenes fail",
    )
    voiceover_parser.add_argument(
        "--export-script",
        action="store_true",
        help="Export a recording script for manual voiceover recording",
    )
    voiceover_parser.add_argument(
        "--output", "-o",
        help="Output path for recording script (with --export-script)",
    )
    voiceover_parser.add_argument(
        "--audio-dir",
        help="Directory containing recorded audio files (required with --provider manual)",
    )
    voiceover_parser.add_argument(
        "--whisper-model",
        choices=["tiny", "base", "small", "medium", "large"],
        default="base",
        help="Whisper model size for transcription (default: base)",
    )
    voiceover_parser.add_argument(
        "--no-sync",
        action="store_true",
        help="Don't auto-sync storyboard durations with voiceover durations",
    )
    voiceover_parser.set_defaults(func=cmd_voiceover)

    # storyboard command
    storyboard_parser = subparsers.add_parser("storyboard", help="Generate or view storyboard")
    storyboard_parser.add_argument("project", help="Project ID")
    storyboard_parser.add_argument(
        "--view",
        action="store_true",
        help="View existing storyboard instead of generating",
    )
    storyboard_parser.set_defaults(func=cmd_storyboard)

    # script command
    script_parser = subparsers.add_parser("script", help="Generate script from input documents")
    script_parser.add_argument("project", help="Project ID")
    script_parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock LLM (for testing)",
    )
    script_parser.add_argument(
        "--duration",
        type=int,
        help="Target duration in seconds",
    )
    script_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed output",
    )
    script_parser.set_defaults(func=cmd_script)

    # narration command
    narration_parser = subparsers.add_parser("narration", help="Generate narrations for a project")
    narration_parser.add_argument("project", help="Project ID")
    narration_parser.add_argument(
        "--topic",
        help="Topic to generate narrations for (default: project title)",
    )
    narration_parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock narrations (for testing)",
    )
    narration_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing narrations",
    )
    narration_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed output",
    )
    narration_parser.set_defaults(func=cmd_narration)

    # render command
    render_parser = subparsers.add_parser("render", help="Render video")
    render_parser.add_argument("project", help="Project ID")
    render_parser.add_argument(
        "--preview",
        action="store_true",
        help="Quick preview render",
    )
    render_parser.add_argument(
        "--resolution", "-r",
        choices=["4k", "1440p", "1080p", "720p", "480p"],
        default="1080p",
        help="Output resolution (default: 1080p)",
    )
    render_parser.set_defaults(func=cmd_render)

    # feedback command
    feedback_parser = subparsers.add_parser(
        "feedback",
        help="Process or view feedback for a project",
    )
    feedback_parser.add_argument("project", help="Project ID")

    feedback_subparsers = feedback_parser.add_subparsers(
        dest="feedback_command",
        help="Feedback commands",
    )

    # feedback add
    feedback_add_parser = feedback_subparsers.add_parser(
        "add",
        help="Add and process new feedback",
    )
    feedback_add_parser.add_argument(
        "feedback_text",
        help="The feedback text (natural language)",
    )
    feedback_add_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Analyze feedback without applying changes",
    )

    # feedback list
    feedback_subparsers.add_parser(
        "list",
        help="List all feedback for the project",
    )

    # feedback show
    feedback_show_parser = feedback_subparsers.add_parser(
        "show",
        help="Show details of a feedback item",
    )
    feedback_show_parser.add_argument(
        "feedback_id",
        help="Feedback ID (e.g., fb_0001_1234567890)",
    )

    feedback_parser.set_defaults(func=cmd_feedback)

    # sound command
    sound_parser = subparsers.add_parser(
        "sound",
        help="Sound design: generate SFX library for Remotion",
    )
    sound_parser.add_argument("project", help="Project ID")

    sound_subparsers = sound_parser.add_subparsers(
        dest="sound_command",
        help="Sound commands",
    )

    # sound library
    sound_library_parser = sound_subparsers.add_parser(
        "library",
        help="Generate/manage SFX library",
    )
    sound_library_parser.add_argument(
        "--list",
        action="store_true",
        help="List all available sounds",
    )
    sound_library_parser.add_argument(
        "--generate",
        action="store_true",
        help="Generate all SFX files to project's sfx/ directory",
    )
    sound_library_parser.add_argument(
        "--download",
        action="store_true",
        help="Alias for --generate (for backwards compatibility)",
    )

    sound_parser.set_defaults(func=cmd_sound)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
