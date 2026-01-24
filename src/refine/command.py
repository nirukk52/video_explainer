"""
CLI command for video refinement.

Implements the `refine` command for the video explainer CLI.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from ..project import Project, load_project
from .models import (
    RefinementPhase,
    RefinementResult,
    GapAnalysisResult,
    NarrationRefinementResult,
    ScriptPatch,
    ScriptPatchType,
    AddScenePatch,
    ModifyScenePatch,
    ExpandScenePatch,
    AddBridgePatch,
    UpdateVisualCuePatch,
)
from .validation import validate_project_sync, ProjectValidator
from .visual import VisualInspector, ClaudeCodeVisualInspector
from .script import ScriptAnalyzer, ScriptRefiner
from .visual_cue import VisualCueRefiner


def cmd_refine(args: argparse.Namespace) -> int:
    """
    Refine a video project to high quality standards.

    This command implements a 3-phase refinement process:
    - Phase 1 (analyze): Compare source material against script to identify gaps
    - Phase 2 (script): Refine narrations and update script structure
    - Phase 3 (visual): Inspect and refine scene visuals

    Returns:
        0 on success, 1 on error.
    """
    # Load project
    try:
        project_path = Path(args.projects_dir) / args.project
        project = load_project(project_path)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print(f"\n🎬 Video Refinement: {project.title}")
    print(f"   Project: {project.id}")
    print(f"   Path: {project.root_dir}")

    # Determine which phase to run
    phase = args.phase if hasattr(args, "phase") and args.phase else "visual"

    # Validate project sync first
    if not args.skip_validation:
        sync_status = validate_project_sync(project)
        if not sync_status.is_synced:
            print("\n⚠️  Project files are out of sync:")
            for issue in sync_status.issues:
                print(f"   - {issue.description}")
                if issue.suggestion:
                    print(f"     💡 {issue.suggestion}")

            if not args.force:
                print("\nRun with --force to continue anyway, or fix the sync issues first.")
                return 1
            print("\n--force specified, continuing with out-of-sync project...")

    # Route to appropriate phase
    if phase == "analyze":
        return _run_analyze_phase(project, args)
    elif phase == "script":
        return _run_script_phase(project, args)
    elif phase == "visual":
        return _run_visual_phase(project, args)
    elif phase == "visual-cue":
        return _run_visual_cue_phase(project, args)
    elif phase == "sync":
        return _run_sync_phase(project, args)
    else:
        print(f"Error: Unknown phase '{phase}'", file=sys.stderr)
        return 1


def _run_analyze_phase(project: Project, args: argparse.Namespace) -> int:
    """Run Phase 1: Gap analysis."""
    print("\n📊 Phase 1: Analyze (Gap Analysis)")
    print("   " + "=" * 40)

    verbose = not getattr(args, "quiet", False)
    analyzer = ScriptAnalyzer(project=project, verbose=verbose)

    # Run analysis
    result = analyzer.analyze()

    # Print results
    _print_gap_analysis(result)

    # Save results
    output_path = analyzer.save_result(result)
    print(f"\n   📄 Results saved to: {output_path}")

    # Return based on critical gaps
    if result.has_critical_gaps:
        print("\n   ⚠️  Critical gaps found. Consider addressing these before proceeding.")
        return 1

    return 0


def _print_gap_analysis(result: GapAnalysisResult) -> None:
    """Print gap analysis results."""
    print("\n" + "=" * 60)
    print("📋 GAP ANALYSIS RESULTS")
    print("=" * 60)

    print(f"\n   Source: {result.source_file}")
    print(f"   Coverage Score: {result.overall_coverage_score:.1f}%")
    print(f"   Total Concepts: {len(result.concepts)}")

    # Show covered concepts count
    covered = [c for c in result.concepts if c.is_covered]
    if covered:
        print(f"\n   ✅ Covered Concepts ({len(covered)}):")
        for cov in covered[:5]:  # Show first 5
            depth_icon = "🎯" if cov.depth.value == "deep_dive" else "📖" if cov.depth.value == "explained" else "📌"
            print(f"      {depth_icon} {cov.concept.name} ({cov.depth.value})")
        if len(covered) > 5:
            print(f"      ... and {len(covered) - 5} more")

    if result.missing_concepts:
        print(f"\n   ❌ Missing Concepts - Need to Add ({len(result.missing_concepts)}):")
        for concept in result.missing_concepts:
            print(f"      - {concept}")

    if result.shallow_concepts:
        print(f"\n   ⚠️  Shallow Coverage - Need Deeper Explanation ({len(result.shallow_concepts)}):")
        for concept in result.shallow_concepts:
            print(f"      - {concept}")

    # Show intentional omissions
    if result.intentionally_omitted_concepts:
        print(f"\n   📋 Intentionally Omitted ({len(result.intentionally_omitted_concepts)}):")
        for concept, reason in result.intentionally_omitted_concepts:
            reason_display = reason.replace("_", " ")
            print(f"      - {concept} ({reason_display})")
        if result.intentional_omissions_summary:
            print(f"\n      Summary: {result.intentional_omissions_summary}")

    if result.narrative_gaps:
        print(f"\n   🔗 Narrative Gaps ({len(result.narrative_gaps)}):")
        for gap in result.narrative_gaps:
            severity_icon = "🔴" if gap.severity == "high" else "🟡" if gap.severity == "medium" else "🟢"
            print(f"      {severity_icon} {gap.from_scene_title} → {gap.to_scene_title}")
            print(f"         {gap.gap_description}")

    if result.suggested_scenes:
        print(f"\n   💡 Suggested New Scenes ({len(result.suggested_scenes)}):")
        for scene in result.suggested_scenes:
            print(f"      - [{scene.suggested_position}] {scene.title}")
            print(f"        Reason: {scene.reason}")

    # Show generated patches
    if result.patches:
        print(f"\n   🔧 Generated Patches ({len(result.patches)}):")
        for i, patch in enumerate(result.patches, 1):
            priority_icon = "🔴" if patch.priority == "critical" else "🟡" if patch.priority == "high" else "🟢"
            print(f"      {priority_icon} [{i}] {patch.patch_type.value}: {patch.reason[:60]}...")

    if result.analysis_notes:
        print(f"\n   📝 Notes: {result.analysis_notes}")

    print("\n" + "=" * 60)


def _run_script_phase(project: Project, args: argparse.Namespace) -> int:
    """Run Phase 2: Script refinement (apply patches)."""
    print("\n📝 Phase 2: Script Refinement")
    print("   " + "=" * 40)

    verbose = not getattr(args, "quiet", False)
    batch_approve = getattr(args, "batch_approve", False)
    refiner = ScriptRefiner(project=project, verbose=verbose)

    # Run analysis to get all patches (Phase 1 patches + storytelling patches)
    all_patches, narration_result = refiner.refine()

    # Print analysis results
    _print_narration_analysis(narration_result)

    # Save narration analysis
    output_path = refiner.save_result(narration_result)
    print(f"\n   📄 Analysis saved to: {output_path}")

    if not all_patches:
        print("\n   ✅ No patches to apply. Script is already in good shape!")
        return 0

    # Print patch summary
    print(f"\n   🔧 Total Patches to Apply: {len(all_patches)}")
    _print_patch_summary(all_patches)

    # Apply patches
    if batch_approve:
        # Batch approval mode: apply all patches
        print("\n   --batch-approve specified, applying all patches...")
        applied = _apply_all_patches(refiner, all_patches)
        print(f"\n   ✅ Applied {applied}/{len(all_patches)} patches.")
    else:
        # Interactive mode: ask for each patch
        applied = _interactive_patches(refiner, all_patches)
        print(f"\n   ✅ Applied {applied}/{len(all_patches)} patches.")

    if applied > 0:
        print("\n   📢 Script and narrations have been updated.")
        print("   💡 Next steps:")
        print("      1. Review changes in script/script.json and narration/narrations.json")
        print("      2. Run 'voiceover' command to regenerate audio")
        print("      3. Run 'scenes' command to regenerate visual components")

    return 0


def _print_narration_analysis(result: NarrationRefinementResult) -> None:
    """Print narration analysis results."""
    print("\n" + "=" * 60)
    print("📋 NARRATION ANALYSIS RESULTS")
    print("=" * 60)

    print(f"\n   Overall Storytelling Score: {result.overall_storytelling_score:.1f}/10")
    print(f"   Total Issues Found: {result.total_issues_found}")
    print(f"   Scenes Needing Revision: {len(result.scenes_needing_revision)}")

    for analysis in result.scene_analyses:
        status = "⚠️" if analysis.needs_revision else "✅"
        print(f"\n   {status} Scene: {analysis.scene_title}")
        print(f"      Score: {analysis.scores.overall:.1f}/10")
        print(f"      Words: {analysis.word_count}/{analysis.expected_word_count} ({analysis.length_ratio:.0%})")

        if analysis.issues:
            for issue in analysis.issues:
                severity_icon = "🔴" if issue.severity == "high" else "🟡" if issue.severity == "medium" else "🟢"
                print(f"      {severity_icon} [{issue.issue_type.value}] {issue.description}")

    if result.high_priority_scenes:
        print(f"\n   🔴 High Priority Scenes: {', '.join(result.high_priority_scenes)}")

    print("\n" + "=" * 60)


def _print_patch_summary(patches: list[ScriptPatch]) -> None:
    """Print a summary of patches to be applied."""
    # Group patches by type
    by_type: dict[str, list[ScriptPatch]] = {}
    for patch in patches:
        patch_type = patch.patch_type.value
        if patch_type not in by_type:
            by_type[patch_type] = []
        by_type[patch_type].append(patch)

    for patch_type, type_patches in by_type.items():
        print(f"\n   {patch_type} ({len(type_patches)}):")
        for patch in type_patches[:3]:  # Show first 3
            priority_icon = "🔴" if patch.priority == "critical" else "🟡" if patch.priority == "high" else "🟢"
            print(f"      {priority_icon} {patch.reason[:50]}...")
        if len(type_patches) > 3:
            print(f"      ... and {len(type_patches) - 3} more")


def _apply_all_patches(refiner: ScriptRefiner, patches: list[ScriptPatch]) -> int:
    """Apply all patches (batch mode).

    Args:
        refiner: The ScriptRefiner instance
        patches: List of patches to apply

    Returns:
        Number of patches applied
    """
    applied = 0
    for patch in patches:
        if refiner.apply_patch(patch):
            applied += 1
    return applied


def _interactive_patches(refiner: ScriptRefiner, patches: list[ScriptPatch]) -> int:
    """Interactively approve and apply patches one by one.

    Args:
        refiner: The ScriptRefiner instance
        patches: List of patches to apply

    Returns:
        Number of patches applied
    """
    applied = 0

    for i, patch in enumerate(patches, 1):
        print("\n" + "-" * 60)
        print(f"   Patch {i}/{len(patches)}")
        _print_patch_details(patch)

        # Ask for approval
        try:
            response = input("\n   Apply this patch? [y/N/q (quit)]: ").strip().lower()
        except EOFError:
            # Non-interactive mode - skip
            print("   (Non-interactive mode, skipping)")
            continue

        if response == "q":
            print("   Stopping patch application.")
            break
        elif response == "y":
            if refiner.apply_patch(patch):
                print("   ✅ Patch applied.")
                applied += 1
            else:
                print("   ❌ Failed to apply patch.")
        else:
            print("   Skipped.")

    return applied


def _print_patch_details(patch: ScriptPatch) -> None:
    """Print detailed information about a patch."""
    priority_icon = "🔴" if patch.priority == "critical" else "🟡" if patch.priority == "high" else "🟢"
    print(f"   {priority_icon} Type: {patch.patch_type.value}")
    print(f"   Priority: {patch.priority}")
    print(f"   Reason: {patch.reason}")

    if isinstance(patch, AddScenePatch):
        print(f"\n   New Scene: {patch.title}")
        print(f"   Insert after: {patch.insert_after_scene_id or '(beginning)'}")
        print(f"   Duration: {patch.duration_seconds}s")
        narration_preview = patch.narration[:200] + "..." if len(patch.narration) > 200 else patch.narration
        print(f"\n   Narration:\n   \"{narration_preview}\"")

    elif isinstance(patch, ModifyScenePatch):
        print(f"\n   Scene: {patch.scene_id}")
        print(f"   Field: {patch.field_name}")
        old_preview = patch.old_value[:100] + "..." if len(patch.old_value) > 100 else patch.old_value
        new_preview = patch.new_value[:100] + "..." if len(patch.new_value) > 100 else patch.new_value
        print(f"\n   Before:\n   \"{old_preview}\"")
        print(f"\n   After:\n   \"{new_preview}\"")

    elif isinstance(patch, ExpandScenePatch):
        print(f"\n   Scene: {patch.scene_id}")
        print(f"   Concepts to add: {', '.join(patch.concepts_to_add)}")
        print(f"   Additional duration: +{patch.additional_duration_seconds}s")
        expanded_preview = patch.expanded_narration[:200] + "..." if len(patch.expanded_narration) > 200 else patch.expanded_narration
        print(f"\n   Expanded narration:\n   \"{expanded_preview}\"")

    elif isinstance(patch, AddBridgePatch):
        print(f"\n   Bridge: {patch.from_scene_id} → {patch.to_scene_id}")
        print(f"   Type: {patch.bridge_type}")
        print(f"   Modify scene: {patch.modify_scene_id}")
        new_preview = patch.new_text[:200] + "..." if len(patch.new_text) > 200 else patch.new_text
        print(f"\n   New text:\n   \"{new_preview}\"")


def _run_visual_phase(project: Project, args: argparse.Namespace) -> int:
    """Run Phase 3: Visual refinement."""
    print("\n🎨 Phase 3: Visual Refinement")
    print("   " + "=" * 40)

    # Determine which scene(s) to refine
    scene_index = getattr(args, "scene", None)
    use_legacy = getattr(args, "legacy", False)

    # Get scene count from storyboard
    validator = ProjectValidator(project)
    try:
        storyboard = project.load_storyboard()
        total_scenes = len(storyboard.get("scenes", []))
    except FileNotFoundError:
        print("\n   ❌ Storyboard not found. Run 'storyboard' command first.")
        return 1

    if total_scenes == 0:
        print("\n   ❌ No scenes found in storyboard.")
        return 1

    # Create inspector (use Claude Code by default, Playwright if --legacy)
    verbose = not getattr(args, "quiet", False)
    live_output = getattr(args, "live", False)

    if use_legacy:
        # Legacy mode: use Playwright-based screenshot capture
        print("\n   📷 Using legacy Playwright-based inspection...")
        screenshots_dir = project.root_dir / "output" / "refinement_screenshots"
        inspector = VisualInspector(
            project=project,
            screenshots_dir=screenshots_dir,
            verbose=verbose,
        )
    else:
        # Default: use Claude Code with --chrome for browser-based inspection
        print("\n   🌐 Using Claude Code with browser access for visual inspection...")
        print("   (Claude Code will start Remotion, navigate frames, inspect & fix)")
        if live_output:
            print("   📺 Live output mode: streaming Claude Code output in real-time")
        inspector = ClaudeCodeVisualInspector(
            project=project,
            verbose=verbose,
            live_output=live_output,
        )

    # Collect results
    results: list = []

    if scene_index is not None:
        # Refine specific scene (convert to 0-based index)
        idx = scene_index - 1
        if idx < 0 or idx >= total_scenes:
            print(f"\n   ❌ Invalid scene number {scene_index}. Valid range: 1-{total_scenes}")
            return 1

        print(f"\n   Refining scene {scene_index} of {total_scenes}...")
        result = inspector.refine_scene(idx)
        results.append(result)
    else:
        # Refine all scenes
        print(f"\n   Refining all {total_scenes} scenes...")
        for idx in range(total_scenes):
            result = inspector.refine_scene(idx)
            results.append(result)

    # Print summary
    _print_refinement_summary(results)

    # Save results to refinement directory in project folder
    refinement_dir = project.root_dir / "refinement"
    refinement_dir.mkdir(parents=True, exist_ok=True)

    # Save per-scene results
    for result in results:
        scene_filename = f"{result.scene_id}.json"
        scene_path = refinement_dir / scene_filename
        scene_data = {
            "project_id": project.id,
            "phase": "visual",
            "scene": result.to_dict(),
        }
        with open(scene_path, "w") as f:
            json.dump(scene_data, f, indent=2)
        print(f"   📄 Scene results saved to: {scene_path}")

    # Save summary if multiple scenes
    if len(results) > 1:
        summary_path = refinement_dir / "summary.json"
        summary_data = {
            "project_id": project.id,
            "phase": "visual",
            "summary": {
                "total_scenes": len(results),
                "scenes_passed": sum(1 for r in results if r.verification_passed),
                "total_issues_found": sum(len(r.issues_found) for r in results),
                "total_fixes_applied": sum(len(r.fixes_applied) for r in results),
            },
            "scenes": [{"scene_id": r.scene_id, "passed": r.verification_passed} for r in results],
        }
        with open(summary_path, "w") as f:
            json.dump(summary_data, f, indent=2)
        print(f"   📄 Summary saved to: {summary_path}")

    # Return success if all scenes passed verification
    all_passed = all(r.verification_passed for r in results)
    return 0 if all_passed else 1


def _run_visual_cue_phase(project: Project, args: argparse.Namespace) -> int:
    """Run visual-cue refinement phase."""
    print("\n🎨 Visual Cue Refinement")
    print("   " + "=" * 40)

    verbose = not getattr(args, "quiet", False)
    apply_patches = getattr(args, "apply", False)
    scene_index = getattr(args, "scene", None)

    refiner = VisualCueRefiner(project=project, verbose=verbose)

    # Determine which scenes to analyze
    scene_indices = None
    if scene_index is not None:
        scene_indices = [scene_index - 1]  # Convert to 0-based

    # Run analysis
    result = refiner.analyze(scene_indices=scene_indices)

    if result.error_message:
        print(f"\n   ❌ Error: {result.error_message}")
        return 1

    # Print results
    _print_visual_cue_analysis(result)

    # Save results
    output_path = refiner.save_result(result)
    print(f"\n   📄 Analysis saved to: {output_path}")

    if not result.patches:
        print("\n   ✅ All visual_cues are well-specified. No updates needed!")
        return 0

    # Apply patches if requested
    if apply_patches:
        print(f"\n   🔧 Applying {len(result.patches)} patches...")
        applied = refiner.apply_patches(result.patches)
        print(f"   ✅ Applied {applied}/{len(result.patches)} patches to script.json")

        if applied > 0:
            print("\n   💡 Next steps:")
            print("      1. Review changes in script/script.json")
            print("      2. Run 'refine --phase visual' to inspect and fix scenes")
    else:
        print(f"\n   💡 Found {len(result.patches)} patches to apply.")
        print("   Run with --apply to update script.json, or review patches in the analysis file.")

    return 0


def _print_visual_cue_analysis(result) -> None:
    """Print visual cue analysis results."""
    print("\n" + "=" * 60)
    print("📋 VISUAL CUE ANALYSIS RESULTS")
    print("=" * 60)

    print(f"\n   Scenes analyzed: {result.scenes_analyzed}")
    print(f"   Scenes needing update: {result.scenes_needing_update}")

    if result.patches:
        print(f"\n   🔧 Patches to apply ({len(result.patches)}):")
        for i, patch in enumerate(result.patches, 1):
            print(f"\n   [{i}] Scene: {patch.scene_title}")
            print(f"       Reason: {patch.reason[:80]}...")
            if patch.new_visual_cue:
                desc = patch.new_visual_cue.get("description", "")[:100]
                print(f"       New description: {desc}...")
                elements = patch.new_visual_cue.get("elements", [])
                if elements:
                    print(f"       Elements: {len(elements)} items")

    if result.analysis_notes:
        print(f"\n   📝 Notes: {result.analysis_notes}")

    print("\n" + "=" * 60)


def _run_sync_phase(project: Project, args: argparse.Namespace) -> int:
    """Run sync phase: visual-voiceover synchronization."""
    print("\n🔄 Phase: Visual-Voiceover Sync")
    print("   " + "=" * 40)

    from ..sync import SyncOrchestrator

    verbose = not getattr(args, "quiet", False)
    dry_run = getattr(args, "dry_run", False)
    force = getattr(args, "force", False)
    full = getattr(args, "full", False)
    generate_map = getattr(args, "generate_map", False)
    generate_timing = getattr(args, "generate_timing", False)
    migrate_scenes = getattr(args, "migrate_scenes", False)
    scene_index = getattr(args, "scene", None)

    orchestrator = SyncOrchestrator(project=project, verbose=verbose)

    # Determine what to run
    if full or (not generate_map and not generate_timing and not migrate_scenes):
        # Full sync (default when no specific step is requested)
        scene_id = None
        if scene_index is not None:
            # Get scene_id from storyboard
            storyboard = project.load_storyboard()
            scenes = storyboard.get("scenes", [])
            if 0 < scene_index <= len(scenes):
                scene_id = scenes[scene_index - 1].get("id")

        result = orchestrator.run_full_sync(
            dry_run=dry_run,
            force=force,
            scene_id=scene_id,
        )
        return 0 if result.success else 1

    # Individual steps
    if generate_map:
        try:
            sync_map = orchestrator.generate_sync_map(force=force)
            print(f"\n   ✅ Sync map generated with {len(sync_map.scenes)} scenes")
            total_points = sum(len(s.sync_points) for s in sync_map.scenes)
            print(f"   Total sync points: {total_points}")
        except Exception as e:
            print(f"\n   ❌ Error: {e}")
            return 1

    if generate_timing:
        try:
            timing_path = orchestrator.generate_timing_file(force=force)
            print(f"\n   ✅ Timing file generated: {timing_path}")
        except Exception as e:
            print(f"\n   ❌ Error: {e}")
            return 1

    if migrate_scenes:
        try:
            scene_id = None
            if scene_index is not None:
                storyboard = project.load_storyboard()
                scenes = storyboard.get("scenes", [])
                if 0 < scene_index <= len(scenes):
                    scene_id = scenes[scene_index - 1].get("id")

            results = orchestrator.migrate_scenes(
                dry_run=dry_run,
                scene_id=scene_id,
            )
            success_count = sum(1 for p in results.values() if p.success)
            print(f"\n   ✅ Migrated {success_count}/{len(results)} scenes")
        except Exception as e:
            print(f"\n   ❌ Error: {e}")
            return 1

    return 0


def _print_refinement_summary(results: list) -> None:
    """Print a summary of refinement results."""
    print("\n" + "=" * 60)
    print("📋 REFINEMENT SUMMARY")
    print("=" * 60)

    total_issues = 0
    total_fixes = 0
    passed_count = 0

    for result in results:
        status = "✅" if result.verification_passed else "⚠️"
        issues = len(result.issues_found)
        fixes = len(result.fixes_applied)
        total_issues += issues
        total_fixes += fixes
        if result.verification_passed:
            passed_count += 1

        print(f"\n{status} Scene: {result.scene_title}")
        print(f"   Issues found: {issues}")
        print(f"   Fixes applied: {fixes}")
        if result.error_message:
            print(f"   ❌ Error: {result.error_message}")

    print("\n" + "-" * 40)
    print(f"Total scenes: {len(results)}")
    print(f"Passed: {passed_count}/{len(results)}")
    print(f"Total issues found: {total_issues}")
    print(f"Total fixes applied: {total_fixes}")
    print("=" * 60)


def add_refine_parser(subparsers: argparse._SubParsersAction) -> None:
    """
    Add the refine command parser to the CLI.

    Args:
        subparsers: The subparsers object from argparse.
    """
    refine_parser = subparsers.add_parser(
        "refine",
        help="Refine video project to professional quality",
        description="""
Refine a video project to high quality standards using a multi-phase process:

Phase 1 (analyze): Compare source material against script to identify gaps
Phase 2 (script): Refine narrations and update script structure
Phase 3 (visual): Inspect and refine scene visuals (default)
Phase 4 (visual-cue): Analyze and improve visual_cue specifications in script.json
Phase 5 (sync): Synchronize visual animations with voiceover timing

The visual phase uses AI to:
1. Parse narration into visual "beats"
2. Capture screenshots at key moments
3. Analyze against 13 quality principles
4. Generate and apply fixes
5. Verify improvements

The visual-cue phase analyzes script.json visual specifications and generates
patches to improve them (dark glass patterns, 3D depth, specific elements).

The sync phase automatically:
1. Analyzes scene code to identify sync points with voiceover
2. Generates centralized timing.ts with frame-accurate constants
3. Migrates scene code to use timing imports

Example usage:
  python -m src.cli.main refine my-project                        # Refine all scenes (visual)
  python -m src.cli.main refine my-project --scene 1              # Refine specific scene
  python -m src.cli.main refine my-project --phase analyze        # Run gap analysis
  python -m src.cli.main refine my-project --phase script         # Refine narrations
  python -m src.cli.main refine my-project --phase visual-cue     # Analyze visual_cues
  python -m src.cli.main refine my-project --phase visual-cue --apply  # Apply visual_cue patches
  python -m src.cli.main refine my-project --phase sync --full    # Full sync workflow
  python -m src.cli.main refine my-project --phase sync --generate-map  # Generate sync map only
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    refine_parser.add_argument(
        "project",
        help="Project ID to refine",
    )

    refine_parser.add_argument(
        "--phase",
        choices=["analyze", "script", "visual", "visual-cue", "sync"],
        default="visual",
        help="Refinement phase to run: analyze, script, visual (default), visual-cue, or sync",
    )

    refine_parser.add_argument(
        "--scene",
        type=int,
        help="Specific scene number to refine (1-based). If not specified, refines all scenes.",
    )

    refine_parser.add_argument(
        "--force",
        action="store_true",
        help="Continue even if project files are out of sync",
    )

    refine_parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip project sync validation",
    )

    refine_parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress progress messages",
    )

    refine_parser.add_argument(
        "--legacy",
        action="store_true",
        help="Use legacy Playwright-based screenshot capture instead of Claude Code with browser",
    )

    refine_parser.add_argument(
        "--live",
        action="store_true",
        help="Stream Claude Code output in real-time (useful for debugging)",
    )

    refine_parser.add_argument(
        "--batch-approve",
        action="store_true",
        help="Automatically approve all suggested revisions (for --phase script)",
    )

    refine_parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply patches to script.json (for --phase visual-cue)",
    )

    # Sync phase arguments
    refine_parser.add_argument(
        "--full",
        action="store_true",
        help="Run full sync workflow (for --phase sync)",
    )

    refine_parser.add_argument(
        "--generate-map",
        action="store_true",
        help="Generate sync map only (for --phase sync)",
    )

    refine_parser.add_argument(
        "--generate-timing",
        action="store_true",
        help="Generate timing.ts only (for --phase sync)",
    )

    refine_parser.add_argument(
        "--migrate-scenes",
        action="store_true",
        help="Migrate scenes to use timing imports (for --phase sync)",
    )

    refine_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying files (for --phase sync)",
    )

    refine_parser.add_argument(
        "--projects-dir",
        default="projects",
        help="Directory containing projects (default: projects)",
    )

    refine_parser.set_defaults(func=cmd_refine)
