#!/usr/bin/env python3
# scripts/test_simple.py
"""
Simple test script to verify MAVSDK installation and connection.

Usage:
    python scripts/test_simple.py
"""

import asyncio

from mavsdk import System


async def test_connection():
    """Test basic drone connection."""
    # Create drone instance
    drone = System()

    print("🚁 Connecting to drone at udp://:14540...")

    try:
        # Connect to drone
        await drone.connect(system_address="udp://:14540")

        # Check if connected
        print("⏳ Waiting for connection...")
        async for state in drone.core.connection_state():
            if state.is_connected:
                print("✅ Connected to drone!")
                break

        # Get some info
        info = await drone.info.get_identification()
        print(f"📡 System ID: {info.hardware_uid}")

        # Check GPS
        print("🛰️  Checking GPS...")
        async for gps_info in drone.telemetry.gps_info():
            print(f"   Satellites: {gps_info.num_satellites}")
            print(f"   Fix type: {gps_info.fix_type}")
            break

        # Check battery
        print("🔋 Checking battery...")
        async for battery in drone.telemetry.battery():
            print(f"   Battery: {battery.remaining_percent * 100:.1f}%")
            print(f"   Voltage: {battery.voltage_v:.2f}V")
            break

        # Check position
        print("📍 Checking position...")
        async for position in drone.telemetry.position():
            print(f"   Lat: {position.latitude_deg:.6f}")
            print(f"   Lon: {position.longitude_deg:.6f}")
            print(f"   Alt: {position.relative_altitude_m:.1f}m")
            break

        print("\n✅ All checks passed!")
        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("DroneSphere Simple Connection Test")
    print("=" * 50)
    print("\nMake sure SITL is running:")
    print(
        "docker run --rm -it -p 14540:14540/udp jonasvautherin/px4-gazebo-headless:latest"
    )
    print("\n" + "=" * 50 + "\n")

    # Note about protobuf warnings
    print("Note: You may see protobuf warnings - these can be safely ignored\n")

    success = asyncio.run(test_connection())
    exit(0 if success else 1)
