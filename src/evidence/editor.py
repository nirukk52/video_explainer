"""
Image Editor Agent.

Crops and processes reviewed screenshots to create curated
versions for use in video production.
"""

from pathlib import Path
from typing import Optional

from PIL import Image
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from .models import CropBox, CuratedEvidence, EvidenceCapture, EvidenceManifest
from .vision import MockVisionLLM, VisionLLM, get_vision_llm

console = Console()


class ImageEditor:
    """
    Processes reviewed screenshots to create curated versions.
    
    Uses Vision LLM to detect optimal crop regions, then applies
    cropping and saves processed images to the curated/ folder.
    """

    CURATED_DIR = "curated"
    
    def __init__(
        self,
        vision_llm: Optional[VisionLLM | MockVisionLLM] = None,
        mock: bool = False,
        padding: int = 40,
    ):
        """
        Initialize the Image Editor.
        
        Args:
            vision_llm: Vision LLM instance. If None, creates one.
            mock: If True and no vision_llm provided, use mock for testing.
            padding: Pixels of padding to add around detected regions.
        """
        self.vision_llm = vision_llm or get_vision_llm(mock=mock)
        self.padding = padding

    def curate_project(
        self,
        project_dir: Path,
        verbose: bool = True,
        force: bool = False,
    ) -> EvidenceManifest:
        """
        Curate all reviewed evidence in a project.
        
        Args:
            project_dir: Path to project directory.
            verbose: If True, print progress to console.
            force: If True, re-process even if already curated.
            
        Returns:
            Updated EvidenceManifest with curated results.
        """
        evidence_dir = project_dir / "evidence"
        if not evidence_dir.exists():
            raise FileNotFoundError(f"Evidence directory not found: {evidence_dir}")
        
        # Load manifest
        manifest = EvidenceManifest.load(evidence_dir)
        
        if not manifest.reviewed:
            raise ValueError(
                "Evidence has not been reviewed yet. "
                "Run 'video-explainer evidence review' first."
            )
        
        # Create curated directory
        curated_dir = evidence_dir / self.CURATED_DIR
        curated_dir.mkdir(exist_ok=True)
        
        # Get captures that have kept variants
        kept_captures = manifest.get_kept_captures()
        
        if verbose:
            console.print(
                f"\n[bold]Curating {len(kept_captures)} captures "
                f"(out of {len(manifest.captures)} total)...[/bold]\n"
            )
        
        # Process each capture
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            disable=not verbose,
        ) as progress:
            for capture in kept_captures:
                # Skip if already curated (unless force)
                if capture.curated and not force:
                    curated_path = evidence_dir / capture.curated.file
                    if curated_path.exists():
                        continue
                
                task = progress.add_task(f"Curating {capture.id}...", total=None)
                capture = self._curate_capture(capture, evidence_dir, curated_dir)
                progress.remove_task(task)
        
        # Mark as curated
        manifest.curated = True
        
        # Save updated manifest
        manifest.save(evidence_dir)
        
        if verbose:
            self._print_summary(manifest, curated_dir)
        
        return manifest

    def _curate_capture(
        self,
        capture: EvidenceCapture,
        evidence_dir: Path,
        curated_dir: Path,
    ) -> EvidenceCapture:
        """
        Curate a single evidence capture.
        
        Args:
            capture: The capture to curate.
            evidence_dir: Path to evidence directory.
            curated_dir: Path to curated output directory.
            
        Returns:
            Updated capture with curated results.
        """
        if not capture.best_variant:
            return capture
        
        # Get the best variant file
        best_file = getattr(capture.files, capture.best_variant, None)
        if not best_file:
            return capture
        
        source_path = evidence_dir / best_file
        if not source_path.exists():
            return capture
        
        # Detect crop region using vision LLM
        crop_box = self.vision_llm.detect_crop_region(
            image_path=source_path,
            anchor_text=capture.anchor_text,
            padding=self.padding,
        )
        
        # Output filename
        output_filename = f"{capture.id}.png"
        output_path = curated_dir / output_filename
        
        # Load and process image
        with Image.open(source_path) as img:
            if crop_box:
                # Apply crop
                cropped = img.crop((
                    crop_box.x,
                    crop_box.y,
                    crop_box.x + crop_box.width,
                    crop_box.y + crop_box.height,
                ))
                cropped.save(output_path, "PNG")
                final_width, final_height = cropped.size
            else:
                # No crop needed - copy as-is
                img.save(output_path, "PNG")
                final_width, final_height = img.size
                crop_box = None
        
        # Update capture with curated info
        capture.curated = CuratedEvidence(
            file=f"{self.CURATED_DIR}/{output_filename}",
            source_variant=capture.best_variant,
            crop=crop_box,
            dimensions={"width": final_width, "height": final_height},
        )
        
        return capture

    def _print_summary(self, manifest: EvidenceManifest, curated_dir: Path) -> None:
        """Print a summary of the curation results."""
        table = Table(title="Evidence Curation Summary")
        table.add_column("Capture ID", style="cyan")
        table.add_column("Source", style="dim")
        table.add_column("Output", style="green")
        table.add_column("Dimensions", justify="right")
        table.add_column("Cropped", justify="center")
        
        curated_count = 0
        for capture in manifest.captures:
            if capture.curated:
                curated_count += 1
                dims = capture.curated.dimensions
                dim_str = f"{dims['width']}x{dims['height']}" if dims else "-"
                cropped = "Yes" if capture.curated.crop else "No"
                table.add_row(
                    capture.id,
                    capture.curated.source_variant or "-",
                    capture.curated.file,
                    dim_str,
                    cropped,
                )
        
        console.print(table)
        console.print(f"\n[bold]Total:[/bold] {curated_count} images curated to {curated_dir}")


def crop_image(
    source_path: Path,
    output_path: Path,
    crop: CropBox,
) -> dict[str, int]:
    """
    Crop an image and save to output path.
    
    Args:
        source_path: Path to source image.
        output_path: Path for output image.
        crop: Crop box coordinates.
        
    Returns:
        Dictionary with final dimensions {width, height}.
    """
    with Image.open(source_path) as img:
        cropped = img.crop((
            crop.x,
            crop.y,
            crop.x + crop.width,
            crop.y + crop.height,
        ))
        cropped.save(output_path, "PNG")
        return {"width": cropped.width, "height": cropped.height}


def curate_evidence(
    project_dir: Path,
    mock: bool = False,
    verbose: bool = True,
    force: bool = False,
) -> EvidenceManifest:
    """
    Convenience function to curate evidence in a project.
    
    Args:
        project_dir: Path to project directory.
        mock: If True, use mock vision LLM (for testing).
        verbose: If True, print progress.
        force: If True, re-process even if already curated.
        
    Returns:
        Updated EvidenceManifest.
    """
    editor = ImageEditor(mock=mock)
    return editor.curate_project(project_dir, verbose=verbose, force=force)
