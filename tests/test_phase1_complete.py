# tests/test_phase1_complete.py
"""
Complete Phase 1 validation test.
Tests the entire LLM infrastructure with multiple scenarios.
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


async def test_complete_pipeline():
    """Test the complete pipeline with various scenarios."""
    print("=" * 60)
    print("PHASE 1 COMPLETE VALIDATION TEST")
    print("=" * 60)

    # Create provider
    config = OpenRouterConfig(
        api_key=os.getenv("OPENROUTER_API_KEY", "dummy-key-for-free-model"),
        model="google/gemma-2-9b-it:free",
        temperature=0.1,
        command_extraction_temperature=0.1,
    )

    provider = OpenRouterProvider(config)

    # Create context
    context = ConversationContext(
        session_id="test-complete",
        drone_id="test-drone-01",
        drone_state={"status": "ready", "battery": 85},
    )

    # Define available commands (current)
    available_commands = [
        {
            "metadata": {"name": "takeoff", "category": "flight"},
            "spec": {
                "description": {
                    "brief": "Take off to specified altitude",
                    "examples": [
                        {"text": "Take off to 20 meters", "params": {"altitude": 20}},
                        {"text": "Launch to 10m", "params": {"altitude": 10}},
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
                    "brief": "Land at current position",
                    "examples": [
                        {"text": "Land now", "params": {}},
                        {"text": "Touch down", "params": {}},
                    ],
                },
                "parameters": {},
            },
        },
    ]

    # Test scenarios
    test_cases = [
        {
            "name": "Simple takeoff",
            "input": "Take off to 15 meters please",
            "expected_command": "takeoff",
            "expected_params": {"altitude": 15},
        },
        {
            "name": "Simple land",
            "input": "Land the drone now",
            "expected_command": "land",
            "expected_params": {},
        },
        {
            "name": "Ambiguous altitude",
            "input": "Take off high",
            "expected_clarification": True,
        },
        {
            "name": "Multiple commands",
            "input": "Take off to 10 meters and then land",
            "expected_commands": ["takeoff", "land"],
        },
        {
            "name": "Persian input",
            "input": "برخیز به ارتفاع ۲۰ متر",
            "expected_command": "takeoff",
            "expected_language": "fa",
        },
    ]

    # Run tests
    for i, test in enumerate(test_cases):
        print(f"\n--- Test {i+1}: {test['name']} ---")
        print(f"Input: {test['input']}")

        try:
            result = await provider.extract_commands(
                test["input"], context, available_commands
            )

            print(f"Commands: {len(result.commands)}")
            for cmd in result.commands:
                print(f"  - {cmd['name']}: {cmd.get('parameters', {})}")
            print(f"Response: {result.response_text}")
            print(f"Confidence: {result.confidence}")
            print(f"Language: {result.detected_language}")
            print(f"Needs clarification: {result.requires_clarification}")

            # Validate expectations
            if "expected_command" in test:
                assert len(result.commands) > 0
                assert result.commands[0]["name"] == test["expected_command"]
                print("✅ Command name matches")

            if "expected_params" in test:
                for key, value in test["expected_params"].items():
                    assert result.commands[0]["parameters"][key] == value
                print("✅ Parameters match")

            if "expected_clarification" in test:
                assert result.requires_clarification == test["expected_clarification"]
                print("✅ Clarification requirement matches")

            if "expected_commands" in test:
                cmd_names = [cmd["name"] for cmd in result.commands]
                assert cmd_names == test["expected_commands"]
                print("✅ Multiple commands extracted correctly")

            if "expected_language" in test:
                assert result.detected_language == test["expected_language"]
                print("✅ Language detected correctly")

        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback

            traceback.print_exc()

    # Test health check
    print("\n--- Health Check ---")
    is_healthy, status = await provider.check_health()
    print(f"Health: {is_healthy}, Status: {status}")

    print("\n" + "=" * 60)
    print("PHASE 1 VALIDATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_complete_pipeline())
