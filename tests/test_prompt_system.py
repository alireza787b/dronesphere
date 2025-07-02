# tests/test_prompt_system.py
"""
Test the new multi-layer prompt system.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "server" / "src"))

from server.services.llm import ConversationContext, OpenRouterConfig
from server.services.llm.providers.openrouter import OpenRouterProvider
from server.services.llm.prompts.builder import prompt_builder


def test_prompt_generation():
    """Test prompt generation with different scenarios."""
    print("=" * 60)
    print("TESTING PROMPT GENERATION SYSTEM")
    print("=" * 60)
    
    # Test scenarios
    test_cases = [
        {
            "name": "Simple command",
            "input": "Take off to 20 meters",
            "commands": [{
                "metadata": {"name": "takeoff"},
                "spec": {
                    "description": {"brief": "Take off to altitude"},
                    "parameters": {
                        "altitude": {"type": "float", "required": True}
                    }
                }
            }]
        },
        {
            "name": "Complex movement",
            "input": "Move 5 meters north, 2 meters east, and climb 1 meter",
            "commands": [{
                "metadata": {"name": "move_local"},
                "spec": {
                    "description": {"brief": "Move in local coordinates"},
                    "parameters": {
                        "north": {"type": "float", "required": False, "default": 0},
                        "east": {"type": "float", "required": False, "default": 0},
                        "down": {"type": "float", "required": False, "default": 0}
                    }
                }
            }]
        }
    ]
    
    for test in test_cases:
        print(f"\n--- {test['name']} ---")
        print(f"Input: {test['input']}")
        
        prompt = prompt_builder.build_extraction_prompt(
            user_input=test["input"],
            available_commands=test["commands"],
            context={"drone_id": "test-01", "status": "ready", "battery": 85}
        )
        
        print(f"\nGenerated prompt length: {len(prompt)} chars")
        print("\nFirst 500 chars of prompt:")
        print("-" * 40)
        print(prompt[:500])
        print("-" * 40)


async def test_with_llm():
    """Test the complete system with actual LLM."""
    print("\n" + "=" * 60)
    print("TESTING WITH ACTUAL LLM")
    print("=" * 60)
    
    config = OpenRouterConfig(
        api_key=os.getenv("OPENROUTER_API_KEY", "dummy-key"),
        model="google/gemma-2-9b-it:free",
        temperature=0.1
    )
    
    provider = OpenRouterProvider(config)
    context = ConversationContext(
        session_id="test-prompt-system",
        drone_id="test-drone"
    )
    
    commands = [{
        "metadata": {"name": "takeoff", "category": "flight"},
        "spec": {
            "description": {
                "brief": "Take off to altitude",
                "examples": [{"text": "Take off to 20m", "params": {"altitude": 20}}]
            },
            "parameters": {
                "altitude": {"type": "float", "required": True, "default": 10}
            }
        }
    }]
    
    test_inputs = [
        "Take off to 15 meters",
        "Land the drone",
        "Fly high",
        "Move 5m north and 2m east"
    ]
    
    for test_input in test_inputs:
        print(f"\n--- Testing: {test_input} ---")
        try:
            result = await provider.extract_commands(test_input, context, commands)
            print(f"Success: {len(result.commands)} commands extracted")
            print(f"Response: {result.response_text}")
            print(f"JSON output obtained: {'commands' in result.dict()}")
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    # Test prompt generation
    test_prompt_generation()
    
    # Test with actual LLM
    asyncio.run(test_with_llm())