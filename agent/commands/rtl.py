"""Return to Launch (RTL) command implementation.

Path: agent/commands/rtl.py
"""
import asyncio
import time

from shared.models import CommandResult

from .base import BaseCommand


class RTLCommand(BaseCommand):
    """Return to launch position and land."""

    def validate_params(self) -> None:
        """RTL command has no parameters to validate."""
        pass

    async def execute(self, backend) -> CommandResult:
        """Execute RTL using MAVSDK backend."""
        start_time = time.time()

        try:
            if not backend.connected:
                return CommandResult(
                    success=False,
                    message="Backend not connected to drone",
                    error="backend_disconnected",
                )

            print("🏠 Executing Return to Launch...")

            # Get MAVSDK drone instance
            drone = backend.drone

            # Execute RTL
            await drone.action.return_to_launch()

            # Wait for RTL completion
            await asyncio.sleep(15)  # Give time for RTL

            duration = time.time() - start_time

            print(f"✅ RTL completed in {duration:.1f}s")
            return CommandResult(
                success=True, message="Return to launch completed successfully", duration=duration
            )

        except Exception as e:
            duration = time.time() - start_time
            error_msg = str(e)
            print(f"❌ RTL failed: {error_msg}")

            return CommandResult(
                success=False,
                message=f"RTL failed: {error_msg}",
                error=error_msg,
                duration=duration,
            )
