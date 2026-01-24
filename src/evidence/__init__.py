"""Evidence curation module for reviewing and processing screenshots."""

from .editor import ImageEditor, crop_image, curate_evidence
from .models import (
    CaptureFiles,
    CropBox,
    CuratedEvidence,
    EvidenceCapture,
    EvidenceManifest,
    VariantReview,
)
from .reviewer import EvidenceReviewer, review_evidence
from .vision import MockVisionLLM, VisionLLM, get_vision_llm

__all__ = [
    # Models
    "CaptureFiles",
    "CropBox",
    "CuratedEvidence",
    "EvidenceCapture",
    "EvidenceManifest",
    "VariantReview",
    # Vision
    "VisionLLM",
    "MockVisionLLM",
    "get_vision_llm",
    # Reviewer
    "EvidenceReviewer",
    "review_evidence",
    # Editor
    "ImageEditor",
    "crop_image",
    "curate_evidence",
]
