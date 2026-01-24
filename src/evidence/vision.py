"""
Vision LLM helpers for screenshot analysis.

Uses Anthropic's Claude API with vision capabilities to analyze
screenshots for quality, relevance, and content detection.
"""

import base64
import json
import os
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel

from .models import CropBox, VariantReview


class VisionAnalysisResult(BaseModel):
    """Result from vision LLM analysis of a screenshot."""

    score: int
    is_blank: bool
    has_anchor_text: bool
    text_readable: bool
    reason: str
    suggested_crop: Optional[CropBox] = None


class VisionLLM:
    """
    Wrapper for Anthropic's Claude API with vision capabilities.
    
    Used by Evidence Reviewer to analyze screenshot quality and
    by Image Editor to detect crop regions.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-20250514"):
        """
        Initialize the Vision LLM client.
        
        Args:
            api_key: Anthropic API key. If None, reads from ANTHROPIC_API_KEY env var.
            model: Claude model to use (must support vision).
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        
        self.model = model
        self._client = None

    @property
    def client(self):
        """Lazy-load the Anthropic client."""
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "anthropic package not installed. "
                    "Install with: pip install anthropic"
                )
        return self._client

    def _encode_image(self, image_path: Path) -> tuple[str, str]:
        """
        Encode an image file to base64.
        
        Args:
            image_path: Path to the image file.
            
        Returns:
            Tuple of (base64_data, media_type).
        """
        suffix = image_path.suffix.lower()
        media_types = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        media_type = media_types.get(suffix, "image/png")
        
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")
        
        return image_data, media_type

    def analyze_screenshot(
        self,
        image_path: Path,
        anchor_text: str,
        description: str = "",
    ) -> VariantReview:
        """
        Analyze a screenshot for quality and relevance.
        
        Args:
            image_path: Path to the screenshot file.
            anchor_text: The text that should be visible in the screenshot.
            description: Description of what the screenshot should show.
            
        Returns:
            VariantReview with score, keep decision, and reasons.
        """
        image_data, media_type = self._encode_image(image_path)
        
        prompt = f"""Analyze this screenshot and evaluate it on the following criteria:

1. **Blank Detection**: Is the image mostly blank, white, black, or empty?
2. **Anchor Text Visible**: Can you see the text "{anchor_text}" clearly in the image?
3. **Text Readability**: Is the text in the image clear and readable (not blurry, not too small)?
4. **Composition**: Is the key content well-framed and properly visible?

{f'Expected content: {description}' if description else ''}

Respond with a JSON object:
{{
    "score": <0-10 quality score>,
    "is_blank": <true if image is mostly blank/empty>,
    "has_anchor_text": <true if anchor text is visible>,
    "text_readable": <true if text is clear and readable>,
    "reason": "<brief explanation of the assessment>"
}}

Score guidelines:
- 0-2: Unusable (blank, wrong content, unreadable)
- 3-4: Poor (partial content, hard to read)
- 5-6: Acceptable (content visible but not ideal)
- 7-8: Good (clear content, well-framed)
- 9-10: Excellent (perfect clarity and composition)

Only output the JSON, no other text."""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=500,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt,
                        },
                    ],
                }
            ],
        )
        
        # Parse the response
        response_text = response.content[0].text.strip()
        
        # Extract JSON from response (handle markdown code blocks)
        if "```" in response_text:
            import re
            json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", response_text)
            if json_match:
                response_text = json_match.group(1).strip()
        
        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            # Fallback for parsing errors
            return VariantReview(
                score=0,
                keep=False,
                reason=f"Failed to parse vision analysis: {response_text[:200]}",
                is_blank=True,
                has_anchor_text=False,
                text_readable=False,
            )
        
        # Determine if we should keep this variant
        score = result.get("score", 0)
        is_blank = result.get("is_blank", False)
        has_anchor_text = result.get("has_anchor_text", True)
        text_readable = result.get("text_readable", True)
        
        # Keep if score >= 5 and not blank and has readable text
        keep = score >= 5 and not is_blank and text_readable
        
        return VariantReview(
            score=score,
            keep=keep,
            reason=result.get("reason", "No reason provided"),
            is_blank=is_blank,
            has_anchor_text=has_anchor_text,
            text_readable=text_readable,
        )

    def detect_crop_region(
        self,
        image_path: Path,
        anchor_text: str,
        padding: int = 40,
    ) -> Optional[CropBox]:
        """
        Detect the optimal crop region for a screenshot.
        
        Args:
            image_path: Path to the screenshot file.
            anchor_text: The text to focus the crop around.
            padding: Pixels of padding around the detected region.
            
        Returns:
            CropBox with coordinates, or None if detection fails.
        """
        image_data, media_type = self._encode_image(image_path)
        
        # Get image dimensions
        try:
            from PIL import Image
            with Image.open(image_path) as img:
                img_width, img_height = img.size
        except ImportError:
            # Can't determine dimensions without PIL
            return None
        
        prompt = f"""Analyze this screenshot and identify the optimal crop region.

The screenshot should focus on content containing or related to: "{anchor_text}"

Find the bounding box that:
1. Contains the anchor text or the main headline/content area
2. Excludes unnecessary margins, navigation bars, ads, and clutter
3. Keeps some context around the main content

Image dimensions: {img_width}x{img_height} pixels

Respond with a JSON object containing the crop coordinates:
{{
    "x": <left edge in pixels>,
    "y": <top edge in pixels>,
    "width": <width in pixels>,
    "height": <height in pixels>,
    "confidence": <0-1 confidence score>,
    "reason": "<what content is being focused on>"
}}

Make sure the coordinates are within the image bounds.
Only output the JSON, no other text."""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=500,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt,
                        },
                    ],
                }
            ],
        )
        
        response_text = response.content[0].text.strip()
        
        # Extract JSON from response
        if "```" in response_text:
            import re
            json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", response_text)
            if json_match:
                response_text = json_match.group(1).strip()
        
        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            return None
        
        # Validate and apply padding
        x = max(0, result.get("x", 0) - padding)
        y = max(0, result.get("y", 0) - padding)
        width = min(result.get("width", img_width) + 2 * padding, img_width - x)
        height = min(result.get("height", img_height) + 2 * padding, img_height - y)
        
        # Skip if crop is too small or covers almost entire image
        if width < 100 or height < 100:
            return None
        if width >= img_width * 0.95 and height >= img_height * 0.95:
            return None
        
        return CropBox(x=x, y=y, width=width, height=height)


class MockVisionLLM:
    """
    Mock Vision LLM for testing without API calls.
    Returns reasonable default values for testing the pipeline.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "mock"):
        """Initialize mock - ignores api_key and model."""
        pass

    def analyze_screenshot(
        self,
        image_path: Path,
        anchor_text: str,
        description: str = "",
    ) -> VariantReview:
        """Return a mock review based on filename heuristics."""
        filename = image_path.name.lower()
        
        # Simulate different quality based on variant type
        if "element_padded" in filename:
            return VariantReview(
                score=8,
                keep=True,
                reason="Mock: Element with padding typically has good framing",
                is_blank=False,
                has_anchor_text=True,
                text_readable=True,
            )
        elif "element_tight" in filename:
            return VariantReview(
                score=7,
                keep=True,
                reason="Mock: Tight element crop is usually readable",
                is_blank=False,
                has_anchor_text=True,
                text_readable=True,
            )
        elif "context" in filename:
            return VariantReview(
                score=5,
                keep=True,
                reason="Mock: Context view has more clutter but is usable",
                is_blank=False,
                has_anchor_text=True,
                text_readable=True,
            )
        elif "viewport" in filename:
            return VariantReview(
                score=3,
                keep=False,
                reason="Mock: Viewport often captures irrelevant content",
                is_blank=False,
                has_anchor_text=False,
                text_readable=True,
            )
        elif "fullpage" in filename:
            return VariantReview(
                score=2,
                keep=False,
                reason="Mock: Full page has too much content, text too small",
                is_blank=False,
                has_anchor_text=True,
                text_readable=False,
            )
        else:
            return VariantReview(
                score=5,
                keep=True,
                reason="Mock: Default review for unknown variant",
                is_blank=False,
                has_anchor_text=True,
                text_readable=True,
            )

    def detect_crop_region(
        self,
        image_path: Path,
        anchor_text: str,
        padding: int = 40,
    ) -> Optional[CropBox]:
        """Return a mock crop region (center crop)."""
        try:
            from PIL import Image
            with Image.open(image_path) as img:
                img_width, img_height = img.size
        except (ImportError, Exception):
            # Default dimensions if we can't read image
            img_width, img_height = 1920, 1080
        
        # Return a center crop
        crop_width = int(img_width * 0.6)
        crop_height = int(img_height * 0.5)
        x = (img_width - crop_width) // 2
        y = (img_height - crop_height) // 3  # Slightly higher than center
        
        return CropBox(x=x, y=y, width=crop_width, height=crop_height)


def get_vision_llm(mock: bool = False, api_key: Optional[str] = None) -> VisionLLM | MockVisionLLM:
    """
    Get a Vision LLM instance.
    
    Args:
        mock: If True, return a mock instance for testing.
        api_key: Optional API key (uses env var if not provided).
        
    Returns:
        VisionLLM or MockVisionLLM instance.
    """
    if mock:
        return MockVisionLLM()
    return VisionLLM(api_key=api_key)
