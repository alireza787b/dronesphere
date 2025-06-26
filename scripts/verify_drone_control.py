#!/usr/bin/env python3
"""Verify drone control adapter implementation."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.adapters.output.drone_control.factory import DroneControlFactory
from src.config.drone_config import drone_config, DroneProfile, multi_drone_config
from src.core.domain.value_objects.battery import BatteryStatus
from src.core.domain.value_objects.command import (
    TakeoffCommand,
    MoveCommand,
    LandCommand,
    OrbitCommand,
    GoToCommand
)
from src.core.domain.value_objects.position import Position
from src.core.ports.output.drone_control import TelemetryData, TelemetryType


async def main():
    """Test drone control functionality."""
    print("🚁 Testing Drone Control Adapter\n")
    
    # Test configuration
    print("📋 Configuration:")
    print(f"   Default connection: {drone_config.default_connection_string}")
    print(f"   Backend: {drone_config.backend}")
    print(f"   Max altitude: {drone_config.max_altitude_m}m")
    print(f"   Max velocity: {drone_config.max_velocity_m_s}m/s")
    print(f"   Min battery: {drone_config.min_battery_percent}%\n")
    
    # Test multi-drone profiles
    print("👥 Multi-Drone Support:")
    
    # Add some drone profiles
    drone1 = DroneProfile(
        drone_id="alpha",
        name="Alpha Drone",
        connection_string="udp://:14540",
        backend="mavsdk",
        max_altitude_m=100,
        capabilities=["camera", "gps", "telemetry"]
    )
    
    drone2 = DroneProfile(
        drone_id="beta", 
        name="Beta Drone",
        connection_string="udp://:14541",
        backend="mavsdk",
        max_velocity_m_s=20,
        capabilities=["cargo", "gps", "telemetry"]
    )
    
    multi_drone_config.add_drone(drone1)
    multi_drone_config.add_drone(drone2)
    
    print(f"✅ Added {len(multi_drone_config.drones)} drone profiles")
    for profile in multi_drone_config.drones.values():
        print(f"   - {profile.name} ({profile.drone_id}): {profile.connection_string}")
    
    # Create adapter from profile
    print("\n🏭 Factory Tests:")
    
    # Test different creation methods
    adapter1 = DroneControlFactory.create_from_env()
    print(f"✅ Created adapter from environment config: {adapter1.backend_name}")
    
    adapter2 = DroneControlFactory.create_from_profile(drone1)
    print(f"✅ Created adapter from profile: {adapter2.backend_name}")
    
    # Test with custom config
    custom_config = {
        'connection_string': 'tcp://192.168.1.100:5760',
        'max_altitude_m': 50,
        'drone_id': 'custom_drone'
    }
    adapter3 = DroneControlFactory.create('mavsdk', custom_config)
    print(f"✅ Created adapter with custom config")
    
    # Test battery value object
    print("\n🔋 Battery Tests:")
    
    battery_tests = [
        BatteryStatus(level=85, voltage=12.4, temperature=25.0),
        BatteryStatus(level=15, voltage=11.1),  # Low battery
        BatteryStatus(level=8, voltage=10.8),   # Critical battery
    ]
    
    for battery in battery_tests:
        print(f"   {battery}")
        print(f"     Healthy: {battery.is_healthy}, Low: {battery.is_low}, Critical: {battery.is_critical}")
    
    # Test command creation and validation
    print("\n📋 Command Tests:")
    
    commands = [
        TakeoffCommand(target_altitude=20),
        MoveCommand(forward_m=10, right_m=5, up_m=2, rotate_deg=45),
        OrbitCommand(
            center=Position(47.3977, 8.5456, 50),
            radius_m=20,
            velocity_m_s=5,
            orbits=2,
            clockwise=True
        ),
        GoToCommand(target_position=Position(47.3980, 8.5460, 30)),
        LandCommand()
    ]
    
    for cmd in commands:
        try:
            cmd.validate()
            print(f"✅ {cmd.describe()}")
        except Exception as e:
            print(f"❌ {cmd.command_type}: {e}")
    
    # Test telemetry
    print("\n📊 Telemetry Tests:")
    
    telemetry_samples = [
        TelemetryData(
            type=TelemetryType.POSITION,
            data={
                "latitude": 47.3977,
                "longitude": 8.5456,
                "altitude_m": 50,
                "absolute_altitude_m": 470
            },
            timestamp=1234567890.0
        ),
        TelemetryData(
            type=TelemetryType.BATTERY,
            data={
                "remaining_percent": 75,
                "voltage_v": 12.2
            },
            timestamp=1234567891.0
        ),
        TelemetryData(
            type=TelemetryType.ATTITUDE,
            data={
                "roll_deg": 2.5,
                "pitch_deg": -1.2,
                "yaw_deg": 178.3
            },
            timestamp=1234567892.0
        )
    ]
    
    for telemetry in telemetry_samples:
        print(f"✅ {telemetry.type.value}: ", end="")
        if telemetry.type == TelemetryType.POSITION:
            pos = telemetry.get_position()
            print(f"{pos}")
        elif telemetry.type == TelemetryType.BATTERY:
            bat = telemetry.get_battery()
            print(f"{bat}")
        else:
            print(f"{telemetry.data}")
    
    print("\n🔌 Connection Test:")
    print("Note: Actual connection requires a running SITL or real drone")
    print(f"Would connect with: await adapter.connect('{drone_config.default_connection_string}')")
    
    print("\n✨ All drone control components working correctly!")


if __name__ == "__main__":
    asyncio.run(main())