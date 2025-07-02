# scripts/debug_extraction.py
"""
Debug script for command extraction issues.

This helps troubleshoot parsing problems by showing each step.
Run: python scripts/debug_extraction.py "your command here"
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


async def debug_extraction(user_input: str):
    """Debug command extraction for a specific input."""
    print("\n" + "=" * 50)
    print(f"Debugging: '{user_input}'")
    print("=" * 50)
    
    # Create provider with debug logging
    config = OpenRouterConfig(
        api_key=os.getenv("OPENROUTER_API_KEY", "test-key"),
        model="google/gemma-2-9b-it:free",
        temperature=0.1,
        max_tokens=500,
    )
    
    provider = OpenRouterProvider(config)
    
    # Create context
    context = ConversationContext(
        session_id="debug-session",
        drone_id="debug-drone",
        drone_state={"status": "ready"},
    )
    
    # Minimal command set for testing
    available_commands = [
        {
            "metadata": {"name": "takeoff", "category": "flight"},
            "spec": {
                "description": {
                    "brief": "Take off to altitude",
                    "examples": [{"text": "Take off to 20 meters", "params": {"altitude": 20}}]
                },
                "parameters": {
                    "altitude": {
                        "type": "float",
                        "required": True,
                        "default": 10.0
                    }
                }
            }
        }
    ]
    
    # Override the LLM call to see raw output
    original_agenerate = provider.llm.agenerate
    raw_response = None
    
    async def debug_agenerate(messages):
        nonlocal raw_response
        result = await original_agenerate(messages)
        raw_response = result.generations[0][0].text
        print("\n--- Raw LLM Output ---")
        print(raw_response)
        print("--- End Raw Output ---\n")
        return result
    
    provider.llm.agenerate = debug_agenerate
    
    try:
        # Extract commands
        result = await provider.extract_commands(
            user_input,
            context,
            available_commands
        )
        
        print("\n--- Extraction Result ---")
        print(f"Success: {len(result.commands)} commands extracted")
        print(f"Commands: {result.commands}")
        print(f"Response: {result.response_text}")
        print(f"Confidence: {result.confidence}")
        
        # Show parsing steps if we have raw response
        if raw_response:
            print("\n--- Parsing Steps ---")
            
            # Step 1: Extract JSON
            json_str = provider._extract_json_from_llm_output(raw_response)
            print(f"1. Extracted JSON: {json_str[:100]}...")
            
            # Step 2: Parse JSON
            import json
            try:
                data = json.loads(json_str)
                print("2. JSON parsed successfully")
                
                # Step 3: Normalize
                normalized = provider._normalize_keys(data)
                print(f"3. Normalized keys: {list(normalized.keys())}")
                
            except Exception as e:
                print(f"2. JSON parsing failed: {e}")
        
    except Exception as e:
        print(f"\n❌ Extraction failed: {e}")
        import traceback
        traceback.print_exc()
        
        # Try fallback parsing
        if raw_response:
            print("\n--- Attempting Fallback ---")
            try:
                parsed = provider._parse_llm_output(raw_response)
                print("✅ Fallback parsing succeeded!")
                print(f"Commands: {parsed.commands}")
            except Exception as e2:
                print(f"❌ Fallback also failed: {e2}")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/debug_extraction.py \"your command here\"")
        print("Example: python scripts/debug_extraction.py \"take off to 15 meters\"")
        sys.exit(1)
    
    user_input = " ".join(sys.argv[1:])
    asyncio.run(debug_extraction(user_input))


if __name__ == "__main__":
    main()