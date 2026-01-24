"""
Evidence Reviewer Agent.

Reviews screenshots captured by the Witness agent to filter out
bad/blank/irrelevant images and identify the best variants.
"""

from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from .models import (
    CaptureFiles,
    EvidenceCapture,
    EvidenceManifest,
    VariantReview,
    VariantType,
)
from .vision import MockVisionLLM, VisionLLM, get_vision_llm

console = Console()


class EvidenceReviewer:
    """
    Reviews evidence screenshots to filter out bad images.
    
    Uses Vision LLM to analyze each screenshot variant for:
    - Blank/empty detection
    - Anchor text visibility
    - Text readability
    - Overall composition quality
    """

    def __init__(
        self,
        vision_llm: Optional[VisionLLM | MockVisionLLM] = None,
        mock: bool = False,
    ):
        """
        Initialize the Evidence Reviewer.
        
        Args:
            vision_llm: Vision LLM instance. If None, creates one.
            mock: If True and no vision_llm provided, use mock for testing.
        """
        self.vision_llm = vision_llm or get_vision_llm(mock=mock)

    def review_project(
        self,
        project_dir: Path,
        verbose: bool = True,
    ) -> EvidenceManifest:
        """
        Review all evidence in a project.
        
        Args:
            project_dir: Path to project directory (contains evidence/ folder).
            verbose: If True, print progress to console.
            
        Returns:
            Updated EvidenceManifest with review results.
        """
        evidence_dir = project_dir / "evidence"
        if not evidence_dir.exists():
            raise FileNotFoundError(f"Evidence directory not found: {evidence_dir}")
        
        # Load existing manifest
        manifest = EvidenceManifest.load(evidence_dir)
        
        if not manifest.captures:
            # Try to discover captures from files
            manifest = self._discover_captures(evidence_dir)
        
        if verbose:
            console.print(f"\n[bold]Reviewing {len(manifest.captures)} evidence captures...[/bold]\n")
        
        # Review each capture
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            disable=not verbose,
        ) as progress:
            for capture in manifest.captures:
                task = progress.add_task(f"Reviewing {capture.id}...", total=None)
                capture = self._review_capture(capture, evidence_dir)
                progress.remove_task(task)
        
        # Mark as reviewed
        manifest.reviewed = True
        
        # Save updated manifest
        manifest.save(evidence_dir)
        
        if verbose:
            self._print_summary(manifest)
        
        return manifest

    def _discover_captures(self, evidence_dir: Path) -> EvidenceManifest:
        """
        Discover captures from files when manifest is empty.
        
        Looks for screenshot files matching the naming convention:
        {capture_id}_{variant}.png
        
        Args:
            evidence_dir: Path to evidence directory.
            
        Returns:
            EvidenceManifest with discovered captures.
        """
        captures: dict[str, EvidenceCapture] = {}
        
        variant_suffixes = [
            "_element_padded",
            "_element_tight", 
            "_context",
            "_viewport",
            "_fullpage",
        ]
        
        for png_file in evidence_dir.glob("*.png"):
            filename = png_file.stem
            
            # Try to extract capture_id and variant
            capture_id = None
            variant = None
            
            for suffix in variant_suffixes:
                if filename.endswith(suffix):
                    capture_id = filename[: -len(suffix)]
                    variant = suffix[1:]  # Remove leading underscore
                    break
            
            if not capture_id:
                # No variant suffix - treat as single-file capture
                capture_id = filename
                variant = "element_padded"  # Default
            
            # Create or update capture
            if capture_id not in captures:
                captures[capture_id] = EvidenceCapture(
                    id=capture_id,
                    url="unknown",
                    description=f"Discovered from {png_file.name}",
                    anchor_text="",
                    files=CaptureFiles(),
                )
            
            # Set the file path for this variant
            setattr(captures[capture_id].files, variant, png_file.name)
        
        return EvidenceManifest(
            captures=list(captures.values()),
            reviewed=False,
            curated=False,
        )

    def _review_capture(
        self,
        capture: EvidenceCapture,
        evidence_dir: Path,
    ) -> EvidenceCapture:
        """
        Review a single evidence capture.
        
        Args:
            capture: The capture to review.
            evidence_dir: Path to evidence directory.
            
        Returns:
            Updated capture with review results.
        """
        reviews: dict[str, VariantReview] = {}
        best_score = -1
        best_variant: Optional[VariantType] = None
        
        # Review each variant that has a file
        variant_names: list[VariantType] = [
            "element_padded",
            "element_tight",
            "context",
            "viewport",
            "fullpage",
        ]
        
        for variant_name in variant_names:
            file_path = getattr(capture.files, variant_name, None)
            if not file_path:
                continue
            
            full_path = evidence_dir / file_path
            if not full_path.exists():
                reviews[variant_name] = VariantReview(
                    score=0,
                    keep=False,
                    reason=f"File not found: {file_path}",
                    is_blank=False,
                    has_anchor_text=False,
                    text_readable=False,
                )
                continue
            
            # Analyze with vision LLM
            review = self.vision_llm.analyze_screenshot(
                image_path=full_path,
                anchor_text=capture.anchor_text,
                description=capture.description,
            )
            
            reviews[variant_name] = review
            
            # Track best variant
            if review.keep and review.score > best_score:
                best_score = review.score
                best_variant = variant_name
        
        # Update capture with review results
        capture.review = reviews
        capture.best_variant = best_variant
        
        # Clear stale curated data if no variant is kept
        if not best_variant:
            capture.curated = None
        
        return capture

    def _print_summary(self, manifest: EvidenceManifest) -> None:
        """Print a summary table of the review results."""
        table = Table(title="Evidence Review Summary")
        table.add_column("Capture ID", style="cyan")
        table.add_column("Best Variant", style="green")
        table.add_column("Score", justify="right")
        table.add_column("Kept", justify="center")
        table.add_column("Reason")
        
        for capture in manifest.captures:
            if capture.best_variant and capture.review:
                best = capture.review.get(capture.best_variant)
                if best:
                    kept_count = sum(1 for r in capture.review.values() if r.keep)
                    total_count = len(capture.review)
                    table.add_row(
                        capture.id,
                        capture.best_variant,
                        str(best.score),
                        f"{kept_count}/{total_count}",
                        best.reason[:50] + "..." if len(best.reason) > 50 else best.reason,
                    )
            else:
                table.add_row(
                    capture.id,
                    "-",
                    "-",
                    "0/0",
                    "No usable variants",
                )
        
        console.print(table)
        
        # Summary stats
        total_captures = len(manifest.captures)
        with_best = sum(1 for c in manifest.captures if c.best_variant)
        console.print(f"\n[bold]Total:[/bold] {with_best}/{total_captures} captures have usable variants")


def review_evidence(
    project_dir: Path,
    mock: bool = False,
    verbose: bool = True,
) -> EvidenceManifest:
    """
    Convenience function to review evidence in a project.
    
    Args:
        project_dir: Path to project directory.
        mock: If True, use mock vision LLM (for testing).
        verbose: If True, print progress.
        
    Returns:
        Updated EvidenceManifest.
    """
    reviewer = EvidenceReviewer(mock=mock)
    return reviewer.review_project(project_dir, verbose=verbose)
