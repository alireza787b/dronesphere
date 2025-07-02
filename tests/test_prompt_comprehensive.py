# tests/test_prompt_comprehensive.py
"""
Comprehensive test suite for the prompt system.
Tests multiple languages, command queuing, and edge cases.
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


async def test_comprehensive():
    """Run comprehensive tests with various scenarios."""
    print("=" * 70)
    print("COMPREHENSIVE PROMPT SYSTEM TEST")
    print("=" * 70)
    
    # Initialize provider
    config = OpenRouterConfig(
        api_key=os.getenv("OPENROUTER_API_KEY", "dummy-key"),
        model="google/gemma-2-9b-it:free",
        temperature=0.1
    )
    
    provider = OpenRouterProvider(config)
    context = ConversationContext(
        session_id="test-comprehensive",
        drone_id="test-drone-01",
        drone_state={"status": "ready", "battery": 85}
    )
    
    # Define available commands
    commands = [
        {
            "metadata": {"name": "takeoff", "category": "flight"},
            "spec": {
                "description": {"brief": "Take off to specified altitude"},
                "parameters": {
                    "altitude": {"type": "float", "required": True, "default": 10.0}
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
                    "north": {"type": "float", "required": False, "default": 0.0},
                    "east": {"type": "float", "required": False, "default": 0.0},
                    "down": {"type": "float", "required": False, "default": 0.0}
                }
            }
        }
    ]
    
    # Test cases
    test_cases = [
        # English tests
        {
            "name": "Simple takeoff",
            "input": "Take off to 20 meters",
            "expected_commands": 1,
            "expected_name": "takeoff",
            "expected_params": {"altitude": 20.0}
        },
        {
            "name": "Command queue",
            "input": "Take off to 10 meters, then move 5 meters north, and finally land",
            "expected_commands": 3,
            "expected_sequence": ["takeoff", "move_local", "land"]
        },
        {
            "name": "Complex movement",
            "input": "Move 5m north, 2m east, and climb 3m",
            "expected_commands": 1,
            "expected_name": "move_local",
            "expected_params": {"north": 5.0, "east": 2.0, "down": -3.0}
        },
        {
            "name": "Ambiguous command",
            "input": "Fly somewhere high",
            "expected_clarification": True
        },
        
        # Persian tests
        {
            "name": "Persian takeoff",
            "input": "برخیز به ارتفاع ۱۵ متر",
            "expected_commands": 1,
            "expected_name": "takeoff",
            "expected_language": "fa"
        },
        {
            "name": "Persian land",
            "input": "فرود بیا",
            "expected_commands": 1,
            "expected_name": "land",
            "expected_language": "fa"
        },
        
        # Spanish test
        {
            "name": "Spanish takeoff",
            "input": "Despegar a 25 metros",
            "expected_commands": 1,
            "expected_name": "takeoff",
            "expected_language": "es"
        },
        
        # Edge cases
        {
            "name": "Unknown command",
            "input": "Do a barrel roll",
            "expected_commands": 0,
            "expected_clarification": True
        },
        {
            "name": "Mixed valid/invalid",
            "input": "Take off to 15m and do a flip",
            "expected_commands": 1,
            "expected_name": "takeoff"
        }
    ]
    
    # Run tests
    passed = 0
    failed = 0
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n--- Test {i}: {test['name']} ---")
        print(f"Input: {test['input']}")
        
        try:
            result = await provider.extract_commands(
                test["input"],
                context,
                commands
            )
            
            # Basic info
            print(f"Commands: {len(result.commands)}")
            if result.commands:
                for j, cmd in enumerate(result.commands):
                    print(f"  [{j+1}] {cmd['name']}: {cmd.get('parameters', {})}")
            print(f"Response: {result.response_text}")
            print(f"Language: {result.detected_language}")
            print(f"Confidence: {result.confidence}")
            print(f"Needs clarification: {result.requires_clarification}")
            
            # Validate expectations
            checks_passed = True
            
            # Check command count
            if "expected_commands" in test:
                if len(result.commands) != test["expected_commands"]:
                    print(f"❌ Expected {test['expected_commands']} commands, got {len(result.commands)}")
                    checks_passed = False
                else:
                    print(f"✅ Command count correct")
            
            # Check command name
            if "expected_name" in test and result.commands:
                if result.commands[0]["name"] != test["expected_name"]:
                    print(f"❌ Expected command '{test['expected_name']}', got '{result.commands[0]['name']}'")
                    checks_passed = False
                else:
                    print(f"✅ Command name correct")
            
            # Check parameters
            if "expected_params" in test and result.commands:
                params = result.commands[0].get("parameters", {})
                for key, value in test["expected_params"].items():
                    if key not in params or params[key] != value:
                        print(f"❌ Parameter {key}: expected {value}, got {params.get(key)}")
                        checks_passed = False
                    else:
                        print(f"✅ Parameter {key} correct")
            
            # Check sequence
            if "expected_sequence" in test:
                actual_sequence = [cmd["name"] for cmd in result.commands]
                if actual_sequence != test["expected_sequence"]:
                    print(f"❌ Expected sequence {test['expected_sequence']}, got {actual_sequence}")
                    checks_passed = False
                else:
                    print(f"✅ Command sequence correct")
            
            # Check clarification
            if "expected_clarification" in test:
                if result.requires_clarification != test["expected_clarification"]:
                    print(f"❌ Expected clarification={test['expected_clarification']}, got {result.requires_clarification}")
                    checks_passed = False
                else:
                    print(f"✅ Clarification requirement correct")
            
            # Check language
            if "expected_language" in test:
                if result.detected_language != test["expected_language"]:
                    print(f"❌ Expected language '{test['expected_language']}', got '{result.detected_language}'")
                    checks_passed = False
                else:
                    print(f"✅ Language detection correct")
            
            # Check JSON format (no markdown)
            raw_response = result.response_text  # This would be from the raw LLM output
            if "```" in str(result):
                print("⚠️  Warning: Markdown detected in output")
            
            if checks_passed:
                print("✅ TEST PASSED")
                passed += 1
            else:
                print("❌ TEST FAILED")
                failed += 1
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
            failed += 1
            import traceback
            traceback.print_exc()
    
    # Summary
    print("\n" + "=" * 70)
    print(f"TEST SUMMARY: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("=" * 70)
    
    return passed, failed


if __name__ == "__main__":
    passed, failed = asyncio.run(test_comprehensive())
    
    # Exit with error code if tests failed
    if failed > 0:
        sys.exit(1)