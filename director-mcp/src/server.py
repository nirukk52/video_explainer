#!/usr/bin/env python3
"""
Director MCP Server - Shorts Factory API

This MCP server provides the full Shorts Factory pipeline:

Core Skills (Script Analysis):
1. plan_short: Transform topics into scripted scenes
2. analyze_hook: Evaluate and improve the first 3 seconds
3. generate_beat_sheet: Create timed visual beats with stakes escalation
4. validate_retention: Score retention potential and flag drop-off risks

Factory Tools (Project Management):
5. factory_create_project: Create a new shorts project
6. factory_get_status: Get project status and pending approvals
7. factory_approve_stage: Approve a pipeline stage gate
8. factory_get_artifacts: Get project artifacts
9. factory_search_evidence: Search for evidence URLs (Exa.ai)
10. factory_capture_screenshots: Capture screenshots (Browserbase)

Usage:
    # stdio transport (local)
    python -m src.server

    # HTTP transport (remote)
    python -m src.server --http --port 8001
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from .models import (
    AnalyzeHookInput,
    GenerateBeatSheetInput,
    PlanShortInput,
    ValidateRetentionInput,
)
from .skills import analyze_hook, generate_beat_sheet, plan_short, validate_retention


def _parse_port() -> int:
    """Parse port from command line args."""
    for i, arg in enumerate(sys.argv):
        if arg == "--port" and i + 1 < len(sys.argv):
            return int(sys.argv[i + 1])
    return 8001  # default port


# Initialize the MCP server with port config for HTTP mode
_port = _parse_port() if "--http" in sys.argv else 8000
mcp = FastMCP("director_mcp", host="0.0.0.0", port=_port)

# Global project storage (in-memory for now, persisted to disk)
_active_projects: dict = {}
_output_dir = Path(os.getenv("SHORTS_OUTPUT_DIR", "output"))


# ============================================================================
# FACTORY INPUT MODELS
# ============================================================================


class CreateProjectInput(BaseModel):
    """Input for creating a new shorts factory project."""
    
    topic: str = Field(
        ...,
        description="The topic/claim for the short (e.g., 'DeepSeek pricing is crashing the AI market')",
        min_length=5,
    )
    duration_seconds: int = Field(
        default=45,
        description="Target duration in seconds (15-60 typical for shorts)",
        ge=15,
        le=120,
    )
    auto_approve: bool = Field(
        default=False,
        description="If True, automatically approve all gates (testing mode)",
    )


class GetStatusInput(BaseModel):
    """Input for getting project status."""
    
    project_id: str = Field(..., description="Project ID to get status for")


class ApproveStageInput(BaseModel):
    """Input for approving a pipeline stage."""
    
    project_id: str = Field(..., description="Project ID")
    gate_id: str = Field(
        ...,
        description="Gate to approve: script_approval, evidence_urls_approval, screenshots_approval, render_approval",
    )
    user_id: str = Field(default="mcp_user", description="User ID for audit trail")
    feedback: Optional[str] = Field(default=None, description="Optional feedback")


class RejectStageInput(BaseModel):
    """Input for rejecting a pipeline stage."""
    
    project_id: str = Field(..., description="Project ID")
    gate_id: str = Field(..., description="Gate to reject")
    user_id: str = Field(default="mcp_user", description="User ID for audit trail")
    reason: str = Field(..., description="Reason for rejection (required)")


class GetArtifactsInput(BaseModel):
    """Input for getting project artifacts."""
    
    project_id: str = Field(..., description="Project ID")
    artifact_type: Optional[str] = Field(
        default=None,
        description="Filter by type: script, evidence_url, screenshot, render_manifest",
    )


class SearchEvidenceInput(BaseModel):
    """Input for searching evidence URLs."""
    
    project_id: str = Field(..., description="Project ID")
    query: Optional[str] = Field(
        default=None,
        description="Optional custom search query (uses script evidence needs if not provided)",
    )


@mcp.tool(
    name="director_plan_short",
    annotations={
        "title": "Plan Short-Form Video",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def director_plan_short(params: PlanShortInput) -> str:
    """
    Create a complete short-form video script from a topic.

    Transforms any topic into a Varun Mayya-style script with:
    - Hook (first 3 seconds, scroll-stopper)
    - Evidence scenes (proof shots with visuals)
    - Analysis (avatar explaining implications)
    - CTA/Close (final punch)

    Args:
        params (PlanShortInput): Input parameters containing:
            - topic (str): The topic to create a short about
            - style (VideoStyle): Style preset (varun_mayya, johnny_harris, generic)
            - duration_seconds (int): Target duration (15-60s typical)
            - evidence_urls (Optional[list]): URLs to use as evidence sources
            - num_scenes (int): Number of scenes to generate (4-8 typical)

    Returns:
        str: JSON-formatted ScriptOutput with scenes, visual plans, and evidence needs.

    Examples:
        - "Create a 45-second short about DeepSeek's pricing crash"
        - "Plan a 30-second explainer on why NVIDIA stock is up"
    """
    try:
        result = await plan_short(params)
        return json.dumps(result.model_dump(), indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool(
    name="director_analyze_hook",
    annotations={
        "title": "Analyze Video Hook",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def director_analyze_hook(params: AnalyzeHookInput) -> str:
    """
    Evaluate the hook (first 3 seconds) of a script for scroll-stopping potential.

    Analyzes:
    - Pattern interrupt strength (weak/moderate/strong)
    - Specificity of claims (numbers, names, outcomes)
    - Visual-audio match
    - Open loop creation

    Args:
        params (AnalyzeHookInput): Input parameters containing:
            - script_json (str): Script content as JSON string or file path
            - scene_id (int): Which scene to analyze (default: 1)

    Returns:
        str: JSON-formatted HookAnalysis with score, suggestions, and improved hook.

    Examples:
        - Analyze hook: "Is my opening strong enough to stop scrolling?"
        - Improve hook: "How can I make my first 3 seconds more engaging?"
    """
    try:
        result = await analyze_hook(params)
        return json.dumps(result.model_dump(), indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool(
    name="director_generate_beats",
    annotations={
        "title": "Generate Beat Sheet",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def director_generate_beats(params: GenerateBeatSheetInput) -> str:
    """
    Break a script into timed visual beats with escalating stakes.

    Creates a beat sheet with:
    - Time ranges for each beat (5-7 seconds typical)
    - Beat types (hook, setup, proof, escalation, cta)
    - Stakes level (attention → credibility → consequence → action)
    - Visual specifications

    Args:
        params (GenerateBeatSheetInput): Input parameters containing:
            - script_json (str): Script content as JSON string or file path
            - beat_interval_seconds (int): Target beat interval (5-7s typical)

    Returns:
        str: JSON-formatted BeatSheet with beats, stakes curve, and pacing score.

    Examples:
        - "Break my script into beats for editing"
        - "What's the pacing structure of my video?"
    """
    try:
        result = await generate_beat_sheet(params)
        return json.dumps(result.model_dump(), indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool(
    name="director_validate_retention",
    annotations={
        "title": "Validate Retention Potential",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def director_validate_retention(params: ValidateRetentionInput) -> str:
    """
    Score a script's retention potential and identify drop-off risks.

    Evaluates:
    - Visual change frequency (target: 2-4 seconds)
    - Stakes escalation (must be ascending)
    - Drop-off risks (timestamps with severity)
    - Predicted average view percentage

    Args:
        params (ValidateRetentionInput): Input parameters containing:
            - script_json (str): Script content as JSON string or file path
            - target_retention_pct (int): Target avg view % (default: 70%)

    Returns:
        str: JSON-formatted RetentionValidation with score, risks, recommendations.

    Examples:
        - "Will viewers watch to the end?"
        - "Where might viewers drop off?"
        - "How does my script compare to top performers?"
    """
    try:
        result = await validate_retention(params)
        return json.dumps(result.model_dump(), indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ============================================================================
# FACTORY TOOLS
# ============================================================================


def _get_or_create_project(project_id: str):
    """Get project from cache or load from disk."""
    if project_id in _active_projects:
        return _active_projects[project_id]
    
    # Try to load from disk
    try:
        # Import here to avoid circular imports
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from src.factory.project import ShortsFactoryProject
        
        project = ShortsFactoryProject.load(project_id, _output_dir)
        _active_projects[project_id] = project
        return project
    except Exception:
        return None


@mcp.tool(
    name="factory_create_project",
    annotations={
        "title": "Create Shorts Factory Project",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def factory_create_project(params: CreateProjectInput) -> str:
    """
    Create a new Shorts Factory project.
    
    Initializes a new project with:
    - Artifact store for canonical storage
    - Approval gates for human checkpoints
    - Director for non-linear orchestration
    
    The project will generate a script and wait at the first approval gate.
    
    Args:
        params: Project creation parameters (topic, duration, auto_approve)
    
    Returns:
        JSON with project_id and initial status
    """
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from src.factory.project import ShortsFactoryProject
        
        project = ShortsFactoryProject.create(
            topic=params.topic,
            output_dir=_output_dir,
            auto_approve=params.auto_approve,
        )
        project.duration_seconds = params.duration_seconds
        
        # Store in cache
        _active_projects[project.project_id] = project
        
        # Start the pipeline (will stop at first gate unless auto_approve)
        result = await project.run()
        
        return json.dumps({
            "project_id": project.project_id,
            "topic": params.topic,
            "status": result,
        }, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool(
    name="factory_get_status",
    annotations={
        "title": "Get Project Status",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def factory_get_status(params: GetStatusInput) -> str:
    """
    Get the current status of a Shorts Factory project.
    
    Returns:
    - Current pipeline state
    - Pending approval gates
    - Artifact summary
    - Whether ready for render
    
    Args:
        params: GetStatusInput with project_id
    
    Returns:
        JSON with full project status
    """
    try:
        project = _get_or_create_project(params.project_id)
        if not project:
            return json.dumps({"error": f"Project {params.project_id} not found"})
        
        status = project.get_status()
        return json.dumps(status, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool(
    name="factory_approve_stage",
    annotations={
        "title": "Approve Pipeline Stage",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
async def factory_approve_stage(params: ApproveStageInput) -> str:
    """
    Approve a pipeline stage gate.
    
    This is a HARD GATE - the pipeline will not progress without approval.
    After approval, related artifacts are locked (immutable).
    
    Available gates:
    - script_approval: Approve the generated script
    - evidence_urls_approval: Approve discovered evidence URLs
    - screenshots_approval: Approve captured screenshots
    - render_approval: Final approval before render
    
    Args:
        params: ApproveStageInput with project_id, gate_id, user_id
    
    Returns:
        JSON with updated status
    """
    try:
        project = _get_or_create_project(params.project_id)
        if not project:
            return json.dumps({"error": f"Project {params.project_id} not found"})
        
        # Map gate_id to approval method
        gate_methods = {
            "script_approval": lambda: project.approve_script(params.user_id, params.feedback),
            "evidence_urls_approval": lambda: project.approve_evidence(params.user_id),
            "screenshots_approval": lambda: project.approve_screenshots(params.user_id),
            "render_approval": lambda: project.approve_render(params.user_id),
        }
        
        if params.gate_id not in gate_methods:
            return json.dumps({"error": f"Unknown gate: {params.gate_id}"})
        
        result = gate_methods[params.gate_id]()
        
        # Resume pipeline after approval
        resume_result = await project.resume()
        
        return json.dumps({
            "approved": True,
            "gate_id": params.gate_id,
            "status": resume_result,
        }, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool(
    name="factory_reject_stage",
    annotations={
        "title": "Reject Pipeline Stage",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
async def factory_reject_stage(params: RejectStageInput) -> str:
    """
    Reject a pipeline stage gate.
    
    Rejection REQUIRES a reason. After rejection, the pipeline can be
    re-run to generate new artifacts.
    
    Args:
        params: RejectStageInput with project_id, gate_id, user_id, reason
    
    Returns:
        JSON with rejection status
    """
    try:
        project = _get_or_create_project(params.project_id)
        if not project:
            return json.dumps({"error": f"Project {params.project_id} not found"})
        
        # Map gate_id to rejection method
        gate_methods = {
            "script_approval": lambda: project.reject_script(params.user_id, params.reason),
            "evidence_urls_approval": lambda: project.reject_evidence(params.user_id, params.reason),
            "screenshots_approval": lambda: project.reject_screenshots(params.user_id, params.reason),
        }
        
        if params.gate_id not in gate_methods:
            return json.dumps({"error": f"Unknown gate: {params.gate_id}"})
        
        result = gate_methods[params.gate_id]()
        
        return json.dumps({
            "rejected": True,
            "gate_id": params.gate_id,
            "reason": params.reason,
            "status": project.get_status(),
        }, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool(
    name="factory_get_artifacts",
    annotations={
        "title": "Get Project Artifacts",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def factory_get_artifacts(params: GetArtifactsInput) -> str:
    """
    Get artifacts from a Shorts Factory project.
    
    Artifacts include:
    - script: Generated video script
    - evidence_url: Discovered evidence URLs
    - screenshot: Captured screenshots
    - render_manifest: Final render specification
    
    Args:
        params: GetArtifactsInput with project_id and optional type filter
    
    Returns:
        JSON array of artifacts
    """
    try:
        project = _get_or_create_project(params.project_id)
        if not project:
            return json.dumps({"error": f"Project {params.project_id} not found"})
        
        # Import ArtifactType here
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from src.factory.artifact_store import ArtifactType
        
        if params.artifact_type:
            try:
                artifact_type = ArtifactType(params.artifact_type)
                artifacts = project.get_artifacts(artifact_type)
            except ValueError:
                return json.dumps({"error": f"Unknown artifact type: {params.artifact_type}"})
        else:
            artifacts = project.get_artifacts()
        
        return json.dumps({"artifacts": artifacts}, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool(
    name="factory_get_script",
    annotations={
        "title": "Get Project Script",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def factory_get_script(params: GetStatusInput) -> str:
    """
    Get the current script from a project.
    
    Returns the latest script artifact data, useful for reviewing
    before approval.
    
    Args:
        params: GetStatusInput with project_id
    
    Returns:
        JSON script data
    """
    try:
        project = _get_or_create_project(params.project_id)
        if not project:
            return json.dumps({"error": f"Project {params.project_id} not found"})
        
        script = project.get_script()
        if not script:
            return json.dumps({"error": "No script generated yet"})
        
        return json.dumps({"script": script}, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool(
    name="factory_get_render_manifest",
    annotations={
        "title": "Get Render Manifest",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def factory_get_render_manifest(params: GetStatusInput) -> str:
    """
    Get the render manifest for a project.
    
    Only returns a manifest if ALL required artifacts are locked:
    - Script must be locked
    - All evidence screenshots must be locked
    
    This ensures render only uses finalized, approved content.
    
    Args:
        params: GetStatusInput with project_id
    
    Returns:
        JSON render manifest or error if not ready
    """
    try:
        project = _get_or_create_project(params.project_id)
        if not project:
            return json.dumps({"error": f"Project {params.project_id} not found"})
        
        ready, missing = project.is_render_ready()
        if not ready:
            return json.dumps({
                "error": "Not ready for render",
                "missing": missing,
            })
        
        manifest = project.get_render_manifest()
        return json.dumps({"manifest": manifest}, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)})


# ============================================================================
# EVAL/SCORING TOOLS
# ============================================================================


class ScoreTemplateInput(BaseModel):
    """Input for scoring a completed template."""
    
    project_id: str = Field(..., description="Project ID to score")


class GetWinnersInput(BaseModel):
    """Input for getting similar winning templates."""
    
    topic: str = Field(..., description="Topic to search for similar winners")
    limit: int = Field(default=3, description="Max number of winners to return", ge=1, le=10)


@mcp.tool(
    name="eval_score_template",
    annotations={
        "title": "Score Completed Template",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def eval_score_template(params: ScoreTemplateInput) -> str:
    """
    Score a completed template to determine if it's a winner.
    
    Scoring dimensions:
    - Hook Score (25%): Scroll-stopping potential
    - Retention Score (25%): Predicted avg view percentage
    - Pacing Score (20%): Stakes escalation and beat timing
    - Evidence Score (15%): Screenshot quality and relevance
    - User Rating (15%): Upvote/downvote history
    
    Templates scoring >= 7.0 become winners and are added to the library.
    
    Args:
        params: ScoreTemplateInput with project_id
    
    Returns:
        JSON with overall score, breakdown, and winner status
    """
    try:
        project = _get_or_create_project(params.project_id)
        if not project:
            return json.dumps({"error": f"Project {params.project_id} not found"})
        
        # Import eval service
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from src.eval.scorer import TemplateScorer
        from src.eval.winner_library import WinnerLibrary
        
        scorer = TemplateScorer(project.store)
        score = await scorer.score_template(params.project_id)
        
        # If winner, add to library
        if score.is_winner:
            library = WinnerLibrary()
            script = project.get_script()
            if script:
                await library.add_winner(
                    project_id=params.project_id,
                    topic=score.topic or project.topic,
                    script_json=script,
                    score=score.overall_score,
                )
        
        return json.dumps(score.to_dict(), indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool(
    name="eval_get_similar_winners",
    annotations={
        "title": "Get Similar Winners",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def eval_get_similar_winners(params: GetWinnersInput) -> str:
    """
    Get similar winning templates for a topic.
    
    Uses embedding similarity search to find templates with similar topics.
    Useful for few-shot prompting in script generation.
    
    Args:
        params: GetWinnersInput with topic and limit
    
    Returns:
        JSON array of similar winning templates
    """
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from src.eval.winner_library import WinnerLibrary
        
        library = WinnerLibrary()
        winners = await library.get_similar_winners(params.topic, params.limit)
        
        return json.dumps({
            "winners": [w.to_dict() for w in winners],
            "count": len(winners),
        }, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)})


def main():
    """Run the Director MCP server."""
    # Check for HTTP transport flag
    if "--http" in sys.argv:
        print(f"Starting Director MCP on HTTP port {_port}...")
        mcp.run(transport="streamable-http")
    else:
        # Default: stdio transport
        mcp.run()


if __name__ == "__main__":
    main()
