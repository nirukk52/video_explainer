"""
The Witness Agent - Visual Capture Engine (Browserbase + Reconnaissance Architecture).

ARCHITECTURE:
=============
Stage 1: Browserbase stealth browser loads page (bypasses Cloudflare/anti-bot)
Stage 2: Reconnaissance - extract REAL visible text from page
Stage 3: LLM picks best anchors from REAL text (no hallucination)
Stage 4: Element discovery using real anchors
Stage 5: Multi-layer capture with fallback chain

CAPTURE FALLBACK CHAIN:
=======================
1. Element with padding (best: specific element + context)
2. Element tight crop (fallback: just the element)
3. Parent container with padding (fallback: more context)
4. Full page screenshot (ultimate fallback: always works)

OUTPUT FILES:
=============
For each capture, generates multiple images:
- element_padded.png   - Target element with 20px padding (borders visible)
- element_tight.png    - Target element tight crop
- context.png          - Parent container with padding
- fullpage.png         - Full page screenshot (fallback)

WHY BROWSERBASE:
================
- Stealth mode bypasses Cloudflare, anti-bot protection
- No local browser detection issues
- Managed infrastructure, no maintenance
"""

import asyncio
import json
import os
import time
from dataclasses import dataclass, field
from typing import Optional, Literal, TYPE_CHECKING

from src.agents.base import BaseAgent

if TYPE_CHECKING:
    from src.models import VideoProject


# Default padding for element captures (pixels)
DEFAULT_PADDING_PX = 20


@dataclass
class ScreenshotVariant:
    """Single screenshot variant with path and display title."""
    
    path: str
    title: str


@dataclass
class ScreenshotBundle:
    """
    Bundle of 5 screenshot variants for a single evidence capture.
    
    Provides flexibility for video rendering - Editor can choose
    the most appropriate variant for each scene's visual needs.
    """
    
    element_padded: Optional[ScreenshotVariant] = None
    element_tight: Optional[ScreenshotVariant] = None
    context: Optional[ScreenshotVariant] = None
    viewport: Optional[ScreenshotVariant] = None
    fullpage: Optional[ScreenshotVariant] = None
    
    def get_all_with_titles(self) -> list[ScreenshotVariant]:
        """Return all available screenshots as a list for easy iteration in UI."""
        variants = []
        if self.element_padded:
            variants.append(self.element_padded)
        if self.element_tight:
            variants.append(self.element_tight)
        if self.context:
            variants.append(self.context)
        if self.viewport:
            variants.append(self.viewport)
        if self.fullpage:
            variants.append(self.fullpage)
        return variants


@dataclass
class CaptureBundle:
    """
    Bundle of all captured images for a single evidence request.
    
    Provides 5 image variants for video rendering flexibility:
    1. element_padded - Element with 20px padding (borders visible)
    2. element_tight  - Element tight crop (no padding)
    3. context        - Parent container with padding
    4. viewport       - Current viewport screenshot
    5. fullpage       - Full page (always captured as fallback)
    """
    
    status: Literal["success", "partial", "failed"]
    
    # File paths to captured images (5 variants)
    element_padded_path: Optional[str] = None
    element_tight_path: Optional[str] = None
    context_path: Optional[str] = None
    viewport_path: Optional[str] = None
    fullpage_path: Optional[str] = None
    
    # Metadata
    element_selector: Optional[str] = None
    anchor_text_found: Optional[str] = None
    strategy_used: Optional[str] = None
    timing_ms: int = 0
    error_message: Optional[str] = None
    
    def to_screenshot_bundle(self) -> ScreenshotBundle:
        """Convert to ScreenshotBundle schema for API response with display titles."""
        return ScreenshotBundle(
            element_padded=ScreenshotVariant(path=self.element_padded_path, title="Element Focus") 
                if self.element_padded_path else None,
            element_tight=ScreenshotVariant(path=self.element_tight_path, title="Element Tight") 
                if self.element_tight_path else None,
            context=ScreenshotVariant(path=self.context_path, title="Context View") 
                if self.context_path else None,
            viewport=ScreenshotVariant(path=self.viewport_path, title="Viewport") 
                if self.viewport_path else None,
            fullpage=ScreenshotVariant(path=self.fullpage_path, title="Full Page") 
                if self.fullpage_path else None,
        )


@dataclass
class EvidenceAsset:
    """Visual evidence captured by the Witness agent."""
    
    capture_status: Literal["success", "partial", "failed", "pending"]
    asset_type: Literal["screenshot", "recording", "dom_crop"]
    css_selector: Optional[str] = None
    identifying_text: Optional[str] = None
    screenshots: Optional[ScreenshotBundle] = None
    screenshot_url: Optional[str] = None  # Best available for backward compat
    recording_url: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    error_message: Optional[str] = None


# LLM prompt for picking anchors from REAL page text
ANCHOR_PICKER_PROMPT = """You are given a list of ACTUAL text snippets found on a web page.
Your job is to pick the 2-4 best ones that would help locate this element:

Target element description: "{description}"

Available text snippets from the page:
{text_candidates}

Rules:
- Pick ONLY from the provided list (copy exactly, including newlines)
- Prefer specific text: prices, model names, unique labels
- Avoid generic text like "Learn more", "Contact", navigation items
- Pick texts that would be INSIDE or NEAR the target element

Return JSON:
{{"selected_anchors": ["exact text 1", "exact text 2"], "reasoning": "brief explanation"}}"""


class Witness(BaseAgent):
    """
    Captures visual evidence using Browserbase stealth browsers.
    
    Uses reconnaissance-first approach: loads page, extracts real text,
    then asks LLM to pick anchors. This eliminates hallucination.
    
    Generates multiple image variants with fallback chain for reliability.
    """

    def __init__(
        self,
        browserbase_api_key: str | None = None,
        browserbase_project_id: str | None = None,
        openai_api_key: str | None = None,
    ):
        """
        Initialize the Witness agent.

        Args:
            browserbase_api_key: Browserbase API key. Falls back to BROWSER_BASE_API_KEY env var.
            browserbase_project_id: Browserbase project ID. Falls back to BROWSER_BASE_PROJECT_ID env var.
            openai_api_key: OpenAI API key for anchor picking. Falls back to OPENAI_API_KEY env var.
        """
        self._browserbase_api_key = browserbase_api_key or os.getenv("BROWSER_BASE_API_KEY", "")
        self._browserbase_project_id = browserbase_project_id or os.getenv("BROWSER_BASE_PROJECT_ID", "")
        self._openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY", "")
        
        self._browserbase = None
        self._openai = None

    def _get_browserbase(self):
        """Lazy-init Browserbase client."""
        if self._browserbase is None:
            if not self._browserbase_api_key:
                raise ValueError("BROWSER_BASE_API_KEY not configured")
            from browserbase import Browserbase
            self._browserbase = Browserbase(api_key=self._browserbase_api_key)
        return self._browserbase

    def _get_openai(self):
        """Lazy-init OpenAI client."""
        if self._openai is None:
            if not self._openai_api_key:
                raise ValueError("OPENAI_API_KEY not configured")
            from openai import AsyncOpenAI
            self._openai = AsyncOpenAI(api_key=self._openai_api_key)
        return self._openai

    @property
    def name(self) -> str:
        return "Witness"

    async def run(self, project: "VideoProject") -> "VideoProject":
        """
        Capture visual assets for all scenes with evidence URLs.
        
        For each scene, generates multiple image variants with fallback chain.
        """
        if not project.script:
            self.log("No script found, skipping capture")
            return project

        self.log("Starting Visual Capture (Browserbase + Reconnaissance)...")

        # Create output directory
        output_dir = f"output/{project.project_id}"
        os.makedirs(output_dir, exist_ok=True)

        for i, scene in enumerate(project.script.scenes):
            # Check if scene has evidence URL (stored in notes from Investigator)
            if "URL:" not in scene.notes:
                self.log(f"Scene {scene.scene_id}: Skipping (no evidence URL)")
                continue

            # Extract URL from notes
            url = self._extract_url_from_notes(scene.notes)
            if not url:
                continue

            description = scene.visual_cue.description
            self.log(f"Scene {scene.scene_id}: Capturing '{description[:50]}...'")

            capture_bundle = await self.capture_with_fallbacks(
                url=url,
                description=description,
                output_dir=output_dir,
                scene_id=i,
            )

            # Store result in scene notes
            if capture_bundle.status in ("success", "partial"):
                best_screenshot = (
                    capture_bundle.element_padded_path
                    or capture_bundle.context_path
                    or capture_bundle.viewport_path
                    or capture_bundle.fullpage_path
                )
                scene.notes += f" | Screenshot: {best_screenshot}"
                self.log(
                    f"Scene {scene.scene_id}: {capture_bundle.status.upper()} "
                    f"via {capture_bundle.strategy_used or 'fullpage'} "
                    f"({capture_bundle.timing_ms}ms)"
                )
            else:
                scene.notes += f" | Capture FAILED: {capture_bundle.error_message}"
                self.log(f"Scene {scene.scene_id}: FAILED - {capture_bundle.error_message}")

        self.log("Visual capture complete.")
        return project

    def _extract_url_from_notes(self, notes: str) -> str | None:
        """Extract URL from scene notes."""
        if "URL:" not in notes:
            return None
        parts = notes.split("URL:")
        if len(parts) < 2:
            return None
        url_part = parts[1].split("|")[0].strip()
        return url_part if url_part.startswith("http") else None

    async def capture_with_fallbacks(
        self,
        url: str,
        description: str,
        output_dir: str,
        scene_id: int,
        timeout_ms: int = 30000,
        padding_px: int = DEFAULT_PADDING_PX,
    ) -> CaptureBundle:
        """
        Capture element with full fallback chain.
        
        Fallback Chain:
        1. Element with padding (ideal)
        2. Element tight crop
        3. Parent container with padding  
        4. Full page screenshot (always works)
        
        Returns CaptureBundle with all available images.
        """
        from playwright.async_api import async_playwright
        
        start_time = time.time()
        bundle = CaptureBundle(status="failed", timing_ms=0)
        
        bb = self._get_browserbase()
        session = None
        
        try:
            # Create Browserbase session
            session = bb.sessions.create(
                project_id=self._browserbase_project_id,
            )
            self.log(f"  Browserbase session: {session.id[:8]}...")
            
            async with async_playwright() as p:
                browser = await p.chromium.connect_over_cdp(session.connect_url)
                
                try:
                    context = browser.contexts[0]
                    page = context.pages[0]
                    
                    # Stage 1: Load page
                    self.log(f"  Loading {url[:50]}...")
                    await page.goto(url, timeout=15000)
                    await page.wait_for_load_state("domcontentloaded", timeout=10000)
                    await asyncio.sleep(2)  # Let JS render
                    
                    # Check for anti-bot block
                    title = await page.title()
                    if "moment" in title.lower() or "cloudflare" in title.lower():
                        bundle.error_message = f"Anti-bot block detected: {title}"
                        return bundle
                    
                    # Stage 2: Capture fullpage and viewport (guaranteed fallbacks)
                    fullpage_path = f"{output_dir}/scene_{scene_id}_fullpage.png"
                    await page.screenshot(path=fullpage_path, full_page=True)
                    bundle.fullpage_path = fullpage_path
                    self.log(f"  ✓ Full page captured")
                    
                    viewport_path = f"{output_dir}/scene_{scene_id}_viewport.png"
                    await page.screenshot(path=viewport_path, full_page=False)
                    bundle.viewport_path = viewport_path
                    bundle.status = "partial"  # At least we have viewport + fullpage
                    self.log(f"  ✓ Viewport captured")
                    
                    # Stage 3: Reconnaissance - extract real text from page
                    text_candidates = await self._extract_page_text(page)
                    
                    if not text_candidates:
                        bundle.error_message = "No text candidates found on page"
                        bundle.timing_ms = int((time.time() - start_time) * 1000)
                        return bundle
                    
                    self.log(f"  Found {len(text_candidates)} text candidates")
                    
                    # Stage 4: LLM picks best anchors from REAL text
                    selected_anchors = await self._pick_anchors_from_real_text(
                        description, text_candidates
                    )
                    
                    if not selected_anchors:
                        bundle.error_message = "LLM failed to pick anchors"
                        bundle.timing_ms = int((time.time() - start_time) * 1000)
                        return bundle
                    
                    self.log(f"  Selected anchors: {selected_anchors[:2]}")
                    
                    # Stage 5: Find element using real anchors
                    element_box, selector, anchor_found, strategy = await self._find_element(
                        page, selected_anchors
                    )
                    
                    if element_box and selector:
                        bundle.element_selector = selector
                        bundle.anchor_text_found = anchor_found
                        bundle.strategy_used = strategy
                        
                        # Capture element with padding
                        padded_path = f"{output_dir}/scene_{scene_id}_element_padded.png"
                        await self._capture_with_padding(page, element_box, padded_path, padding_px)
                        bundle.element_padded_path = padded_path
                        self.log(f"  ✓ Element with padding captured")
                        
                        # Capture element tight
                        tight_path = f"{output_dir}/scene_{scene_id}_element_tight.png"
                        await page.screenshot(path=tight_path, clip=element_box)
                        bundle.element_tight_path = tight_path
                        self.log(f"  ✓ Element tight captured")
                        
                        # Try to capture parent container
                        parent_box = await self._find_parent_container(page, anchor_found)
                        if parent_box:
                            context_path = f"{output_dir}/scene_{scene_id}_context.png"
                            await self._capture_with_padding(page, parent_box, context_path, padding_px)
                            bundle.context_path = context_path
                            self.log(f"  ✓ Context captured")
                        
                        bundle.status = "success"
                    else:
                        bundle.error_message = f"Element not found with anchors: {selected_anchors[:2]}"
                    
                finally:
                    await browser.close()
                    
        except Exception as e:
            bundle.error_message = str(e)
            
        finally:
            # Clean up Browserbase session
            if session:
                try:
                    bb.sessions.update(
                        session.id,
                        project_id=self._browserbase_project_id,
                        status="REQUEST_RELEASE"
                    )
                except Exception:
                    pass
        
        bundle.timing_ms = int((time.time() - start_time) * 1000)
        return bundle

    async def _extract_page_text(self, page) -> list[str]:
        """
        Reconnaissance: Extract all visible text candidates from page.
        
        Focuses on text that could be useful for element identification.
        """
        return await page.evaluate("""
            () => {
                const candidates = [];
                const seen = new Set();
                const elements = document.querySelectorAll('h1, h2, h3, h4, p, span, td, th, div, a, button');
                
                for (const el of elements) {
                    const text = el.innerText?.trim();
                    if (!text || text.length < 3 || text.length > 100) continue;
                    if (seen.has(text)) continue;
                    
                    const rect = el.getBoundingClientRect();
                    if (rect.width === 0 || rect.height === 0) continue;
                    
                    // Score based on usefulness
                    let dominated = false;
                    for (const child of el.children) {
                        if (child.innerText?.trim() === text) {
                            dominated = true;
                            break;
                        }
                    }
                    if (dominated) continue;
                    
                    seen.add(text);
                    candidates.push(text);
                }
                
                return candidates.slice(0, 50);
            }
        """)

    async def _pick_anchors_from_real_text(
        self, description: str, text_candidates: list[str]
    ) -> list[str]:
        """
        Ask LLM to pick best anchors from REAL text found on page.
        
        This eliminates hallucination - LLM can only choose from actual page content.
        """
        try:
            openai = self._get_openai()
            
            # Format candidates for prompt
            formatted = "\n".join(f"- {t}" for t in text_candidates[:30])
            
            response = await openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": ANCHOR_PICKER_PROMPT.format(
                            description=description,
                            text_candidates=formatted
                        ),
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=300,
            )
            
            content = response.choices[0].message.content
            if not content:
                return []
            
            parsed = json.loads(content)
            return parsed.get("selected_anchors", [])
            
        except Exception as e:
            self.log(f"  Anchor picking error: {e}")
            return []

    async def _find_element(
        self, page, anchors: list[str]
    ) -> tuple[dict | None, str | None, str | None, str | None]:
        """
        Find element using anchor texts.
        
        Returns (bounding_box, selector, anchor_found, strategy).
        """
        for anchor in anchors:
            # Clean anchor text (remove newlines for better matching)
            clean_anchor = anchor.split('\n')[0].strip()
            
            # Strategy 1: Text locator
            try:
                locator = page.get_by_text(clean_anchor, exact=False)
                count = await locator.count()
                if count > 0:
                    first = locator.first
                    await first.scroll_into_view_if_needed(timeout=3000)
                    box = await first.bounding_box()
                    if box:
                        selector = await self._get_selector(first)
                        return box, selector, anchor, "text_locator"
            except Exception:
                pass
            
            # Strategy 2: XPath (use clean anchor)
            try:
                escaped = clean_anchor.replace("'", "\\'")
                xpath = f"//*[contains(text(), '{escaped}')]"
                locator = page.locator(xpath)
                count = await locator.count()
                if count > 0:
                    first = locator.first
                    await first.scroll_into_view_if_needed(timeout=3000)
                    box = await first.bounding_box()
                    if box:
                        selector = await self._get_selector(first)
                        return box, selector, anchor, "xpath"
            except Exception:
                pass
        
        return None, None, None, None

    async def _get_selector(self, locator) -> str | None:
        """Get CSS selector for a locator."""
        try:
            element = await locator.element_handle()
            if not element:
                return None
            
            return await element.evaluate("""
                (el) => {
                    if (el.id) return '#' + CSS.escape(el.id);
                    
                    let path = [];
                    let current = el;
                    while (current && current !== document.body) {
                        let selector = current.tagName.toLowerCase();
                        if (current.parentElement) {
                            const siblings = Array.from(current.parentElement.children);
                            const index = siblings.indexOf(current) + 1;
                            selector += ':nth-child(' + index + ')';
                        }
                        path.unshift(selector);
                        current = current.parentElement;
                    }
                    return 'body > ' + path.join(' > ');
                }
            """)
        except Exception:
            return None

    async def _capture_with_padding(
        self, page, box: dict, path: str, padding: int
    ):
        """Capture element with padding around it."""
        page_height = await page.evaluate("document.body.scrollHeight")
        page_width = await page.evaluate("document.body.scrollWidth")
        
        padded_clip = {
            "x": max(0, box["x"] - padding),
            "y": max(0, box["y"] - padding),
            "width": min(box["width"] + (padding * 2), page_width - max(0, box["x"] - padding)),
            "height": min(box["height"] + (padding * 2), page_height - max(0, box["y"] - padding)),
        }
        
        await page.screenshot(path=path, clip=padded_clip)

    async def _find_parent_container(self, page, anchor_text: str) -> dict | None:
        """
        Find a sensible parent container for context capture.
        
        Walks up the DOM to find a card/section that contains the element.
        """
        if not anchor_text:
            return None
            
        try:
            result = await page.evaluate("""
                (searchText) => {
                    const elements = document.querySelectorAll('*');
                    let target = null;
                    
                    for (const el of elements) {
                        if (el.innerText?.includes(searchText)) {
                            const hasChildWithText = Array.from(el.children).some(
                                child => child.innerText?.includes(searchText)
                            );
                            if (!hasChildWithText) {
                                target = el;
                                break;
                            }
                        }
                    }
                    
                    if (!target) return null;
                    
                    // Walk up to find container
                    let current = target.parentElement;
                    let attempts = 0;
                    
                    while (current && current !== document.body && attempts < 8) {
                        const rect = current.getBoundingClientRect();
                        
                        // Look for card-sized container
                        if (rect.width > 200 && rect.height > 150 && 
                            rect.width < 800 && rect.height < 600) {
                            return {
                                x: rect.x + window.scrollX,
                                y: rect.y + window.scrollY,
                                width: rect.width,
                                height: rect.height
                            };
                        }
                        
                        current = current.parentElement;
                        attempts++;
                    }
                    
                    return null;
                }
            """, anchor_text)
            
            return result
            
        except Exception:
            return None

    async def capture_url(
        self,
        url: str,
        description: str,
        output_dir: str = "output/captures",
    ) -> CaptureBundle:
        """
        Public method to capture a URL without full pipeline context.

        Useful for standalone capture or testing.
        """
        os.makedirs(output_dir, exist_ok=True)
        return await self.capture_with_fallbacks(
            url=url,
            description=description,
            output_dir=output_dir,
            scene_id=0,
        )
