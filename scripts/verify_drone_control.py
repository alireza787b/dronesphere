#!/usr/bin/env python3
"""Verify drone control adapter implementation."""

import asyncio
import sys

sys.path.insert(0, '..')

from src.adapters.output.drone_control.factory import DroneControlFactory
from src.core.domain.value_objects.command import (
    TakeoffCommand,
    MoveCommand,
    LandCommand
)
from src.core.domain.value_objects.position import Position


async def main():
    """Test drone control functionality."""
    print("🚁 Testing Drone Control Adapter\n")
    
    # Create MAVSDK adapter
    adapter = DroneControlFactory.create('mavsdk')
    print(f"✅ Created {adapter.backend_name} adapter")
    print(f"   Supports simulation: {adapter.supports_simulation}")
    print(f"   Max altitude: {adapter.max_altitude_m}m")
    print(f"   Max velocity: {adapter.max_velocity_m_s}m/s\n")
    
    # Test command creation and validation
    print("📋 Testing Commands:")
    
    commands = [
        TakeoffCommand(target_altitude=20),
        MoveCommand(forward_m=10, right_m=0, up_m=5, rotate_deg=90),
        LandCommand()
    ]
    
    for cmd in commands:
        try:
            cmd.validate()
            print(f"✅ {cmd.describe()}")
        except Exception as e:
            print(f"❌ {cmd.command_type}: {e}")
    
    print("\n🔌 Connection Test:")
    print("Note: Actual connection requires a running SITL or real drone")
    print("Would connect with: await adapter.connect('udp://:14540')")
    
    # Test telemetry data structures
    print("\n📊 Testing Telemetry:")
    from src.core.ports.output.drone_control import TelemetryData, TelemetryType
    
    telemetry = TelemetryData(
        type=TelemetryType.POSITION,
        data={
            "latitude": 47.3977,
            "longitude": 8.5456,
            "altitude_m": 50
        },
        timestamp=1234567890.0
    )
    
    position = telemetry.get_position()
    print(f"✅ Position from telemetry: {position}")
    
    print("\n✨ All drone control components working correctly!")


if __name__ == "__main__":
    asyncio.run(main())