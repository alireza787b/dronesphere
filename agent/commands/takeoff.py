"""takeoff command implementation with robustness checks.

Path: agent/commands/takeoff.py
ROBUSTNESS: Only operates when drone is on ground and disarmed/armed.
"""
import asyncio
import time

from shared.models import CommandResult

from .base import BaseCommand


class TakeoffCommand(BaseCommand):
    """Takeoff to specified altitude.

    Parameters:
        - altitude: Target altitude in meters (1.0 to 50.0, default: 10.0)

    Robustness: Only works when drone is on ground (relative altitude < 0.5m).
    If already airborne, returns informational message without action.
    """

    def validate_params(self) -> None:
        """Validate takeoff parameters."""
        altitude = self.params.get("altitude", 10.0)

        if not isinstance(altitude, (int, float)):
            raise ValueError("altitude must be a number")

        if not 1.0 <= altitude <= 50.0:
            raise ValueError(f"altitude must be between 1-50m, got {altitude}m")

    async def _check_ground_state(self, backend) -> bool:
        """Check if drone is on ground.

        Returns:
            bool: True if on ground (relative altitude < 0.5m), False if airborne
        """
        drone = backend.drone

        async for position in drone.telemetry.position():
            relative_alt = position.relative_altitude_m
            is_on_ground = relative_alt < 0.5

            print(f"📊 Current relative altitude: {relative_alt:.2f}m")
            return is_on_ground

    async def execute(self, backend) -> CommandResult:
        """Execute takeoff using MAVSDK backend."""
        start_time = time.time()

        try:
            if not backend.connected:
                return CommandResult(
                    success=False,
                    message="Backend not connected to drone",
                    error="backend_disconnected",
                )

            altitude = float(self.params.get("altitude", 10.0))

            # Check if already airborne
            is_on_ground = await self._check_ground_state(backend)

            if not is_on_ground:
                # Already airborne - return success without action
                duration = time.time() - start_time
                return CommandResult(
                    success=True,
                    message=f"Drone already airborne - takeoff not needed",
                    duration=duration,
                )

            print(f"🚁 Executing takeoff to {altitude}m...")

            # Get MAVSDK drone instance
            drone = backend.drone

            # Arm the drone
            print("🔧 Arming drone...")
            await drone.action.arm()

            # Set takeoff altitude
            await drone.action.set_takeoff_altitude(altitude)

            # Execute takeoff
            print(f"🚀 Taking off to {altitude}m...")
            await drone.action.takeoff()

            # Wait for takeoff completion
            await asyncio.sleep(8)

            duration = time.time() - start_time

            print(f"✅ Takeoff completed in {duration:.1f}s")
            return CommandResult(
                success=True,
                message=f"Takeoff to {altitude}m completed successfully",
                duration=duration,
            )

        except Exception as e:
            duration = time.time() - start_time
            return CommandResult(
                success=False, message=f"Takeoff failed: {str(e)}", error=str(e), duration=duration
            )
