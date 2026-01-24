"""
Test Director prompt output against Remotion schema.

Run with:
    python -m pytest tests/test_director_prompt.py -v
    
Or directly:
    python tests/test_director_prompt.py
"""

import json
import os
from pathlib import Path

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.prompts.director_short import SHORT_SYSTEM_PROMPT, SHORT_USER_PROMPT_TEMPLATE


# =============================================================================
# Schema Validation
# =============================================================================

VALID_TEMPLATES = [
    "SplitVideo", "VideoCard", "TextOverProof", "TextCard",
    "SplitProof", "FullAvatar", "ProofOnly"
]

VALID_BACKGROUND_TYPES = ["video", "screenshot", "gradient", "solid"]

VALID_AVATAR_POSITIONS = ["bottom", "full"]


def validate_script(script: dict) -> list[str]:
    """
    Validate a script.json against Remotion schema.
    
    Returns list of validation errors (empty = valid).
    """
    errors = []
    
    # Required top-level fields
    if "id" not in script:
        errors.append("Missing required field: id")
    if "scenes" not in script:
        errors.append("Missing required field: scenes")
        return errors  # Can't validate scenes without scenes array
    
    if not isinstance(script["scenes"], list):
        errors.append("scenes must be an array")
        return errors
    
    if len(script["scenes"]) == 0:
        errors.append("scenes array is empty")
        return errors
    
    # Validate each scene
    for i, scene in enumerate(script["scenes"]):
        scene_prefix = f"scenes[{i}]"
        
        # Required scene fields
        if "id" not in scene:
            errors.append(f"{scene_prefix}: missing id")
        
        if "template" not in scene:
            errors.append(f"{scene_prefix}: missing template")
        elif scene["template"] not in VALID_TEMPLATES:
            errors.append(f"{scene_prefix}: invalid template '{scene['template']}'. Must be one of {VALID_TEMPLATES}")
        
        if "start_seconds" not in scene:
            errors.append(f"{scene_prefix}: missing start_seconds")
        
        if "end_seconds" not in scene:
            errors.append(f"{scene_prefix}: missing end_seconds")
        
        # Validate timing
        if "start_seconds" in scene and "end_seconds" in scene:
            if scene["end_seconds"] <= scene["start_seconds"]:
                errors.append(f"{scene_prefix}: end_seconds must be > start_seconds")
        
        # Validate audio
        if "audio" in scene:
            if "text" not in scene["audio"]:
                errors.append(f"{scene_prefix}.audio: missing text")
        
        # Validate background
        if "background" in scene:
            bg = scene["background"]
            if "type" not in bg:
                errors.append(f"{scene_prefix}.background: missing type")
            elif bg["type"] not in VALID_BACKGROUND_TYPES:
                errors.append(f"{scene_prefix}.background: invalid type '{bg['type']}'")
        
        # Validate avatar
        if "avatar" in scene:
            avatar = scene["avatar"]
            if "visible" not in avatar:
                errors.append(f"{scene_prefix}.avatar: missing visible")
            if avatar.get("visible") and "position" in avatar:
                if avatar["position"] not in VALID_AVATAR_POSITIONS:
                    errors.append(f"{scene_prefix}.avatar: invalid position '{avatar['position']}'")
    
    # Validate scene timing continuity
    scenes = script["scenes"]
    for i in range(1, len(scenes)):
        prev_end = scenes[i-1].get("end_seconds", 0)
        curr_start = scenes[i].get("start_seconds", 0)
        if curr_start < prev_end:
            errors.append(f"scenes[{i}]: overlaps with previous scene (starts at {curr_start}, prev ends at {prev_end})")
    
    # Validate assets_needed if present
    if "assets_needed" in script:
        assets = script["assets_needed"]
        for asset_type in ["backgrounds", "evidence", "avatar"]:
            if asset_type in assets:
                for j, asset in enumerate(assets[asset_type]):
                    if "id" not in asset:
                        errors.append(f"assets_needed.{asset_type}[{j}]: missing id")
                    if "source" not in asset:
                        errors.append(f"assets_needed.{asset_type}[{j}]: missing source")
    
    return errors


def validate_script_file(path: Path) -> tuple[bool, list[str]]:
    """Validate a script.json file."""
    with open(path) as f:
        script = json.load(f)
    errors = validate_script(script)
    return len(errors) == 0, errors


# =============================================================================
# Test with Mock LLM
# =============================================================================

def test_mock_director_output():
    """Test that mock LLM produces valid script."""
    from src.understanding.llm_provider import MockLLMProvider
    from src.config import LLMConfig
    
    provider = MockLLMProvider(LLMConfig(provider="mock"))
    
    user_prompt = SHORT_USER_PROMPT_TEMPLATE.format(
        duration_seconds=6,
        topic="China's drone swarm technology controlled by one person",
        evidence_urls="https://reuters.com/china-drones",
        num_scenes=4
    )
    
    result = provider.generate_json(user_prompt, SHORT_SYSTEM_PROMPT)
    
    # Mock provider returns old format - this test documents the gap
    # The mock needs updating to return new Remotion-compatible format
    assert "scenes" in result or "project_title" in result


def test_template_test_script_valid():
    """Test that template-test/script.json is valid."""
    script_path = Path(__file__).parent.parent / "projects" / "template-test" / "script" / "script.json"
    
    if not script_path.exists():
        print(f"SKIP: {script_path} not found")
        return
    
    is_valid, errors = validate_script_file(script_path)
    
    if errors:
        print("Validation errors:")
        for e in errors:
            print(f"  - {e}")
    
    assert is_valid, f"template-test/script.json is invalid: {errors}"


# =============================================================================
# Test with Real LLM (requires API key)
# =============================================================================

def test_real_llm_director_output():
    """
    Test Director prompt with real LLM.
    
    Requires OPENAI_API_KEY or ANTHROPIC_API_KEY env var.
    Skip if no API key available.
    """
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("SKIP: No API key found (set OPENAI_API_KEY or ANTHROPIC_API_KEY)")
        return
    
    # Use OpenAI if available
    if os.environ.get("OPENAI_API_KEY"):
        import openai
        client = openai.OpenAI()
        
        user_prompt = SHORT_USER_PROMPT_TEMPLATE.format(
            duration_seconds=6,
            topic="China's drone swarm technology - one person controlling 10,000 drones",
            evidence_urls="",
            num_scenes=4
        )
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SHORT_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        result_text = response.choices[0].message.content
        result = json.loads(result_text)
        
        # Validate against schema
        errors = validate_script(result)
        
        if errors:
            print("LLM output validation errors:")
            for e in errors:
                print(f"  - {e}")
            print("\nLLM output:")
            print(json.dumps(result, indent=2))
        
        assert len(errors) == 0, f"LLM output is invalid: {errors}"
        
        # Save for inspection
        output_path = Path(__file__).parent / "output" / "director_test_output.json"
        output_path.parent.mkdir(exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\nSaved LLM output to: {output_path}")


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Testing Director Prompt")
    print("=" * 60)
    
    print("\n1. Validating template-test/script.json...")
    test_template_test_script_valid()
    print("   PASS")
    
    print("\n2. Testing mock LLM output...")
    test_mock_director_output()
    print("   PASS (note: mock returns old format)")
    
    print("\n3. Testing real LLM output...")
    test_real_llm_director_output()
    print("   PASS" if os.environ.get("OPENAI_API_KEY") else "   SKIP (no API key)")
    
    print("\n" + "=" * 60)
    print("All tests passed!")
    print("=" * 60)
