# scripts/test_nlp_demo.py
"""Demo mission with proper command sequence."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.adapters.output.nlp.factory import NLPServiceFactory
from src.core.domain.value_objects.position import Position

# Colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


async def run_realistic_demo():
    """Run a realistic demo mission with proper drone state management."""
    print(f"\n{BLUE}{'=' * 60}{RESET}")
    print(f"{BLUE}{'Realistic Drone Mission Demo'.center(60)}{RESET}")
    print(f"{BLUE}{'=' * 60}{RESET}\n")
    
    # Create service
    service = NLPServiceFactory.create("spacy")
    
    # Initial context - drone is connected and armed (simulating real scenario)
    context = {
        "drone_state": "ARMED",  # Start armed for demo
        "battery_percent": 90.0,
        "current_altitude": 0.0,
        "current_position": Position(47.3977, 8.5456, 0.0),
        "home_position": Position(47.3977, 8.5456, 0.0),
        "is_armed": True,
    }
    
    print("🚁 Drone Status: CONNECTED and ARMED")
    print(f"📍 Location: {context['current_position']}")
    print(f"🔋 Battery: {context['battery_percent']}%")
    print("\nStarting mission...\n")
    
    # Realistic mission with supported commands
    mission_steps = [
        # Step 1: Takeoff
        {
            "command": "take off to 25 meters",
            "expected_state": "HOVERING",
            "update": {"current_altitude": 25.0}
        },
        
        # Step 2: Move forward
        {
            "command": "move forward 50 meters",
            "expected_state": "FLYING",
            "update": {}
        },
        
        # Step 3: Rotate
        {
            "command": "rotate clockwise 90 degrees",
            "expected_state": "FLYING",
            "update": {}
        },
        
        # Step 4: Move left
        {
            "command": "move left 20 meters",
            "expected_state": "FLYING",
            "update": {}
        },
        
        # Step 5: Hover (stay in place)
        {
            "command": "hover",
            "expected_state": "HOVERING",
            "update": {}
        },
        
        # Step 6: Move up
        {
            "command": "move up 10 meters",
            "expected_state": "FLYING",
            "update": {"current_altitude": 35.0}
        },
        
        # Step 7: Return home
        {
            "command": "return home",
            "expected_state": "FLYING",
            "update": {}
        },
        
        # Step 8: Land
        {
            "command": "land",
            "expected_state": "LANDED",
            "update": {"current_altitude": 0.0, "is_armed": False}
        }
    ]
    
    success_count = 0
    
    for i, step in enumerate(mission_steps, 1):
        command_text = step["command"]
        print(f"Step {i}: \"{command_text}\"")
        
        # Parse command
        result = await service.parse_command(command_text, context)
        
        if result.success:
            # Check feasibility
            is_feasible, reason = await service.validate_feasibility(
                result.command, context
            )
            
            if is_feasible:
                print(f"{GREEN}✅ Executing: {result.command.describe()}{RESET}")
                print(f"   Confidence: {result.intent.confidence:.2f}")
                
                # Update context (simulate execution)
                context["drone_state"] = step["expected_state"]
                for key, value in step["update"].items():
                    context[key] = value
                
                success_count += 1
            else:
                print(f"{RED}❌ Cannot execute: {reason}{RESET}")
        else:
            print(f"{RED}❌ Failed to parse: {result.error}{RESET}")
            if result.suggestions:
                print(f"{YELLOW}💡 Suggestions: {', '.join(result.suggestions[:2])}{RESET}")
        
        # Show current status
        print(f"   📊 State: {context['drone_state']}, Alt: {context['current_altitude']}m")
        print()
        
        await asyncio.sleep(0.5)  # Simulate execution time
    
    # Mission summary
    print(f"\n{BLUE}{'=' * 60}{RESET}")
    print(f"{BLUE}{'Mission Summary'.center(60)}{RESET}")
    print(f"{BLUE}{'=' * 60}{RESET}\n")
    
    print(f"Commands executed: {success_count}/{len(mission_steps)}")
    print(f"Final altitude: {context['current_altitude']}m")
    print(f"Final state: {context['drone_state']}")
    
    if success_count == len(mission_steps):
        print(f"\n{GREEN}🎉 Mission completed successfully!{RESET}")
    else:
        print(f"\n{YELLOW}⚠️  Mission completed with some issues{RESET}")


async def test_command_variations():
    """Test various command variations to show flexibility."""
    print(f"\n{BLUE}{'=' * 60}{RESET}")
    print(f"{BLUE}{'Command Variation Tests'.center(60)}{RESET}")
    print(f"{BLUE}{'=' * 60}{RESET}\n")
    
    service = NLPServiceFactory.create("spacy")
    
    # Test context
    context = {
        "drone_state": "HOVERING",
        "battery_percent": 85.0,
        "current_altitude": 25.0,
        "current_position": Position(47.3977, 8.5456, 25.0),
        "is_armed": True,
    }
    
    # Various ways to express the same commands
    test_variations = [
        # Takeoff variations
        ("take off to 50 meters", "Standard takeoff"),
        ("takeoff to 30m", "Abbreviated"),
        ("launch to 100 feet", "Different unit"),
        ("fly up to 40 meters", "Alternative phrasing"),
        
        # Movement variations
        ("move forward 10 meters", "Standard move"),
        ("go ahead 20m", "Alternative"),
        ("fly backward 15 meters", "Backward movement"),
        ("move left 5m and up 3m", "Multi-axis"),
        
        # Rotation variations
        ("rotate clockwise 90 degrees", "Standard rotation"),
        ("turn left 45 degrees", "Alternative"),
        ("spin counter-clockwise 180 degrees", "Alternative verb"),
        
        # Other commands
        ("return to home", "RTH variation"),
        ("come down and land", "Landing variation"),
        ("emergency stop", "Emergency"),
    ]
    
    for command, description in test_variations:
        result = await service.parse_command(command, context)
        
        if result.success:
            print(f"{GREEN}✅{RESET} {description}: \"{command}\"")
            print(f"   → {result.command.describe()}")
            print(f"   Confidence: {result.intent.confidence:.2f}")
        else:
            print(f"{RED}❌{RESET} {description}: \"{command}\"")
            print(f"   Error: {result.error}")
        print()


async def main():
    """Run all demos."""
    try:
        # Run realistic mission
        await run_realistic_demo()
        
        # Ask if user wants to see variations
        user_input = input("\nTest command variations? (y/n): ")
        if user_input.lower() == 'y':
            await test_command_variations()
        
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}👋 Demo interrupted by user{RESET}")
    except Exception as e:
        print(f"\n\n{RED}❌ Unexpected error: {e}{RESET}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())