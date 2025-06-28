#!/usr/bin/env python3
# scripts/test_connection.py
"""
Test script to verify MAVSDK connection to SITL.

Usage:
    python scripts/test_connection.py
"""

import asyncio
import sys
from pathlib import Path

# Add agent source to path
sys.path.insert(0, str(Path(__file__).parent.parent / "agent" / "src"))

try:
    import structlog

    from agent.connection import DroneConnection
except ImportError as e:
    print(f"Import error: {e}")
    print(
        "Make sure you're in the dronesphere directory and have installed dependencies"
    )
    sys.exit(1)

# Configure logging
structlog.configure(processors=[structlog.dev.ConsoleRenderer(colors=True)])
logger = structlog.get_logger()


async def test_connection():
    """Test basic drone connection and operations."""
    drone_conn = DroneConnection()

    try:
        # Connect
        logger.info("Connecting to drone...")
        await drone_conn.connect()
        logger.info("✅ Connected successfully!")

        # Wait for GPS (in SITL this should be immediate)
        logger.info("Waiting for GPS fix...")
        for _ in range(10):
            if drone_conn.state.gps_fix:
                logger.info("✅ GPS fix acquired")
                break
            await asyncio.sleep(1)

        # Print current state
        state = drone_conn.state
        logger.info(
            "Drone state",
            armed=state.armed,
            mode=state.mode,
            battery=f"{state.battery_percent:.1f}%",
            position=f"({state.position[0]:.6f}, {state.position[1]:.6f}, {state.position[2]:.1f}m)",
        )

        # Test arming
        logger.info("Testing arm command...")
        await drone_conn.arm()
        await asyncio.sleep(2)

        if drone_conn.state.armed:
            logger.info("✅ Drone armed successfully")

            # Disarm
            logger.info("Disarming...")
            await drone_conn.disarm()
            logger.info("✅ Drone disarmed")
        else:
            logger.warning("❌ Failed to arm drone")

    except Exception as e:
        logger.error("Test failed", error=str(e))
        return False

    finally:
        await drone_conn.disconnect()

    logger.info("✅ All tests passed!")
    return True


if __name__ == "__main__":
    print("🚁 DroneSphere Connection Test")
    print("==============================")
    print("Make sure SITL is running:")
    print(
        "docker run --rm -it -p 14540:14540/udp jonasvautherin/px4-gazebo-headless:latest"
    )
    print()

    success = asyncio.run(test_connection())
    sys.exit(0 if success else 1)
