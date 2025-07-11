"""Professional orbit command with flexible coordinate systems and smart defaults.

This module provides a comprehensive orbit/circular flight command with support for:
- Multiple coordinate systems (local NED, global GPS, auto-detection)
- Flexible duration control (time-based, loop-based, continuous)
- All MAVSDK yaw behaviors with user-friendly names
- Smart defaults for beginners with advanced options for experts
- Automatic coordinate conversion using pymap3d or fallback methods

Usage Examples:
1. Beginner: orbit() → 10m radius at current position, 30s duration
2. Basic: orbit(radius=15, velocity=3) → custom radius and speed
3. Advanced: orbit(center_lat=-35.36, center_lon=149.16, radius=20, loops=2)
"""

import asyncio
import math
from typing import Optional, Tuple

from dronesphere.backends.base import AbstractBackend
from dronesphere.backends.orbit_extension import get_orbit_yaw_behavior
from dronesphere.commands.base import BaseCommand
from dronesphere.core.logging import get_logger
from dronesphere.core.models import CommandResult, DroneState

logger = get_logger(__name__)


class OrbitCommand(BaseCommand):
    """Command to execute circular orbit flight patterns with flexible configuration.

    This command supports multiple usage levels:
    1. Zero-config: orbit() uses smart defaults (10m radius, current position, 30s)
    2. Basic: orbit(radius=15, velocity=3) for simple customization
    3. Advanced: Full coordinate and behavior control

    Coordinate Systems:
    - LOCAL NED: center_north/center_east relative to takeoff origin
    - GLOBAL GPS: center_lat/center_lon absolute positioning
    - AUTO-DETECT: Automatically chooses system based on provided parameters
    """

    async def run(self, backend: AbstractBackend, **params) -> CommandResult:
        """Execute orbit command with comprehensive coordinate and duration control.

        Args:
            backend: MAVSDK backend for drone control
            **params: Command parameters with smart defaults

        Returns:
            CommandResult with detailed execution information
        """
        # Extract core orbit parameters with smart defaults
        radius = params.get("radius", 10.0)  # 10m default radius
        velocity = params.get("velocity", 2.0)  # 2m/s default velocity (clockwise)
        yaw_behavior_str = params.get("yaw_behavior", "face_center")
        timeout = params.get("timeout", 120.0)

        # Extract coordinate parameters
        center_north = params.get("center_north")
        center_east = params.get("center_east")
        altitude_relative = params.get("altitude_relative")
        center_lat = params.get("center_lat")
        center_lon = params.get("center_lon")
        altitude_msl = params.get("altitude_msl")
        coordinate_mode = params.get("coordinate_mode", "auto")

        # Extract duration control parameters
        duration = params.get("duration", 30.0 if not params.get("loops") and not params.get("continuous") else None)
        loops = params.get("loops")
        continuous = params.get("continuous", False)

        logger.info(
            "orbit_command_started",
            command_id=id(self),
            radius=radius,
            velocity=velocity,
            yaw_behavior=yaw_behavior_str,
            coordinate_mode=coordinate_mode,
            duration=duration,
            loops=loops,
            continuous=continuous,
            drone_id=backend.drone_id,
        )

        try:
            # Pre-flight safety checks
            initial_state = await backend.get_state()
            if initial_state not in [DroneState.FLYING, DroneState.TAKEOFF]:
                return CommandResult(
                    success=False,
                    message="Cannot orbit: drone not flying",
                    error="Drone must be flying to execute orbit command",
                )

            if initial_state == DroneState.DISCONNECTED:
                return CommandResult(
                    success=False,
                    message="Cannot orbit: drone disconnected",
                    error="Drone not connected",
                )

            # Validate orbit parameters
            validation_result = self._validate_orbit_parameters(
                radius, velocity, yaw_behavior_str, duration, loops, continuous
            )
            if not validation_result.success:
                return validation_result

            # Convert yaw behavior string to MAVSDK enum
            try:
                yaw_behavior = get_orbit_yaw_behavior(yaw_behavior_str)
            except ValueError as e:
                return CommandResult(
                    success=False,
                    message=f"Invalid yaw behavior: {yaw_behavior_str}",
                    error=str(e),
                )

            # Determine coordinate system and get orbit center
            coord_result = await self._determine_orbit_coordinates(
                backend,
                coordinate_mode,
                center_north, center_east, altitude_relative,
                center_lat, center_lon, altitude_msl
            )
            if not coord_result.success:
                return coord_result

            orbit_center = coord_result.data
            actual_coordinate_mode = orbit_center["coordinate_mode"]

            logger.info(
                "orbit_coordinates_determined",
                command_id=id(self),
                coordinate_mode=actual_coordinate_mode,
                orbit_center=orbit_center,
                drone_id=backend.drone_id,
            )

            # Calculate expected orbit duration for monitoring
            expected_duration = self._calculate_expected_duration(radius, velocity, duration, loops)

            start_time = asyncio.get_event_loop().time()

            # Execute orbit command based on coordinate system
            if actual_coordinate_mode == "global":
                await backend.orbit_at_global_position(
                    center_lat=orbit_center["lat"],
                    center_lon=orbit_center["lon"],
                    altitude_msl=orbit_center["alt_msl"],
                    radius=radius,
                    velocity=velocity,
                    yaw_behavior=yaw_behavior
                )
            else:  # local
                await backend.orbit_at_local_position(
                    center_north=orbit_center["north"],
                    center_east=orbit_center["east"],
                    altitude_relative=orbit_center["alt_relative"],
                    radius=radius,
                    velocity=velocity,
                    yaw_behavior=yaw_behavior
                )

            await self.check_cancelled()

            # Monitor orbit execution based on duration control
            completion_result = await self._monitor_orbit_execution(
                backend, duration, loops, continuous, expected_duration, timeout, radius, velocity
            )

            actual_duration = asyncio.get_event_loop().time() - start_time

            if completion_result.success:
                logger.info(
                    "orbit_command_completed",
                    command_id=id(self),
                    coordinate_mode=actual_coordinate_mode,
                    completion_reason=completion_result.data["completion_reason"],
                    actual_duration=actual_duration,
                    expected_duration=expected_duration,
                    drone_id=backend.drone_id,
                )

                return CommandResult(
                    success=True,
                    message=f"Orbit completed successfully ({completion_result.data['completion_reason']})",
                    duration=actual_duration,
                    data={
                        "coordinate_mode": actual_coordinate_mode,
                        "orbit_center": orbit_center,
                        "radius": radius,
                        "velocity": velocity,
                        "yaw_behavior": yaw_behavior_str,
                        "completion_reason": completion_result.data["completion_reason"],
                        "expected_duration": expected_duration,
                        "loops_completed": completion_result.data.get("loops_completed", 0),
                    },
                )
            else:
                return CommandResult(
                    success=False,
                    message=completion_result.message,
                    error=completion_result.error,
                    duration=actual_duration,
                    data={
                        "coordinate_mode": actual_coordinate_mode,
                        "orbit_center": orbit_center,
                        "radius": radius,
                        "velocity": velocity,
                        "expected_duration": expected_duration,
                    },
                )

        except asyncio.CancelledError:
            logger.info(
                "orbit_command_cancelled",
                command_id=id(self),
                drone_id=backend.drone_id,
            )
            return CommandResult(
                success=False,
                message="Orbit command was cancelled",
                error="Cancelled",
            )

        except Exception as e:
            logger.error(
                "orbit_command_failed",
                command_id=id(self),
                error=str(e),
                drone_id=backend.drone_id,
            )
            return CommandResult(
                success=False,
                message=f"Orbit failed: {str(e)}",
                error=str(e),
            )

    async def cancel(self) -> None:
        """Cancel orbit command."""
        await super().cancel()

    def _validate_orbit_parameters(
        self,
        radius: float,
        velocity: float,
        yaw_behavior: str,
        duration: Optional[float],
        loops: Optional[float],
        continuous: bool
    ) -> CommandResult:
        """Validate orbit parameters for safety and consistency."""
        
        # Validate radius
        if radius <= 0:
            return CommandResult(
                success=False,
                message="Orbit radius must be positive",
                error=f"Invalid radius: {radius}",
            )
        if radius > 500:
            return CommandResult(
                success=False,
                message="Orbit radius too large (max 500m)",
                error=f"Radius {radius}m exceeds safety limit",
            )

        # Validate velocity
        if abs(velocity) < 0.1:
            return CommandResult(
                success=False,
                message="Orbit velocity too slow (min 0.1 m/s)",
                error=f"Invalid velocity: {velocity}",
            )
        if abs(velocity) > 15:
            return CommandResult(
                success=False,
                message="Orbit velocity too fast (max 15 m/s)",
                error=f"Velocity {velocity}m/s exceeds safety limit",
            )

        # Validate duration control (only one should be specified)
        duration_controls = sum([
            1 if duration is not None else 0,
            1 if loops is not None else 0,
            1 if continuous else 0
        ])
        
        if duration_controls > 1:
            return CommandResult(
                success=False,
                message="Only one duration control method allowed",
                error="Specify either duration, loops, or continuous - not multiple",
            )

        # Validate specific duration values
        if duration is not None and (duration < 5 or duration > 600):
            return CommandResult(
                success=False,
                message="Duration must be between 5-600 seconds",
                error=f"Invalid duration: {duration}s",
            )

        if loops is not None and (loops < 0.5 or loops > 20):
            return CommandResult(
                success=False,
                message="Loops must be between 0.5-20",
                error=f"Invalid loops: {loops}",
            )

        return CommandResult(success=True, message="Parameters valid")

    async def _determine_orbit_coordinates(
        self,
        backend: AbstractBackend,
        coordinate_mode: str,
        center_north: Optional[float],
        center_east: Optional[float],
        altitude_relative: Optional[float],
        center_lat: Optional[float],
        center_lon: Optional[float],
        altitude_msl: Optional[float]
    ) -> CommandResult:
        """Determine orbit center coordinates based on mode and provided parameters."""
        
        try:
            # Auto-detect coordinate system if mode is "auto"
            if coordinate_mode == "auto":
                if center_lat is not None or center_lon is not None:
                    actual_mode = "global"
                elif center_north is not None or center_east is not None:
                    actual_mode = "local"
                else:
                    actual_mode = "local"  # Default to local at current position
            else:
                actual_mode = coordinate_mode

            if actual_mode == "global":
                # Global coordinate mode
                if center_lat is None or center_lon is None:
                    # Use current position if not provided
                    current_lat, current_lon, current_alt_msl = await backend.get_current_global_position()
                    center_lat = center_lat or current_lat
                    center_lon = center_lon or current_lon
                
                if altitude_msl is None:
                    # Use current altitude if not provided
                    _, _, current_alt_msl = await backend.get_current_global_position()
                    altitude_msl = current_alt_msl

                return CommandResult(
                    success=True,
                    message="Global coordinates determined",
                    data={
                        "coordinate_mode": "global",
                        "lat": center_lat,
                        "lon": center_lon,
                        "alt_msl": altitude_msl,
                    }
                )

            else:
                # Local coordinate mode
                if center_north is None or center_east is None:
                    # Use current position if not provided
                    current_north, current_east, current_down = await backend.get_current_local_position()
                    center_north = center_north or current_north
                    center_east = center_east or current_east

                if altitude_relative is None:
                    # Use current altitude if not provided
                    _, _, current_down = await backend.get_current_local_position()
                    altitude_relative = max(1.0, -current_down)  # Convert NED down to relative altitude

                return CommandResult(
                    success=True,
                    message="Local coordinates determined",
                    data={
                        "coordinate_mode": "local",
                        "north": center_north,
                        "east": center_east,
                        "alt_relative": altitude_relative,
                    }
                )

        except Exception as e:
            return CommandResult(
                success=False,
                message="Failed to determine orbit coordinates",
                error=f"Coordinate determination error: {e}",
            )

    def _calculate_expected_duration(
        self,
        radius: float,
        velocity: float,
        duration: Optional[float],
        loops: Optional[float]
    ) -> float:
        """Calculate expected orbit duration for monitoring purposes."""
        
        if duration is not None:
            return duration
        elif loops is not None:
            # Calculate time for specified number of loops
            circumference = 2 * math.pi * radius
            time_per_loop = circumference / abs(velocity)
            return loops * time_per_loop
        else:
            # Continuous mode - use a large value for monitoring
            return 300.0  # 5 minutes default monitoring

    async def _monitor_orbit_execution(
        self,
        backend: AbstractBackend,
        duration: Optional[float],
        loops: Optional[float],
        continuous: bool,
        expected_duration: float,
        timeout: float,
        radius: float,
        velocity: float
    ) -> CommandResult:
        """Monitor orbit execution and handle completion based on duration control."""
        
        start_time = asyncio.get_event_loop().time()
        circumference = 2 * math.pi * radius
        time_per_loop = circumference / abs(velocity)
        
        try:
            # Monitoring loop
            while True:
                await self.check_cancelled()
                
                elapsed = asyncio.get_event_loop().time() - start_time
                estimated_loops = elapsed / time_per_loop if time_per_loop > 0 else 0
                
                # Log progress every 5 seconds
                if int(elapsed) % 5 == 0:
                    logger.info(
                        "orbit_progress",
                        elapsed=elapsed,
                        estimated_loops=estimated_loops,
                        expected_duration=expected_duration,
                        drone_id=backend.drone_id,
                    )

                # Check completion conditions
                if duration is not None:
                    # Time-based completion
                    if elapsed >= duration:
                        return CommandResult(
                            success=True,
                            message="Duration completed",
                            data={
                                "completion_reason": f"duration ({duration}s)",
                                "loops_completed": estimated_loops,
                            }
                        )
                
                elif loops is not None:
                    # Loop-based completion
                    if estimated_loops >= loops:
                        return CommandResult(
                            success=True,
                            message="Loops completed",
                            data={
                                "completion_reason": f"{loops} loops",
                                "loops_completed": estimated_loops,
                            }
                        )
                
                elif continuous:
                    # Continuous mode - only stop on timeout or cancellation
                    if elapsed >= timeout:
                        return CommandResult(
                            success=False,
                            message="Continuous orbit timed out",
                            error=f"Timeout after {timeout}s in continuous mode",
                            data={"loops_completed": estimated_loops}
                        )
                
                # General timeout check
                if elapsed >= timeout:
                    return CommandResult(
                        success=False,
                        message="Orbit execution timed out",
                        error=f"Timeout after {timeout}s",
                        data={"loops_completed": estimated_loops}
                    )

                # Check drone state for critical failures
                state = await backend.get_state()
                if state in [DroneState.DISCONNECTED, DroneState.EMERGENCY]:
                    return CommandResult(
                        success=False,
                        message="Orbit interrupted by drone state change",
                        error=f"Drone state changed to {state}",
                        data={"loops_completed": estimated_loops}
                    )

                await asyncio.sleep(1.0)  # Check every second

        except asyncio.CancelledError:
            estimated_loops = (asyncio.get_event_loop().time() - start_time) / time_per_loop
            return CommandResult(
                success=False,
                message="Orbit monitoring cancelled",
                error="Cancelled during execution",
                data={"loops_completed": estimated_loops}
            )