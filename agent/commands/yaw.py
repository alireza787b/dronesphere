"""Yaw command implementation."""
import asyncio
import time

from shared.models import CommandResult

from .base import BaseCommand


class YawCommand(BaseCommand):
    """Rotate drone to specified heading."""

    def validate_params(self) -> None:
        """Validate yaw command parameters."""
        heading = self.params.get("heading")
        if heading is None or not isinstance(heading, (int, float)) or not (0 <= heading < 360):
            raise ValueError("heading must be a number between 0 and 360 degrees")
        speed = self.params.get("speed", 30.0)
        if not isinstance(speed, (int, float)) or speed <= 0 or speed > 180:
            raise ValueError("speed must be a positive number ≤ 180 deg/s")

    async def _check_flight_state(self, backend) -> None:
        """Check if drone is armed and airborne."""
        drone = backend.drone
        async for is_armed in drone.telemetry.armed():
            if not is_armed:
                raise RuntimeError("yaw command requires drone to be armed. Use takeoff first.")
            break
        async for position in drone.telemetry.position():
            if position.relative_altitude_m < 0.5:
                raise RuntimeError("yaw command requires drone to be airborne. Use takeoff first.")
            break

    async def execute(self, backend) -> CommandResult:
        """Execute yaw rotation using MAVSDK set_current_heading."""
        start_time = time.time()
        try:
            if not backend.connected:
                return CommandResult(
                    success=False,
                    message="Backend not connected to drone",
                    error="backend_disconnected",
                )
            self.validate_params()
            await self._check_flight_state(backend)
            drone = backend.drone
            heading = self.params["heading"]
            speed = self.params.get("speed", 30.0)
            print(f"🔧 Executing yaw to heading {heading}° at speed {speed}°/s")
            await drone.action.set_current_heading(heading)
            print("🚁 Yaw command sent, monitoring heading...")
            # Monitor heading until within tolerance
            timeout = 30.0
            check_interval = 0.5
            tolerance = 2.0
            elapsed = 0.0
            while elapsed < timeout:
                async for attitude in drone.telemetry.attitude_euler():
                    current_heading = attitude.yaw_deg % 360
                    diff = abs((current_heading - heading + 180) % 360 - 180)
                    if diff <= tolerance:
                        duration = time.time() - start_time
                        return CommandResult(
                            success=True,
                            message=f"Yaw to {heading}° completed (actual: {current_heading:.1f}°)",
                            duration=duration,
                        )
                    if elapsed % 5.0 < check_interval:
                        print(f"   📊 Current heading: {current_heading:.1f}°, Δ={diff:.1f}°")
                    break
                await asyncio.sleep(check_interval)
                elapsed += check_interval
            duration = time.time() - start_time
            return CommandResult(
                success=False,
                message=f"Yaw to {heading}° timed out after {timeout}s",
                error="timeout",
                duration=duration,
            )
        except Exception as e:
            duration = time.time() - start_time
            return CommandResult(
                success=False, message=f"yaw failed: {str(e)}", error=str(e), duration=duration
            )
