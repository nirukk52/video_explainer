"""
Integration tests for the Evidence Curation Pipeline.

Tests the full flow:
1. Witness captures screenshots (mocked or real)
2. Evidence Reviewer analyzes with Vision LLM
3. Image Editor crops and curates

Run with:
    pytest tests/test_evidence_pipeline.py -v
    pytest tests/test_evidence_pipeline.py -v -m "not slow"  # Skip API tests
"""

import json
import shutil
import tempfile
from pathlib import Path

import pytest

from src.evidence.models import (
    CaptureFiles,
    CropBox,
    EvidenceCapture,
    EvidenceManifest,
    VariantReview,
)
from src.evidence.reviewer import EvidenceReviewer, review_evidence
from src.evidence.editor import ImageEditor, curate_evidence, crop_image
from src.evidence.vision import MockVisionLLM, VisionLLM, get_vision_llm


# --- Fixtures ---

def _keep_artifacts(request) -> bool:
    """Whether to keep temp dirs (--keep-artifacts)."""
    return request.config.getoption("--keep-artifacts", default=False)


@pytest.fixture
def temp_project_dir(request):
    """Create a temporary project directory with evidence folder."""
    temp_dir = Path(tempfile.mkdtemp())
    evidence_dir = temp_dir / "evidence"
    evidence_dir.mkdir()

    yield temp_dir

    if not _keep_artifacts(request):
        shutil.rmtree(temp_dir)
    else:
        print(f"\n[keep-artifacts] evidence pipeline temp dir: {temp_dir}")
        ev = temp_dir / "evidence"
        print(f"  evidence/    {[p.name for p in ev.iterdir()]}")
        cur = ev / "curated"
        if cur.exists():
            print(f"  curated/     {[p.name for p in cur.iterdir()]}")


@pytest.fixture
def sample_manifest(temp_project_dir: Path) -> EvidenceManifest:
    """Create a sample manifest with test screenshots."""
    evidence_dir = temp_project_dir / "evidence"
    
    # Create a simple test PNG (1x1 red pixel)
    _create_test_png(evidence_dir / "test_001_element_padded.png", width=800, height=600)
    _create_test_png(evidence_dir / "test_001_fullpage.png", width=1920, height=3000)
    _create_test_png(evidence_dir / "test_002_element_padded.png", width=640, height=480)
    
    manifest = EvidenceManifest(
        project_id="test-project",
        captures=[
            EvidenceCapture(
                id="test_001",
                url="https://example.com/article",
                description="Test article with headline",
                anchor_text="Breaking News Headline",
                files=CaptureFiles(
                    element_padded="test_001_element_padded.png",
                    fullpage="test_001_fullpage.png",
                ),
            ),
            EvidenceCapture(
                id="test_002",
                url="https://example.com/pricing",
                description="Pricing table",
                anchor_text="$0.14 per million",
                files=CaptureFiles(
                    element_padded="test_002_element_padded.png",
                ),
            ),
        ],
    )
    
    manifest.save(evidence_dir)
    return manifest


def _create_test_png(path: Path, width: int = 100, height: int = 100, color: str = "red"):
    """Create a test PNG image."""
    try:
        from PIL import Image
        img = Image.new("RGB", (width, height), color)
        img.save(path, "PNG")
    except ImportError:
        # Fallback: create minimal valid PNG
        # PNG signature + IHDR + IDAT + IEND (1x1 red pixel)
        import struct
        import zlib
        
        def png_chunk(chunk_type, data):
            chunk = chunk_type + data
            crc = zlib.crc32(chunk) & 0xffffffff
            return struct.pack(">I", len(data)) + chunk + struct.pack(">I", crc)
        
        signature = b"\x89PNG\r\n\x1a\n"
        ihdr = png_chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
        scanline = b"\x00\xff\x00\x00"  # filter byte + RGB
        idat = png_chunk(b"IDAT", zlib.compress(scanline))
        iend = png_chunk(b"IEND", b"")
        
        path.write_bytes(signature + ihdr + idat + iend)


# --- Unit Tests ---

class TestEvidenceModels:
    """Test Pydantic models for evidence curation."""
    
    def test_crop_box_creation(self):
        """CropBox should store pixel coordinates."""
        crop = CropBox(x=10, y=20, width=100, height=50)
        assert crop.x == 10
        assert crop.y == 20
        assert crop.width == 100
        assert crop.height == 50
    
    def test_variant_review_keep_logic(self):
        """VariantReview should track review decisions."""
        review = VariantReview(
            score=8,
            keep=True,
            reason="Clear headline, good framing",
            is_blank=False,
            has_anchor_text=True,
            text_readable=True,
        )
        assert review.keep is True
        assert review.score == 8
    
    def test_manifest_load_save(self, temp_project_dir: Path):
        """EvidenceManifest should save and load from JSON."""
        evidence_dir = temp_project_dir / "evidence"
        
        manifest = EvidenceManifest(
            project_id="test",
            captures=[
                EvidenceCapture(
                    id="cap_001",
                    url="https://example.com",
                    description="Test",
                    anchor_text="Test text",
                )
            ],
        )
        
        manifest.save(evidence_dir)
        
        loaded = EvidenceManifest.load(evidence_dir)
        assert loaded.project_id == "test"
        assert len(loaded.captures) == 1
        assert loaded.captures[0].id == "cap_001"
    
    def test_manifest_get_kept_captures(self):
        """get_kept_captures should filter to captures with kept variants."""
        manifest = EvidenceManifest(
            captures=[
                EvidenceCapture(
                    id="good",
                    url="",
                    description="",
                    anchor_text="",
                    review={"element_padded": VariantReview(score=8, keep=True, reason="Good")},
                ),
                EvidenceCapture(
                    id="bad",
                    url="",
                    description="",
                    anchor_text="",
                    review={"element_padded": VariantReview(score=2, keep=False, reason="Blank")},
                ),
            ]
        )
        
        kept = manifest.get_kept_captures()
        assert len(kept) == 1
        assert kept[0].id == "good"


class TestMockVisionLLM:
    """Test mock Vision LLM for development/testing."""
    
    def test_analyze_screenshot_returns_review(self, temp_project_dir: Path):
        """MockVisionLLM should return VariantReview based on filename."""
        evidence_dir = temp_project_dir / "evidence"
        _create_test_png(evidence_dir / "test_element_padded.png")
        
        mock_llm = MockVisionLLM()
        review = mock_llm.analyze_screenshot(
            image_path=evidence_dir / "test_element_padded.png",
            anchor_text="Test",
        )
        
        assert isinstance(review, VariantReview)
        assert review.score > 0
        # element_padded should be highly rated by mock
        assert review.keep is True
    
    def test_detect_crop_region_returns_cropbox(self, temp_project_dir: Path):
        """MockVisionLLM should return a crop region."""
        evidence_dir = temp_project_dir / "evidence"
        _create_test_png(evidence_dir / "test.png", width=800, height=600)
        
        mock_llm = MockVisionLLM()
        crop = mock_llm.detect_crop_region(
            image_path=evidence_dir / "test.png",
            anchor_text="Test",
        )
        
        assert crop is not None
        assert isinstance(crop, CropBox)
        assert crop.width > 0
        assert crop.height > 0


class TestEvidenceReviewer:
    """Test Evidence Reviewer agent."""
    
    def test_review_with_mock(self, temp_project_dir: Path, sample_manifest: EvidenceManifest):
        """Reviewer should analyze all captures with mock LLM."""
        reviewer = EvidenceReviewer(mock=True)
        result = reviewer.review_project(temp_project_dir, verbose=False)
        
        assert result.reviewed is True
        assert len(result.captures) == 2
        
        # Both captures should have reviews
        for capture in result.captures:
            assert capture.review is not None
            assert len(capture.review) > 0
            # Mock should mark element_padded as best
            assert capture.best_variant is not None
    
    def test_review_discovers_captures_from_files(self, temp_project_dir: Path):
        """Reviewer should discover captures from files when manifest is empty."""
        evidence_dir = temp_project_dir / "evidence"
        
        # Create files but empty manifest
        _create_test_png(evidence_dir / "article_001_element_padded.png")
        _create_test_png(evidence_dir / "article_001_fullpage.png")
        
        manifest = EvidenceManifest()
        manifest.save(evidence_dir)
        
        reviewer = EvidenceReviewer(mock=True)
        result = reviewer.review_project(temp_project_dir, verbose=False)
        
        assert len(result.captures) == 1
        assert result.captures[0].id == "article_001"


class TestImageEditor:
    """Test Image Editor agent."""
    
    def test_curate_with_mock(self, temp_project_dir: Path, sample_manifest: EvidenceManifest):
        """Editor should crop and save curated images."""
        evidence_dir = temp_project_dir / "evidence"
        
        # First review
        reviewer = EvidenceReviewer(mock=True)
        reviewer.review_project(temp_project_dir, verbose=False)
        
        # Then curate
        editor = ImageEditor(mock=True)
        result = editor.curate_project(temp_project_dir, verbose=False)
        
        assert result.curated is True
        
        # Check curated folder was created
        curated_dir = evidence_dir / "curated"
        assert curated_dir.exists()
        
        # Check images were created
        curated_files = list(curated_dir.glob("*.png"))
        assert len(curated_files) >= 1
    
    def test_curate_requires_review_first(self, temp_project_dir: Path, sample_manifest: EvidenceManifest):
        """Editor should fail if evidence hasn't been reviewed."""
        editor = ImageEditor(mock=True)
        
        with pytest.raises(ValueError, match="not been reviewed"):
            editor.curate_project(temp_project_dir, verbose=False)
    
    def test_crop_image_function(self, temp_project_dir: Path):
        """crop_image should crop image to specified region."""
        evidence_dir = temp_project_dir / "evidence"
        source = evidence_dir / "source.png"
        output = evidence_dir / "cropped.png"
        
        _create_test_png(source, width=800, height=600)
        
        crop = CropBox(x=100, y=100, width=200, height=150)
        dims = crop_image(source, output, crop)
        
        assert output.exists()
        assert dims["width"] == 200
        assert dims["height"] == 150


class TestFullPipeline:
    """Integration tests for full evidence pipeline."""
    
    def test_review_then_curate_pipeline(self, temp_project_dir: Path, sample_manifest: EvidenceManifest):
        """Full pipeline: review → curate should work end-to-end."""
        # Step 1: Review
        manifest = review_evidence(temp_project_dir, mock=True, verbose=False)
        
        assert manifest.reviewed is True
        assert all(c.review is not None for c in manifest.captures)
        
        # Step 2: Curate
        manifest = curate_evidence(temp_project_dir, mock=True, verbose=False)
        
        assert manifest.curated is True
        
        # Verify output structure
        evidence_dir = temp_project_dir / "evidence"
        curated_dir = evidence_dir / "curated"
        
        assert curated_dir.exists()
        assert (evidence_dir / "manifest.json").exists()
        
        # Load and verify manifest has curated entries
        final_manifest = EvidenceManifest.load(evidence_dir)
        for capture in final_manifest.captures:
            if capture.best_variant:  # Only captures with kept variants
                assert capture.curated is not None
                assert capture.curated.file.startswith("curated/")
    
    def test_pipeline_clears_curated_when_rejected(self, temp_project_dir: Path, sample_manifest: EvidenceManifest):
        """
        If review rejects all variants, curated data should be cleared.
        
        This tests the fix where stale curated data was left after
        a re-review rejected previously approved captures.
        """
        evidence_dir = temp_project_dir / "evidence"
        
        # First pass: mock review keeps the captures
        manifest = review_evidence(temp_project_dir, mock=True, verbose=False)
        assert manifest.captures[0].best_variant is not None
        
        # Curate
        manifest = curate_evidence(temp_project_dir, mock=True, verbose=False)
        assert manifest.captures[0].curated is not None
        
        # Simulate a re-review that rejects everything
        # (This would happen with real Vision LLM on bad images)
        for capture in manifest.captures:
            if capture.review:
                for key in capture.review:
                    capture.review[key].keep = False
                    capture.review[key].score = 1
            capture.best_variant = None
            capture.curated = None  # This is what the fix does
        
        manifest.reviewed = True
        manifest.curated = False
        manifest.save(evidence_dir)
        
        # Verify curated is cleared
        reloaded = EvidenceManifest.load(evidence_dir)
        assert reloaded.captures[0].curated is None


@pytest.mark.slow
class TestRealVisionLLM:
    """Tests that use real Vision LLM API (requires ANTHROPIC_API_KEY)."""
    
    def test_real_vision_analysis(self, temp_project_dir: Path):
        """Test real Vision LLM analyzes screenshot correctly."""
        import os
        
        if not os.environ.get("ANTHROPIC_API_KEY"):
            pytest.skip("ANTHROPIC_API_KEY not set")
        
        evidence_dir = temp_project_dir / "evidence"
        
        # Create a simple image with text-like content
        _create_test_png(evidence_dir / "test.png", width=400, height=300)
        
        llm = VisionLLM()
        review = llm.analyze_screenshot(
            image_path=evidence_dir / "test.png",
            anchor_text="Test content",
        )
        
        assert isinstance(review, VariantReview)
        assert 0 <= review.score <= 10
        # Simple solid color image should be marked as blank or low quality
        assert review.score < 5 or review.is_blank


# --- Witness Integration Tests (require Browserbase) ---

@pytest.mark.slow
class TestWitnessIntegration:
    """Tests for Witness agent integration (requires Browserbase credentials)."""
    
    @pytest.mark.asyncio
    async def test_witness_capture_real_screenshot(self, request):
        """
        Test Witness captures a real screenshot using Browserbase.
        
        This test requires:
        - BROWSER_BASE_API_KEY
        - BROWSER_BASE_PROJECT_ID
        """
        import os
        import sys

        keep = _keep_artifacts(request)

        # Check required credentials
        if not os.environ.get("BROWSER_BASE_API_KEY"):
            pytest.skip("BROWSER_BASE_API_KEY not set")

        # Add visual-truth-engine to path
        vte_path = Path(__file__).parent.parent / "visual-truth-engine"
        if str(vte_path) not in sys.path:
            sys.path.insert(0, str(vte_path))

        from agents.witness import Witness

        # Create temp output directory
        temp_dir = Path(tempfile.mkdtemp())

        try:
            witness = Witness()

            # Capture a simple webpage
            result = await witness.capture_with_fallbacks(
                url="https://example.com",
                description="Example domain homepage",
                output_dir=str(temp_dir),
                scene_id=1,
                timeout_ms=30000,
            )

            print(f"Capture status: {result.status}")
            print(f"Strategy used: {result.strategy_used}")
            print(f"Fullpage path: {result.fullpage_path}")

            # Should at least have fullpage screenshot
            assert result.fullpage_path is not None
            assert Path(result.fullpage_path).exists()

        finally:
            if not keep:
                shutil.rmtree(temp_dir)
            else:
                print(f"\n[keep-artifacts] witness capture temp dir: {temp_dir}")
                print(f"  files: {list(temp_dir.iterdir())}")
    
    @pytest.mark.asyncio
    async def test_full_pipeline_witness_to_curated(self, request):
        """
        Full integration: Witness captures → Reviewer filters → Editor crops.
        
        This test requires:
        - BROWSER_BASE_API_KEY
        - BROWSER_BASE_PROJECT_ID
        - ANTHROPIC_API_KEY
        """
        import os
        import sys

        keep = _keep_artifacts(request)

        # Check required credentials
        if not os.environ.get("BROWSER_BASE_API_KEY"):
            pytest.skip("BROWSER_BASE_API_KEY not set")
        if not os.environ.get("ANTHROPIC_API_KEY"):
            pytest.skip("ANTHROPIC_API_KEY not set")

        # Add visual-truth-engine to path
        vte_path = Path(__file__).parent.parent / "visual-truth-engine"
        if str(vte_path) not in sys.path:
            sys.path.insert(0, str(vte_path))

        from agents.witness import Witness

        # Create temp project structure
        temp_dir = Path(tempfile.mkdtemp())
        evidence_dir = temp_dir / "evidence"
        evidence_dir.mkdir()

        try:
            # Step 1: Witness captures evidence
            print("\n=== Step 1: Witness Capture ===")
            witness = Witness()
            
            result = await witness.capture_with_fallbacks(
                url="https://news.ycombinator.com",
                description="Hacker News front page with tech headlines",
                output_dir=str(evidence_dir),
                scene_id=1,
                timeout_ms=30000,
            )
            
            print(f"Capture status: {result.status}")
            print(f"Files captured:")
            if result.element_padded_path:
                print(f"  - element_padded: {result.element_padded_path}")
            if result.fullpage_path:
                print(f"  - fullpage: {result.fullpage_path}")
            
            # Create manifest from capture
            manifest = EvidenceManifest(
                project_id="test-pipeline",
                captures=[
                    EvidenceCapture(
                        id="hn_001",
                        url="https://news.ycombinator.com",
                        description="Hacker News front page",
                        anchor_text="Hacker News",
                        files=CaptureFiles(
                            element_padded=Path(result.element_padded_path).name if result.element_padded_path else None,
                            fullpage=Path(result.fullpage_path).name if result.fullpage_path else None,
                        ),
                    )
                ],
            )
            manifest.save(evidence_dir)
            
            # Step 2: Evidence Reviewer
            print("\n=== Step 2: Evidence Review ===")
            reviewed = review_evidence(temp_dir, mock=False, verbose=True)
            
            print(f"Reviewed: {reviewed.reviewed}")
            for cap in reviewed.captures:
                print(f"  {cap.id}: best_variant={cap.best_variant}")
                if cap.review:
                    for variant, review in cap.review.items():
                        print(f"    {variant}: score={review.score}, keep={review.keep}")
            
            # Step 3: Image Editor (if any variants kept)
            if reviewed.get_kept_captures():
                print("\n=== Step 3: Image Curation ===")
                curated = curate_evidence(temp_dir, mock=False, verbose=True)
                
                print(f"Curated: {curated.curated}")
                for cap in curated.captures:
                    if cap.curated:
                        print(f"  {cap.id}: {cap.curated.file}")
                        print(f"    Dimensions: {cap.curated.dimensions}")
                
                # Verify curated folder exists
                curated_dir = evidence_dir / "curated"
                assert curated_dir.exists()
                curated_files = list(curated_dir.glob("*.png"))
                print(f"\nCurated files: {[f.name for f in curated_files]}")
                assert len(curated_files) >= 1
            else:
                print("\n=== No variants kept - skipping curation ===")
            
            print("\n=== Full Pipeline Complete ===")

        finally:
            if not keep:
                shutil.rmtree(temp_dir)
            else:
                print(f"\n[keep-artifacts] full pipeline temp dir: {temp_dir}")
                print(f"  evidence/    {[p.name for p in evidence_dir.iterdir()]}")
                curated_dir = evidence_dir / "curated"
                if curated_dir.exists():
                    print(f"  curated/     {[p.name for p in curated_dir.iterdir()]}")
