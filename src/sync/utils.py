"""
Utility functions for visual-voiceover sync.

This module provides word matching, frame calculations, and code extraction
utilities adapted from src/short/timing_generator.py.
"""

import re
from typing import Any, Optional


def find_word_frame(
    word_timestamps: list[dict[str, Any]],
    target_word: str,
    fps: int = 30,
    match_mode: str = "contains",
    use_start: bool = True,
    offset_frames: int = 0,
) -> Optional[int]:
    """Find the frame number when a specific word is spoken.

    Args:
        word_timestamps: List of word timestamp dicts with 'word', 'start_seconds', 'end_seconds'.
        target_word: The word to find (case-insensitive).
        fps: Frames per second for conversion.
        match_mode: How to match words:
            - "exact": Word must match exactly (after stripping punctuation)
            - "contains": Word contains the target (default)
            - "starts_with": Word starts with target
        use_start: If True, return frame at word START. If False, return frame at word END.
        offset_frames: Number of frames to add to the result (negative = earlier).

    Returns:
        Frame number when the word starts/ends (plus offset), or None if not found.
    """
    target_lower = target_word.lower().strip()
    # Also strip punctuation from target for matching
    target_clean = re.sub(r"[.,!?;:'\"]+$", "", target_lower)

    for ts in word_timestamps:
        word = ts.get("word", "")
        # Strip common punctuation for matching
        word_clean = re.sub(r"[.,!?;:'\"]+$", "", word.lower().strip())

        matched = False
        if match_mode == "exact":
            matched = word_clean == target_clean
        elif match_mode == "contains":
            matched = target_clean in word_clean or word_clean in target_clean
        elif match_mode == "starts_with":
            matched = word_clean.startswith(target_clean)

        if matched:
            # Return frame at start or end of word
            if use_start:
                time_seconds = ts.get("start_seconds", 0)
            else:
                time_seconds = ts.get("end_seconds", 0)
            return int(time_seconds * fps) + offset_frames

    return None


def find_word_frame_fuzzy(
    word_timestamps: list[dict[str, Any]],
    target_word: str,
    fps: int = 30,
    use_start: bool = True,
    offset_frames: int = 0,
) -> Optional[int]:
    """Find word frame with fuzzy matching, trying multiple strategies.

    Args:
        word_timestamps: List of word timestamp dicts.
        target_word: The word to find.
        fps: Frames per second.
        use_start: If True, return frame at word START.
        offset_frames: Number of frames to add to the result.

    Returns:
        Frame number or None if not found.
    """
    # Try exact match first
    frame = find_word_frame(word_timestamps, target_word, fps, "exact", use_start, offset_frames)
    if frame is not None:
        return frame

    # Try contains match
    frame = find_word_frame(word_timestamps, target_word, fps, "contains", use_start, offset_frames)
    if frame is not None:
        return frame

    # Try starts_with match
    frame = find_word_frame(word_timestamps, target_word, fps, "starts_with", use_start, offset_frames)
    if frame is not None:
        return frame

    return None


def find_word_index(
    word_timestamps: list[dict[str, Any]],
    target_word: str,
) -> Optional[int]:
    """Find the index of a word in the timestamps list.

    Args:
        word_timestamps: List of word timestamp dicts.
        target_word: The word to find.

    Returns:
        Index of the word or None if not found.
    """
    target_clean = re.sub(r"[.,!?;:'\"]+$", "", target_word.lower().strip())

    for i, ts in enumerate(word_timestamps):
        word = ts.get("word", "")
        word_clean = re.sub(r"[.,!?;:'\"]+$", "", word.lower().strip())

        # Try exact match
        if word_clean == target_clean:
            return i
        # Try contains match
        if target_clean in word_clean or word_clean in target_clean:
            return i

    return None


def extract_timing_vars(code: str) -> list[dict[str, Any]]:
    """Extract timing-related variable declarations from TypeScript/JavaScript code.

    Looks for patterns like:
    - const PHASE = { NUMBERS: [0, 220], ... }
    - const numbersAppear = 120;
    - const TIMING = { duration: 900, ... }

    Args:
        code: The source code to analyze.

    Returns:
        List of dicts with 'name', 'value', 'line' for each timing variable.
    """
    timing_vars = []

    # Pattern 1: Simple numeric constants
    # const numbersAppear = 120;
    simple_pattern = re.compile(
        r"const\s+(\w+)\s*=\s*(\d+)\s*;",
        re.MULTILINE
    )
    for match in simple_pattern.finditer(code):
        name = match.group(1)
        value = int(match.group(2))
        # Filter to likely timing variables (not IDs, sizes, etc.)
        if _is_likely_timing_var(name):
            timing_vars.append({
                "name": name,
                "value": value,
                "type": "simple",
                "line": code[:match.start()].count("\n") + 1,
            })

    # Pattern 2: Object with numeric values (PHASE pattern)
    # const PHASE = { NUMBERS: [0, 220], COMBINED: [200, 800] }
    object_pattern = re.compile(
        r"const\s+(PHASE|TIMING|FRAMES|KEYFRAMES)\s*=\s*\{([^}]+)\}",
        re.MULTILINE | re.IGNORECASE
    )
    for match in object_pattern.finditer(code):
        obj_name = match.group(1)
        obj_content = match.group(2)

        # Extract individual properties
        prop_pattern = re.compile(r"(\w+)\s*:\s*\[?\s*(\d+)")
        for prop_match in prop_pattern.finditer(obj_content):
            prop_name = prop_match.group(1)
            prop_value = int(prop_match.group(2))
            timing_vars.append({
                "name": f"{obj_name}.{prop_name}",
                "value": prop_value,
                "type": "object_property",
                "line": code[:match.start()].count("\n") + 1,
            })

    # Pattern 3: Inline frame numbers in interpolate() calls
    # interpolate(f, [180, 220], ...)
    interpolate_pattern = re.compile(
        r"interpolate\s*\(\s*\w+\s*,\s*\[\s*(\d+)\s*,\s*(\d+)\s*\]",
        re.MULTILINE
    )
    for match in interpolate_pattern.finditer(code):
        start_frame = int(match.group(1))
        end_frame = int(match.group(2))
        line = code[:match.start()].count("\n") + 1
        timing_vars.append({
            "name": f"interpolate_range_{line}",
            "value": [start_frame, end_frame],
            "type": "interpolate",
            "line": line,
        })

    # Pattern 4: spring() frame offsets
    # spring({ frame: Math.max(0, f - 220), ... })
    spring_pattern = re.compile(
        r"spring\s*\(\s*\{[^}]*frame\s*:\s*(?:Math\.max\s*\(\s*\d+\s*,\s*)?\w+\s*-\s*(\d+)",
        re.MULTILINE
    )
    for match in spring_pattern.finditer(code):
        frame_offset = int(match.group(1))
        line = code[:match.start()].count("\n") + 1
        timing_vars.append({
            "name": f"spring_offset_{line}",
            "value": frame_offset,
            "type": "spring",
            "line": line,
        })

    return timing_vars


def _is_likely_timing_var(name: str) -> bool:
    """Check if a variable name is likely a timing-related constant.

    Args:
        name: Variable name to check.

    Returns:
        True if the name suggests timing usage.
    """
    timing_keywords = [
        "frame", "timing", "duration", "start", "end", "delay",
        "appear", "exit", "entrance", "phase", "animation",
        "reveal", "show", "hide", "fade", "transition"
    ]
    name_lower = name.lower()
    return any(kw in name_lower for kw in timing_keywords)


def seconds_to_frames(seconds: float, fps: int = 30) -> int:
    """Convert seconds to frame number.

    Args:
        seconds: Time in seconds.
        fps: Frames per second.

    Returns:
        Frame number.
    """
    return int(seconds * fps)


def frames_to_seconds(frames: int, fps: int = 30) -> float:
    """Convert frame number to seconds.

    Args:
        frames: Frame number.
        fps: Frames per second.

    Returns:
        Time in seconds.
    """
    return frames / fps


def get_scene_duration_frames(duration_seconds: float, fps: int = 30) -> int:
    """Get scene duration in frames.

    Args:
        duration_seconds: Duration in seconds.
        fps: Frames per second.

    Returns:
        Duration in frames.
    """
    return int(duration_seconds * fps)


def validate_trigger_word(
    trigger_word: str,
    word_timestamps: list[dict[str, Any]],
) -> tuple[bool, Optional[str]]:
    """Validate that a trigger word exists in the word timestamps.

    Args:
        trigger_word: The word to validate.
        word_timestamps: List of word timestamp dicts.

    Returns:
        Tuple of (is_valid, suggestion). If not valid, suggestion contains
        a similar word that was found, if any.
    """
    index = find_word_index(word_timestamps, trigger_word)
    if index is not None:
        return True, None

    # Try to find similar words for suggestion
    target_clean = trigger_word.lower().strip()
    suggestions = []

    for ts in word_timestamps:
        word = ts.get("word", "").lower().strip()
        # Check for partial matches
        if target_clean[:3] in word or word[:3] in target_clean:
            suggestions.append(ts.get("word", ""))

    if suggestions:
        return False, suggestions[0]
    return False, None


def camel_to_snake(name: str) -> str:
    """Convert camelCase to snake_case.

    Args:
        name: CamelCase string.

    Returns:
        snake_case string.
    """
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def snake_to_camel(name: str) -> str:
    """Convert snake_case to camelCase.

    Args:
        name: snake_case string.

    Returns:
        camelCase string.
    """
    components = name.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


def format_scene_id(title: str) -> str:
    """Format a scene title into a valid ID.

    Args:
        title: Scene title (e.g., "The Impossible Leap").

    Returns:
        Formatted ID (e.g., "the_impossible_leap").
    """
    # Remove special characters and convert to snake_case
    clean = re.sub(r"[^a-zA-Z0-9\s]", "", title)
    clean = re.sub(r"\s+", "_", clean.strip())
    return clean.lower()
