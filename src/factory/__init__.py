"""
Shorts Factory - High-quality Varun Mayya style shorts generator.

This module provides the core architecture for evidence-based short-form video production:
- ArtifactStore: Canonical store for all outputs (scripts, proofs, screenshots)
- Director: Non-linear orchestrator that loops, assigns, checks, iterates
- ApprovalGate: Hard gates requiring explicit human approval
- Renderer: Only consumes locked/finalized artifacts

Architecture:
    Director Loop → Agents Write to Store → Approval Gate → Lock → Render
"""

from src.factory.artifact_store import ArtifactStore, Artifact, ArtifactType
from src.factory.approval_gate import ApprovalGate, ApprovalStatus
from src.factory.director import Director, DirectorState
from src.factory.project import ShortsFactoryProject

__all__ = [
    "ArtifactStore",
    "Artifact",
    "ArtifactType",
    "ApprovalGate",
    "ApprovalStatus",
    "Director",
    "DirectorState",
    "ShortsFactoryProject",
]
