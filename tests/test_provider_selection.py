# tests/test_provider_selection.py
"""
Test script to check which LLM provider works and run tests.

Automatically detects which provider is configured and available.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "server" / "src"))

from server.core.config import ServerSettings, get_settings
from server.services.llm import ConversationContext
from server.services.llm.config import (
    OpenRouterConfig, 
    OllamaConfig, 
    LLMProvider,
    LLMConfigFactory
)
from server.services.llm.factory import LLMProviderFactory


async def test_provider(provider_name: str, settings: ServerSettings) -> Tuple[bool, str, Optional[Any]]:
    """
    Test a specific provider.
    
    Returns:
        Tuple of (success, message, provider_instance)
    """
    print(f"\n🔍 Testing {provider_name}...")
    
    try:
        # Create provider config based on settings
        if provider_name == "openrouter":
            if not settings.openrouter_api_key or settings.openrouter_api_key == "your-openrouter-key-here":
                return False, "No API key configured", None
                
            config = OpenRouterConfig(
                api_key=settings.openrouter_api_key,
                base_url=settings.openrouter_base_url,
                model=settings.openrouter_model,
                temperature=settings.openrouter_temperature,
                max_tokens=settings.openrouter_max_tokens,
            )
            
        elif provider_name == "ollama":
            config = OllamaConfig(
                base_url=settings.ollama_host,
                model=settings.ollama_model,
            )
            
        else:
            return False, f"Unknown provider: {provider_name}", None
        
        # Create provider
        provider = LLMProviderFactory.create_provider(config)
        
        # Test health
        is_healthy, status = await provider.check_health()
        
        if not is_healthy:
            return False, f"Health check failed: {status}", None
        
        # Test actual extraction
        context = ConversationContext(
            session_id="test-provider",
            drone_id="test-drone"
        )
        
        commands = [{
            "metadata": {"name": "takeoff", "category": "flight"},
            "spec": {
                "description": {"brief": "Take off to altitude"},
                "parameters": {
                    "altitude": {"type": "float", "required": True, "default": 10}
                }
            }
        }]
        
        result = await provider.extract_commands(
            "Take off to 20 meters",
            context,
            commands
        )
        
        if result.commands and result.commands[0]["name"] == "takeoff":
            return True, f"✅ {provider_name} working! Model: {config.model}", provider
        else:
            return False, "Command extraction failed", provider
            
    except Exception as e:
        return False, f"Error: {str(e)}", None


async def run_comprehensive_test(provider):
    """Run comprehensive tests with the working provider."""
    print("\n" + "=" * 70)
    print("RUNNING COMPREHENSIVE TESTS")
    print("=" * 70)
    
    context = ConversationContext(
        session_id="test-comprehensive",
        drone_id="test-drone-01"
    )
    
    commands = [
        {
            "metadata": {"name": "takeoff", "category": "flight"},
            "spec": {
                "description": {"brief": "Take off to altitude"},
                "parameters": {
                    "altitude": {"type": "float", "required": True, "default": 10}
                }
            }
        },
        {
            "metadata": {"name": "land", "category": "flight"},
            "spec": {
                "description": {"brief": "Land at current position"},
                "parameters": {}
            }
        },
        {
            "metadata": {"name": "move_local", "category": "navigation"},
            "spec": {
                "description": {"brief": "Move in local NED coordinates"},
                "parameters": {
                    "north": {"type": "float", "required": False, "default": 0},
                    "east": {"type": "float", "required": False, "default": 0},
                    "down": {"type": "float", "required": False, "default": 0}
                }
            }
        }
    ]
    
    test_cases = [
        ("Simple takeoff", "Take off to 15 meters"),
        ("Simple land", "Land now"),
        ("Complex movement", "Move 5m north, 2m east, and climb 3m"),
        ("Command sequence", "Take off to 10m, move 5m north, then land"),
        ("Persian", "برخیز به ارتفاع ۲۰ متر"),
        ("Ambiguous", "Fly somewhere high"),
    ]
    
    passed = 0
    for name, test_input in test_cases:
        print(f"\n--- {name} ---")
        print(f"Input: {test_input}")
        
        try:
            result = await provider.extract_commands(test_input, context, commands)
            
            print(f"Commands: {len(result.commands)}")
            for cmd in result.commands:
                print(f"  - {cmd['name']}: {cmd.get('parameters', {})}")
            print(f"Response: {result.response_text}")
            print(f"Language: {result.detected_language}")
            print(f"Confidence: {result.confidence}")
            
            if result.commands or result.requires_clarification:
                print("✅ PASS")
                passed += 1
            else:
                print("❌ FAIL")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
    
    print(f"\n📊 Results: {passed}/{len(test_cases)} tests passed")


async def main():
    """Main test function."""
    print("=" * 70)
    print("LLM PROVIDER DETECTION AND TESTING")
    print("=" * 70)
    
    # Load settings
    settings = get_settings()
    
    print(f"\n📋 Configuration:")
    print(f"  Primary provider: {settings.llm_provider}")
    print(f"  Fallback provider: {settings.llm_fallback_provider or 'none'}")
    
    # Test primary provider
    primary_works, primary_msg, primary_provider = await test_provider(
        settings.llm_provider, 
        settings
    )
    print(f"  Primary: {primary_msg}")
    
    # Test fallback if configured
    fallback_provider = None
    if settings.llm_fallback_provider:
        fallback_works, fallback_msg, fallback_provider = await test_provider(
            settings.llm_fallback_provider,
            settings
        )
        print(f"  Fallback: {fallback_msg}")
    
    # Determine which provider to use
    if primary_works:
        print(f"\n✅ Using primary provider: {settings.llm_provider}")
        await run_comprehensive_test(primary_provider)
    elif fallback_provider:
        print(f"\n✅ Using fallback provider: {settings.llm_fallback_provider}")
        await run_comprehensive_test(fallback_provider)
    else:
        print("\n❌ No working LLM provider found!")
        print("\n💡 Suggestions:")
        print("  1. For OpenRouter: Set OPENROUTER_API_KEY in .env")
        print("  2. For Ollama: Make sure Ollama is running and accessible")
        print("     - Install: curl -fsSL https://ollama.com/install.sh | sh")
        print("     - Run: ollama serve")
        print("     - Pull model: ollama pull deepseek:latest")
        print("  3. Check your .env configuration")


if __name__ == "__main__":
    asyncio.run(main())