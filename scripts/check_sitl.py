# scripts/check_sitl.py
import asyncio
import sys

from mavsdk import System


async def check_sitl():
    drone = System()
    print("Attempting to connect to SITL...")
    try:
        # Use a timeout for the connection attempt
        # Mavsdk's connect can implicitly wait for heartbeats to confirm connection
        # Setting a reasonable timeout is crucial.
        await asyncio.wait_for(
            drone.connect(system_address="udp://:14540"), timeout=15.0
        )  # Increased timeout slightly

        print("SITL connected and receiving heartbeats!")
        sys.exit(0)  # Success

    except asyncio.TimeoutError:
        print("Timeout: Could not connect to SITL within the specified time.")
        sys.exit(1)  # Failure
    except Exception as e:
        print(f"Error connecting to SITL: {e}")
        sys.exit(1)  # Failure


if __name__ == "__main__":
    asyncio.run(check_sitl())
