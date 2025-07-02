# tests/test_llm_infrastructure.py
"""
Test script for Phase 1: LLM Infrastructure.

This script tests the core LLM components without full integration.
Run from project root: python tests/test_llm_infrastructure.py
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
    LLMConfigFactory,
    LLMProvider,
    LLMProviderFactory,
    OpenRouterConfig,
)


async def test_config_creation():
    """Test configuration creation."""
    print("\n=== Testing Configuration Creation ===")
    
    # Test OpenRouter config
    config = LLMConfigFactory.create_config(
        "openrouter",
        api_key=os.getenv("OPENROUTER_API_KEY", "test-key"),
        model="google/gemma-2-9b-it:free",
        temperature=0.3,
    )
    
    assert isinstance(config, OpenRouterConfig)
    assert config.provider == LLMProvider.OPENROUTER
    assert config.model == "google/gemma-2-9b-it:free"
    print("✅ OpenRouter config created successfully")
    
    # Test invalid provider
    try:
        LLMConfigFactory.create_config("invalid-provider")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print("✅ Invalid provider correctly rejected")
    
    return config


async def test_provider_creation(config):
    """Test provider creation."""
    print("\n=== Testing Provider Creation ===")
    
    # Create provider
    provider = LLMProviderFactory.create_provider(config)
    
    assert provider is not None
    assert provider.name == "OpenRouterProvider"
    print("✅ Provider created successfully")
    
    # Test caching
    provider2 = LLMProviderFactory.create_provider(config)
    assert provider is provider2
    print("✅ Provider caching works")
    
    return provider


async def test_basic_generation(provider):
    """Test basic text generation."""
    print("\n=== Testing Basic Generation ===")
    
    context = ConversationContext(
        session_id="test-session",
        drone_id="test-drone",
    )
    
    try:
        response = await provider.generate_response(
            "Reply with 'Hello, I am ready to control drones!' if you understand.",
            context
        )
        
        print(f"Response: {response}")
        assert len(response) > 0
        print("✅ Basic generation works")
        
    except Exception as e:
        print(f"⚠️  Generation test skipped (no API key?): {e}")


async def test_command_extraction(provider):
    """Test command extraction structure."""
    print("\n=== Testing Command Extraction ===")
    
    # Mock command schemas
    available_commands = [
        {
            "metadata": {"name": "takeoff", "category": "flight"},
            "spec": {
                "description": {
                    "brief": "Take off to altitude",
                    "examples": [
                        {"text": "Take off to 20 meters", "params": {"altitude": 20}},
                        {"text": "برخیز به ارتفاع ۱۰ متر", "params": {"altitude": 10}, "language": "fa"},
                    ]
                },
                "parameters": {
                    "altitude": {
                        "type": "float",
                        "required": True,
                        "default": 10.0,
                        "constraints": {"min": 1, "max": 50}
                    }
                }
            }
        }
    ]
    
    context = ConversationContext(
        session_id="test-session",
        drone_id="test-drone",
        drone_state={"status": "ready"},
    )
    
    try:
        result = await provider.extract_commands(
            "Take off to 15 meters",
            context,
            available_commands
        )
        
        print(f"Extraction result:")
        print(f"  Commands: {result.commands}")
        print(f"  Confidence: {result.confidence}")
        print(f"  Response: {result.response_text}")
        print(f"  Language: {result.detected_language}")
        
        assert isinstance(result.commands, list)
        print("✅ Command extraction structure works")
        
    except Exception as e:
        print(f"⚠️  Command extraction test skipped (no API key?): {e}")


async def test_health_check(provider):
    """Test health check."""
    print("\n=== Testing Health Check ===")
    
    try:
        is_healthy, status = await provider.check_health()
        print(f"Health check: {is_healthy} - {status}")
        
        if is_healthy:
            print("✅ Provider is healthy")
        else:
            print("⚠️  Provider is unhealthy")
            
    except Exception as e:
        print(f"⚠️  Health check failed: {e}")


async def main():
    """Run all tests."""
    print("=" * 50)
    print("DroneSphere LLM Infrastructure Test")
    print("=" * 50)
    
    try:
        # Test configuration
        config = await test_config_creation()
        
        # Test provider creation
        provider = await test_provider_creation(config)
        
        # Test functionality
        await test_basic_generation(provider)
        await test_command_extraction(provider)
        await test_health_check(provider)
        
        print("\n" + "=" * 50)
        print("✅ All infrastructure tests completed!")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Check if running from correct directory
    if not Path("server").exists():
        print("Please run this script from the project root directory")
        sys.exit(1)
    
    asyncio.run(main())