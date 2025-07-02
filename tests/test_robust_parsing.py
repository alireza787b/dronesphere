# tests/test_robust_parsing.py
"""
Test robust JSON parsing for LLM outputs.

This tests the preprocessing functions that handle:
- Markdown code blocks
- Capitalization issues
- Malformed JSON

Run: python tests/test_robust_parsing.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "server" / "src"))

from server.services.llm.providers.openrouter import OpenRouterProvider


def test_json_extraction():
    """Test JSON extraction from various formats."""
    print("\n=== Testing JSON Extraction ===")
    
    test_cases = [
        # Case 1: Markdown with json tag
        (
            """```json
            {"commands": [{"name": "takeoff"}]}
            ```""",
            '{"commands": [{"name": "takeoff"}]}'
        ),
        # Case 2: Markdown without tag
        (
            """```
            {"commands": [{"name": "land"}]}
            ```""",
            '{"commands": [{"name": "land"}]}'
        ),
        # Case 3: Plain JSON
        (
            '{"commands": [{"name": "hover"}]}',
            '{"commands": [{"name": "hover"}]}'
        ),
        # Case 4: JSON with text before and after
        (
            'Here is the JSON: {"commands": [{"name": "move"}]} That\'s all!',
            '{"commands": [{"name": "move"}]}'
        ),
        # Case 5: Multiple code blocks (should get first)
        (
            """First block:
            ```json
            {"commands": [{"name": "first"}]}
            ```
            Second block:
            ```json
            {"commands": [{"name": "second"}]}
            ```""",
            '{"commands": [{"name": "first"}]}'
        ),
    ]
    
    for i, (input_text, expected) in enumerate(test_cases, 1):
        result = OpenRouterProvider._extract_json_from_llm_output(input_text)
        # Normalize whitespace for comparison
        result_normalized = ' '.join(result.split())
        expected_normalized = ' '.join(expected.split())
        
        if result_normalized == expected_normalized:
            print(f"✅ Test case {i} passed")
        else:
            print(f"❌ Test case {i} failed")
            print(f"   Input: {input_text[:50]}...")
            print(f"   Expected: {expected_normalized}")
            print(f"   Got: {result_normalized}")


def test_key_normalization():
    """Test key normalization for capitalization issues."""
    print("\n=== Testing Key Normalization ===")
    
    test_cases = [
        # Case 1: Commands -> commands
        (
            {"Commands": [{"name": "takeoff"}]},
            {"commands": [{"name": "takeoff"}]}
        ),
        # Case 2: Multiple normalizations
        (
            {
                "Commands": [{"Original_phrase": "test"}],
                "Response_text": "OK",
                "Overall_confidence": 0.9
            },
            {
                "commands": [{"original_phrase": "test"}],
                "response_text": "OK",
                "overall_confidence": 0.9
            }
        ),
        # Case 3: Nested normalization
        (
            {"data": {"Commands": [{"name": "test"}]}},
            {"data": {"commands": [{"name": "test"}]}}
        ),
    ]
    
    for i, (input_dict, expected) in enumerate(test_cases, 1):
        result = OpenRouterProvider._normalize_keys(input_dict)
        
        if result == expected:
            print(f"✅ Test case {i} passed")
        else:
            print(f"❌ Test case {i} failed")
            print(f"   Input: {input_dict}")
            print(f"   Expected: {expected}")
            print(f"   Got: {result}")


def test_full_parsing():
    """Test full parsing pipeline with realistic LLM outputs."""
    print("\n=== Testing Full Parsing Pipeline ===")
    
    # Create a minimal config and provider
    from server.services.llm.config import OpenRouterConfig
    
    config = OpenRouterConfig(
        api_key="test-key",
        model="test-model"
    )
    provider = OpenRouterProvider(config)
    
    test_outputs = [
        # Case 1: Well-formed with markdown
        """```json
        {
            "commands": [{
                "name": "takeoff",
                "category": "flight",
                "parameters": {"altitude": 15},
                "confidence": 1.0,
                "original_phrase": "Take off to 15 meters"
            }],
            "response_text": "Taking off to 15 meters.",
            "requires_clarification": false,
            "clarification_questions": [],
            "detected_language": "en",
            "overall_confidence": 1.0
        }
        ```""",
        
        # Case 2: Capitalized keys
        """
        {
            "Commands": [{
                "name": "land",
                "category": "flight",
                "parameters": {},
                "confidence": 0.95,
                "Original_phrase": "Land the drone"
            }],
            "Response_text": "Landing the drone.",
            "Requires_clarification": false,
            "Clarification_questions": [],
            "Detected_language": "en",
            "Overall_confidence": 0.95
        }
        """,
        
        # Case 3: Extra text around JSON
        """
        I'll help you with that. Here's the command extraction:
        
        {"commands": [{"name": "hover", "category": "flight", "parameters": {"duration": 10}, "confidence": 0.8, "original_phrase": "hover for 10 seconds"}], "response_text": "Hovering for 10 seconds.", "requires_clarification": false, "clarification_questions": [], "detected_language": "en", "overall_confidence": 0.8}
        
        That should work!
        """
    ]
    
    for i, output in enumerate(test_outputs, 1):
        try:
            result = provider._parse_llm_output(output)
            print(f"✅ Test case {i} parsed successfully")
            print(f"   Commands: {len(result.commands)}")
            if result.commands:
                print(f"   First command: {result.commands[0].name}")
            print(f"   Response: {result.response_text[:50]}...")
        except Exception as e:
            print(f"❌ Test case {i} failed: {e}")


def main():
    """Run all tests."""
    print("=" * 50)
    print("Robust LLM Output Parsing Tests")
    print("=" * 50)
    
    test_json_extraction()
    test_key_normalization()
    test_full_parsing()
    
    print("\n" + "=" * 50)
    print("Tests Complete!")


if __name__ == "__main__":
    main()