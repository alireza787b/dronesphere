# tests/test_openrouter_fixed.py
"""
Test script for OpenRouter integration with fixes.

Run from project root: python tests/test_openrouter_fixed.py
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
    LLMProviderFactory,
    OpenRouterConfig,
)


async def test_openrouter_directly():
    """Test OpenRouter provider directly without factory."""
    print("\n=== Testing OpenRouter Provider Directly ===")

    # Create config
    config = OpenRouterConfig(
        api_key=os.getenv("OPENROUTER_API_KEY", "sk-or-dummy-key-for-free-models"),
        model="google/gemma-2-9b-it:free",
        temperature=0.3,
        max_tokens=200,
        command_extraction_temperature=0.1,
        conversation_temperature=0.7,
    )

    print(f"Config created: model={config.model}, temperature={config.temperature}")

    # Import provider directly
    from server.services.llm.providers.openrouter import OpenRouterProvider

    # Create provider
    provider = OpenRouterProvider(config)
    print("✅ Provider created successfully")

    # Test basic generation
    context = ConversationContext(
        session_id="test-session",
        drone_id="test-drone",
    )

    print("\n--- Testing Basic Generation ---")
    try:
        response = await provider.generate_response(
            "Say 'Hello from DroneSphere!' if you can hear me.", context
        )
        print(f"Response: {response}")
        print("✅ Basic generation works")
    except Exception as e:
        print(f"❌ Generation failed: {e}")
        print(f"Error type: {type(e).__name__}")

    # Test command extraction
    print("\n--- Testing Command Extraction ---")
    available_commands = [
        {
            "metadata": {"name": "takeoff", "category": "flight"},
            "spec": {
                "description": {
                    "brief": "Take off to altitude",
                    "examples": [
                        {"text": "Take off to 20 meters", "params": {"altitude": 20}},
                        {
                            "text": "برخیز به ارتفاع ۱۰ متر",
                            "params": {"altitude": 10},
                            "language": "fa",
                        },
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
        }
    ]

    try:
        result = await provider.extract_commands(
            "Take off to 15 meters please", context, available_commands
        )
        print(f"Commands extracted: {len(result.commands)}")
        if result.commands:
            print(f"First command: {result.commands[0]}")
        print(f"Response: {result.response_text}")
        print(f"Confidence: {result.confidence}")
        print("✅ Command extraction works")
    except Exception as e:
        print(f"❌ Command extraction failed: {e}")
        print(f"Error type: {type(e).__name__}")

    # Test health check
    print("\n--- Testing Health Check ---")
    try:
        is_healthy, status = await provider.check_health()
        print(f"Health: {is_healthy}, Status: {status}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")

    return provider


async def test_with_factory():
    """Test using the factory pattern."""
    print("\n=== Testing with Factory Pattern ===")

    # Create a mock settings object
    class MockSettings:
        llm_provider = "openrouter"
        openrouter_api_key = os.getenv("OPENROUTER_API_KEY", "sk-or-dummy-key")
        openrouter_base_url = "https://openrouter.ai/api/v1"
        openrouter_model = "google/gemma-2-9b-it:free"
        openrouter_temperature = 0.3
        openrouter_max_tokens = 200

    settings = MockSettings()

    try:
        provider = LLMProviderFactory.create_from_settings(settings)
        print("✅ Provider created via factory")

        # Quick health check
        is_healthy, status = await provider.check_health()
        print(f"Health: {is_healthy}, Status: {status}")

    except Exception as e:
        print(f"❌ Factory creation failed: {e}")


async def main():
    """Run all tests."""
    print("=" * 50)
    print("OpenRouter Integration Test (Fixed)")
    print("=" * 50)

    # Test OpenRouter directly
    await test_openrouter_directly()

    # Test with factory
    await test_with_factory()

    print("\n" + "=" * 50)
    print("Test Complete!")
    print("=" * 50)


if __name__ == "__main__":
    # Check environment
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("\n⚠️  Warning: OPENROUTER_API_KEY not set")
        print("The test will try to use free models which may work without a key")
        print("For best results, set: export OPENROUTER_API_KEY='your-key-here'")

    asyncio.run(main())
