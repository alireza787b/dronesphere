# tests/test_command_extraction_e2e.py
"""
End-to-end test for command extraction with robust parsing.

This simulates real LLM responses and tests the full pipeline.
Run: python tests/test_command_extraction_e2e.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "server" / "src"))

from server.services.llm import (
    ConversationContext,
    OpenRouterConfig,
)
from server.services.llm.providers.openrouter import OpenRouterProvider


async def test_with_mock_response():
    """Test with a mock LLM response to verify parsing works."""
    print("\n=== Testing with Mock LLM Response ===")

    # Create provider
    config = OpenRouterConfig(
        api_key=os.getenv("OPENROUTER_API_KEY", "test-key"),
        model="google/gemma-2-9b-it:free",
        temperature=0.1,
    )
    provider = OpenRouterProvider(config)

    # Mock the LLM response by overriding the parse method
    mock_responses = [
        # Response 1: With markdown wrapper
        """```json
        {
            "Commands": [
                {
                    "name": "takeoff",
                    "category": "flight",
                    "parameters": {"altitude": 20},
                    "confidence": 0.95,
                    "original_phrase": "take off to 20 meters"
                }
            ],
            "response_text": "I'll help you take off to 20 meters altitude.",
            "requires_clarification": false,
            "clarification_questions": [],
            "detected_language": "en",
            "overall_confidence": 0.95
        }
        ```""",
        # Response 2: Without markdown, mixed case
        """
        {
            "commands": [
                {
                    "name": "land",
                    "category": "flight",
                    "parameters": {},
                    "confidence": 1.0,
                    "Original_phrase": "land the drone now"
                }
            ],
            "Response_text": "Landing the drone now.",
            "Requires_clarification": false,
            "clarification_questions": [],
            "Detected_language": "en",
            "Overall_confidence": 1.0
        }
        """,
    ]

    for i, mock_response in enumerate(mock_responses, 1):
        print(f"\n--- Test Case {i} ---")
        try:
            # Test the parsing directly
            parsed = provider._parse_llm_output(mock_response)
            print(f"✅ Successfully parsed mock response {i}")
            print(f"   Commands: {len(parsed.commands)}")
            if parsed.commands:
                cmd = parsed.commands[0]
                print(f"   Command: {cmd.name}")
                print(f"   Parameters: {cmd.parameters}")
                print(f"   Confidence: {cmd.confidence}")
            print(f"   Response: {parsed.response_text}")
            print(f"   Language: {parsed.detected_language}")
        except Exception as e:
            print(f"❌ Failed to parse mock response {i}: {e}")


async def test_real_extraction():
    """Test with real OpenRouter API if key is available."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key or api_key == "test-key":
        print("\n=== Skipping Real API Test (No API Key) ===")
        return

    print("\n=== Testing with Real OpenRouter API ===")

    # Create provider
    config = OpenRouterConfig(
        api_key=api_key,
        model="google/gemma-2-9b-it:free",
        temperature=0.1,
        max_tokens=500,
    )
    provider = OpenRouterProvider(config)

    # Create context
    context = ConversationContext(
        session_id="test-session",
        drone_id="test-drone-1",
        drone_state={"status": "ready"},
    )

    # Define available commands
    available_commands = [
        {
            "metadata": {"name": "takeoff", "category": "flight"},
            "spec": {
                "description": {
                    "brief": "Take off to specified altitude",
                    "examples": [
                        {"text": "Take off to 20 meters", "params": {"altitude": 20}},
                        {"text": "Launch to 50 feet", "params": {"altitude": 15.24}},
                    ],
                },
                "parameters": {
                    "altitude": {
                        "type": "float",
                        "required": True,
                        "default": 10.0,
                        "constraints": {"min": 1, "max": 50},
                    }
                },
            },
        },
        {
            "metadata": {"name": "land", "category": "flight"},
            "spec": {
                "description": {
                    "brief": "Land the drone at current position",
                    "examples": [
                        {"text": "Land the drone", "params": {}},
                        {"text": "Touch down", "params": {}},
                    ],
                },
                "parameters": {},
            },
        },
    ]

    # Test inputs
    test_inputs = [
        "Take off to 15 meters",
        "Land the drone safely",
        "First take off to 20 meters, then land",
    ]

    for user_input in test_inputs:
        print(f"\n--- Testing: '{user_input}' ---")
        try:
            result = await provider.extract_commands(
                user_input, context, available_commands
            )

            print("✅ Extraction successful")
            print(f"   Commands found: {len(result.commands)}")
            for j, cmd in enumerate(result.commands):
                print(
                    f"   Command {j+1}: {cmd['name']} with params {cmd.get('parameters', {})}"
                )
            print(f"   Response: {result.response_text}")
            print(f"   Confidence: {result.confidence}")
            print(f"   Language: {result.detected_language}")

        except Exception as e:
            print(f"❌ Extraction failed: {e}")
            import traceback

            traceback.print_exc()


async def main():
    """Run all tests."""
    print("=" * 50)
    print("Command Extraction End-to-End Test")
    print("=" * 50)

    # Test with mock responses
    await test_with_mock_response()

    # Test with real API
    await test_real_extraction()

    print("\n" + "=" * 50)
    print("All tests complete!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
