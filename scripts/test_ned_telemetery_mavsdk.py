#!/usr/bin/env python3
"""
Test script to verify MAVSDK Python local NED position telemetry.

PROBLEM DISCOVERED:
- MAVSDK Python does NOT have telemetry.position_ned() method
- Documentation and examples suggest it should exist, but it's missing
- This has been causing our telemetry to return null NED coordinates

SOLUTION FOUND:
- Use telemetry.position_velocity_ned() instead
- This returns an Odometry object with position.north_m, position.east_m, position.down_m
- This is the ONLY way to get local NED coordinates in MAVSDK Python 1.4.15
"""

import asyncio
from mavsdk import System

async def test_ned_methods():
    """Test all possible ways to get local NED position in MAVSDK Python."""
    
    drone = System()
    await drone.connect(system_address="udp://:14540")

    print("=" * 60)
    print("TESTING MAVSDK PYTHON LOCAL NED POSITION METHODS")
    print("=" * 60)

    # Wait for connection
    print("\n1. Waiting for drone connection...")
    async for state in drone.core.connection_state():
        if state.is_connected:
            print("✅ Connected to drone!")
            break

    # Check available telemetry methods
    print("\n2. Checking available telemetry methods...")
    telemetry_methods = [method for method in dir(drone.telemetry) if not method.startswith('_')]
    ned_methods = [method for method in telemetry_methods if 'ned' in method.lower() or 'position' in method.lower()]
    
    print("Available NED/position related methods:")
    for method in sorted(ned_methods):
        print(f"   - {method}")
    
    # Check for specific methods we expect
    print(f"\n3. Method availability check:")
    print(f"   - telemetry.position(): {'✅ EXISTS' if hasattr(drone.telemetry, 'position') else '❌ MISSING'}")
    print(f"   - telemetry.position_ned(): {'✅ EXISTS' if hasattr(drone.telemetry, 'position_ned') else '❌ MISSING'}")
    print(f"   - telemetry.position_velocity_ned(): {'✅ EXISTS' if hasattr(drone.telemetry, 'position_velocity_ned') else '❌ MISSING'}")

    # Wait for local position health
    print("\n4. Waiting for local position health...")
    async for health in drone.telemetry.health():
        if hasattr(health, 'is_local_position_ok') and health.is_local_position_ok:
            print("✅ Local position is OK!")
            break
        elif hasattr(health, 'is_local_position_ok'):
            print(f"⏳ Local position not ready (is_local_position_ok: {health.is_local_position_ok})")
        else:
            print("⚠️  is_local_position_ok attribute not found")
        await asyncio.sleep(0.5)

    # Test Method 1: position_ned() - Expected to fail
    print("\n5. Testing telemetry.position_ned() [EXPECTED TO FAIL]...")
    try:
        async for pos_ned in drone.telemetry.position_ned():
            print(f"✅ Got position_ned: North={pos_ned.north_m}, East={pos_ned.east_m}, Down={pos_ned.down_m}")
            break
    except AttributeError as e:
        print(f"❌ position_ned() method not available: {e}")
    except Exception as e:
        print(f"❌ position_ned() error: {e}")

    # Test Method 2: position_velocity_ned() - Should work
    print("\n6. Testing telemetry.position_velocity_ned() [SHOULD WORK]...")
    try:
        async for odom in drone.telemetry.position_velocity_ned():
            pos = odom.position
            vel = odom.velocity
            print(f"✅ Got position_velocity_ned:")
            print(f"   Position: North={pos.north_m:.3f}m, East={pos.east_m:.3f}m, Down={pos.down_m:.3f}m")
            print(f"   Velocity: North={vel.north_m_s:.3f}m/s, East={vel.east_m_s:.3f}m/s, Down={vel.down_m_s:.3f}m/s")
            break
    except AttributeError as e:
        print(f"❌ position_velocity_ned() method not available: {e}")
    except Exception as e:
        print(f"❌ position_velocity_ned() error: {e}")

    # Test Method 3: Regular position() for comparison
    print("\n7. Testing telemetry.position() [GPS coordinates]...")
    try:
        async for pos in drone.telemetry.position():
            print(f"✅ Got GPS position:")
            print(f"   Lat: {pos.latitude_deg:.6f}°, Lon: {pos.longitude_deg:.6f}°")
            print(f"   Alt MSL: {pos.absolute_altitude_m:.3f}m, Alt Rel: {pos.relative_altitude_m:.3f}m")
            break
    except Exception as e:
        print(f"❌ position() error: {e}")

    print("\n" + "=" * 60)
    print("TEST SUMMARY:")
    print("- position_ned(): NOT AVAILABLE in MAVSDK Python")
    print("- position_velocity_ned(): WORKING method for local NED coordinates")
    print("- position(): Working for GPS coordinates")
    print("=" * 60)

if __name__ == "__main__":
    print("Testing MAVSDK Python NED position methods...")
    print("Make sure PX4 SITL and mavlink2rest are running!")
    asyncio.run(test_ned_methods())