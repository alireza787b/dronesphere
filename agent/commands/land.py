"""land command implementation with robustness checks.

Path: agent/commands/land.py
ROBUSTNESS: Only operates when drone is airborne.
"""
import asyncio
import time

from shared.models import CommandResult

from .base import BaseCommand


class LandCommand(BaseCommand):
    """Land the drone at current location.

    No parameters required.

    Robustness: Only works when drone is airborne (relative altitude > 0.5m).
    If already on ground, returns informational message without action.
    """

    def validate_params(self) -> None:
        """Validate land parameters (none required)."""
        # Land command takes no parameters
        pass

    async def _check_airborne_state(self, backend) -> bool:
        """Check if drone is airborne.

        Returns:
            bool: True if airborne (relative altitude > 0.5m), False if on ground
        """
        drone = backend.drone

        async for position in drone.telemetry.position():
            relative_alt = position.relative_altitude_m
            is_airborne = relative_alt > 0.5

            print(f"📊 Current relative altitude: {relative_alt:.2f}m")
            return is_airborne

    async def execute(self, backend) -> CommandResult:
        """Execute land using MAVSDK backend."""
        start_time = time.time()

        try:
            if not backend.connected:
                return CommandResult(
                    success=False,
                    message="Backend not connected to drone",
                    error="backend_disconnected",
                )

            # Check if airborne
            is_airborne = await self._check_airborne_state(backend)

            if not is_airborne:
                # Already on ground - return success without action
                duration = time.time() - start_time
                return CommandResult(
                    success=True,
                    message=f"Drone already on ground - landing not needed",
                    duration=duration,
                )

            print("🛬 Executing landing...")

            # Get MAVSDK drone instance
            drone = backend.drone

            # Execute landing
            await drone.action.land()

            # Wait for landing completion
            await asyncio.sleep(10)

            duration = time.time() - start_time

            print(f"✅ Landing completed in {duration:.1f}s")
            return CommandResult(
                success=True, message="Landing completed successfully", duration=duration
            )

        except Exception as e:
            duration = time.time() - start_time
            return CommandResult(
                success=False, message=f"Landing failed: {str(e)}", error=str(e), duration=duration
            )
