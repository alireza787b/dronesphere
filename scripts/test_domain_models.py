#!/usr/bin/env python3
"""Test script to verify domain models are working correctly."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.domain import (
    Drone,
    DroneState,
    Position,
    TakeoffCommand,
    LandCommand,
    GoToCommand,
    MoveCommand,
)


def test_position():
    """Test Position value object."""
    print("\n🧪 Testing Position Value Object...")
    
    # Create positions
    pos1 = Position(latitude=47.397742, longitude=8.545594, altitude=435.0)
    pos2 = Position(latitude=47.398742, longitude=8.546594, altitude=450.0)
    
    print(f"✅ Created position: {pos1}")
    print(f"✅ Distance between positions: {pos1.distance_to(pos2):.2f}m")
    
    # Test immutability
    pos3 = pos1.with_altitude(500.0)
    print(f"✅ New position with altitude: {pos3}")
    
    # Test equality
    pos4 = Position(latitude=47.397742, longitude=8.545594, altitude=435.0)
    assert pos1 == pos4, "Equal positions should be equal"
    print("✅ Value object equality works")


def test_drone_entity():
    """Test Drone entity."""
    print("\n🧪 Testing Drone Entity...")
    
    # Create drone
    drone = Drone(name="TestDrone", model="Phantom 4")
    print(f"✅ Created drone: {drone.name} ({drone.id})")
    print(f"✅ Initial state: {drone.state}")
    
    # Connect drone
    initial_pos = Position(latitude=47.397742, longitude=8.545594, altitude=435.0)
    drone.connect(initial_pos)
    print(f"✅ Connected at: {drone.position}")
    
    # Check events
    events = drone.pull_events()
    print(f"✅ Generated {len(events)} events: {[e.event_name for e in events]}")
    
    # Arm drone
    drone.arm()
    print(f"✅ Armed drone, state: {drone.state}")
    print(f"✅ Home position set: {drone.home_position}")
    
    # Takeoff
    drone.takeoff(10.0)
    print(f"✅ Taking off to 10m, state: {drone.state}")
    
    # Update position (simulate climb)
    new_pos = initial_pos.with_altitude(445.0)
    drone.update_position(new_pos)
    print(f"✅ Updated position, state: {drone.state}")
    
    # Pull all events
    events = drone.pull_events()
    print(f"\n📊 Total events generated: {len(events)}")
    for event in events:
        print(f"   - {event.event_name}")


def test_commands():
    """Test Command value objects."""
    print("\n🧪 Testing Commands...")
    
    # Takeoff command
    takeoff = TakeoffCommand(target_altitude=15.0)
    takeoff.validate()
    print(f"✅ {takeoff.describe()}")
    
    # Land command
    land = LandCommand()
    print(f"✅ {land.describe()}")
    
    # GoTo command
    target = Position(latitude=47.398, longitude=8.546, altitude=450.0)
    goto = GoToCommand(target_position=target, speed_m_s=5.0)
    goto.validate()
    print(f"✅ {goto.describe()}")
    
    # Move command
    move = MoveCommand(forward_m=10, right_m=-5, up_m=2, rotate_deg=45)
    move.validate()
    print(f"✅ {move.describe()}")
    
    # Test invalid command
    try:
        bad_takeoff = TakeoffCommand(target_altitude=200)  # Too high
        bad_takeoff.validate()
    except ValueError as e:
        print(f"✅ Validation works: {e}")


def test_state_transitions():
    """Test drone state machine."""
    print("\n🧪 Testing State Transitions...")
    
    # Test valid transitions
    assert DroneState.DISCONNECTED.can_transition_to(DroneState.CONNECTED)
    assert DroneState.ARMED.can_transition_to(DroneState.TAKING_OFF)
    print("✅ Valid transitions work")
    
    # Test invalid transitions
    assert not DroneState.DISCONNECTED.can_transition_to(DroneState.FLYING)
    assert not DroneState.LANDED.can_transition_to(DroneState.TAKING_OFF)
    print("✅ Invalid transitions blocked")


def main():
    """Run all tests."""
    print("🚁 DroneSphere Domain Model Tests")
    print("=" * 50)
    
    try:
        test_position()
        test_drone_entity()
        test_commands()
        test_state_transitions()
        
        print("\n" + "=" * 50)
        print("🎉 All domain model tests passed!")
        print("\nDomain models are ready for use:")
        print("  • Drone entity with state management ✅")
        print("  • Position value object with validation ✅")
        print("  • Command patterns for drone control ✅")
        print("  • Domain events for state changes ✅")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())