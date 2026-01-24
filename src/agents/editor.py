"""
The Editor Agent - Asset Packager for Render Pipelines.

Transforms the enriched project state into a render-ready JSON manifest.
Makes layout decisions based on asset availability and structures output
for consumption by Remotion or other video rendering tools.
"""

from typing import Literal, TYPE_CHECKING

from src.agents.base import BaseAgent

if TYPE_CHECKING:
    from src.models import VideoProject, ScriptScene


# Average reading speed for duration calculation (words per second)
WORDS_PER_SECOND = 2.5

# Layout types for Remotion composition
LayoutType = Literal["full_avatar", "split_screen", "pip", "evidence_only"]


class Editor(BaseAgent):
    """
    Packages collected assets into render-ready JSON manifests.

    Applies layout logic:
    - If evidence_asset exists → SPLIT_SCREEN or PIP layout
    - If evidence_asset missing → FULL_AVATAR fallback

    Outputs a clean JSON manifest consumable by Remotion compositions.
    """

    @property
    def name(self) -> str:
        return "Editor"

    async def run(self, project: "VideoProject") -> "VideoProject":
        """
        Generate the final render manifest from collected assets.

        Structures all scenes with their assets, durations, and layout
        decisions into a JSON format ready for video rendering pipelines.

        Args:
            project: Fully enriched project state from all previous agents.

        Returns:
            Project with render_manifest ready for Remotion.
        """
        if not project.script:
            self.log("No script found, skipping manifest generation")
            return project

        self.log("Assembling render manifest...")

        render_queue = []

        for scene in project.script.scenes:
            # Calculate duration from voiceover
            duration = self._calculate_duration(scene.voiceover)

            # Determine layout based on asset availability and type
            layout = self._determine_layout(scene)

            # Extract screenshot path from notes if available
            screenshot_url = self._extract_screenshot_from_notes(scene.notes)

            # Build scene entry for render manifest
            scene_manifest = {
                "scene_id": scene.scene_id,
                "scene_type": scene.scene_type,
                "duration_seconds": duration,
                "layout": layout,
                "voiceover": {
                    "text": scene.voiceover,
                    "word_count": len(scene.voiceover.split()),
                },
                "visual": {
                    "type": scene.visual_cue.visual_type,
                    "description": scene.visual_cue.description,
                    "screenshot_url": screenshot_url,
                },
                "layers": self._build_layers(scene, layout, screenshot_url),
            }

            render_queue.append(scene_manifest)
            self.log(f"Scene {scene.scene_id}: {layout} layout, {duration:.1f}s")

        # Calculate total duration
        total_duration = sum(scene["duration_seconds"] for scene in render_queue)

        # Store render manifest in project
        # Using storyboard's style_guide dict to store render_manifest temporarily
        if project.storyboard:
            project.storyboard.style_guide["render_manifest"] = {
                "project_id": project.project_id,
                "total_duration_seconds": round(total_duration, 1),
                "scene_count": len(render_queue),
                "render_queue": render_queue,
            }

        self.log(f"Manifest assembly complete. Total duration: {total_duration:.1f}s")
        return project

    def _calculate_duration(self, voiceover: str) -> float:
        """
        Calculate scene duration based on voiceover word count.

        Uses average reading speed plus buffer for pacing.
        """
        word_count = len(voiceover.split())
        base_duration = word_count / WORDS_PER_SECOND

        # Add buffer for visual transitions (0.5s min, 1.5s for evidence)
        buffer = 1.0

        # Minimum duration of 3 seconds, max of 10 seconds per scene
        return max(3.0, min(10.0, base_duration + buffer))

    def _determine_layout(self, scene: "ScriptScene") -> LayoutType:
        """
        Determine the layout type based on scene content and assets.

        Layout logic:
        - full_avatar: Hook/conclusion scenes or when no evidence asset
        - split_screen: Evidence scenes with scroll recordings
        - pip: Evidence scenes with static screenshots (avatar in corner)
        - evidence_only: DOM crops that should fill the screen
        """
        visual_type = scene.visual_cue.visual_type.lower()

        # Full avatar for intro/opinion scenes
        if visual_type in ("full_avatar", "animation"):
            return "full_avatar"

        # Check if we have a screenshot (from notes)
        has_screenshot = "Screenshot:" in scene.notes

        if not has_screenshot:
            # Fallback to full avatar if capture failed
            return "full_avatar"

        # Layout based on visual type
        if visual_type in ("scroll_highlight", "recording"):
            return "split_screen"  # Video on main, avatar on side
        elif visual_type in ("dom_crop", "element"):
            return "evidence_only"  # Clean crop fills screen
        elif visual_type in ("static_highlight", "screenshot"):
            return "pip"  # Screenshot with avatar picture-in-picture

        return "full_avatar"

    def _extract_screenshot_from_notes(self, notes: str) -> str | None:
        """Extract screenshot path from scene notes."""
        if "Screenshot:" not in notes:
            return None
        parts = notes.split("Screenshot:")
        if len(parts) < 2:
            return None
        screenshot_part = parts[1].split("|")[0].strip()
        return screenshot_part if screenshot_part else None

    def _build_layers(
        self, scene: "ScriptScene", layout: LayoutType, screenshot_url: str | None
    ) -> list[dict]:
        """
        Build the layer stack for a scene's composition.

        Each layer represents a visual element in the Remotion composition.
        """
        layers = []

        # Add voiceover/TTS layer (always present)
        layers.append({
            "type": "audio",
            "source": "tts",
            "text": scene.voiceover,
            "voice_id": None,  # To be filled by TTS service
        })

        # Add visual layers based on layout
        if layout == "full_avatar":
            layers.append({
                "type": "avatar",
                "position": "center",
                "scale": 1.0,
            })

        elif layout == "split_screen":
            layers.append({
                "type": "evidence",
                "source": screenshot_url,
                "position": "left",
                "scale": 0.6,
                "animation": "scroll_down",
            })
            layers.append({
                "type": "avatar",
                "position": "right",
                "scale": 0.4,
            })

        elif layout == "pip":
            layers.append({
                "type": "evidence",
                "source": screenshot_url,
                "position": "fullscreen",
                "scale": 1.0,
                "animation": "zoom_highlight",
            })
            layers.append({
                "type": "avatar",
                "position": "bottom_right",
                "scale": 0.25,
            })

        elif layout == "evidence_only":
            layers.append({
                "type": "evidence",
                "source": screenshot_url,
                "position": "center",
                "scale": 1.0,
                "animation": "fade_in",
            })

        return layers

    def generate_manifest(self, project: "VideoProject") -> dict:
        """
        Generate render manifest without modifying project state.

        Useful for preview or validation.
        """
        if not project.script:
            return {}

        render_queue = []
        for scene in project.script.scenes:
            duration = self._calculate_duration(scene.voiceover)
            layout = self._determine_layout(scene)
            screenshot_url = self._extract_screenshot_from_notes(scene.notes)

            render_queue.append({
                "scene_id": scene.scene_id,
                "scene_type": scene.scene_type,
                "duration_seconds": duration,
                "layout": layout,
                "voiceover": {"text": scene.voiceover},
                "visual": {
                    "type": scene.visual_cue.visual_type,
                    "screenshot_url": screenshot_url,
                },
            })

        return {
            "project_id": project.project_id,
            "total_duration_seconds": sum(s["duration_seconds"] for s in render_queue),
            "scene_count": len(render_queue),
            "render_queue": render_queue,
        }
