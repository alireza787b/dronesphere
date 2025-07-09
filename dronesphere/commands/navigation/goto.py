"""Enhanced Goto command with dual positioning modes and real position verification.

This module provides absolute and relative positioning modes:
- Absolute: Target coordinates relative to takeoff origin (default)
- Relative: Movement delta from current position

Key features:
- Dual positioning modes with automatic coordinate calculation
- Real NED position verification using MAVSDK position_velocity_ned()
- Velocity control with configurable max/approach speeds
- Movement detection and progress tracking
- Comprehensive error handling and safety checks
"""

import asyncio
import math

from dronesphere.backends.base import AbstractBackend
from dronesphere.commands.base import BaseCommand
from dronesphere.core.logging import get_logger
from dronesphere.core.models import CommandResult, DroneState, Position

logger = get_logger(__name__)


class GotoCommand(BaseCommand):
    """Command to fly to local NED coordinates with absolute or relative positioning modes.

    Positioning Modes:
    1. ABSOLUTE (default): Coordinates relative to takeoff origin
       Example: goto(north=10, east=5, down=-3) → fly to (10,5,-3) from origin

    2. RELATIVE: Movement delta from current position
       Example: goto(north=5, east=0, down=-2, relative=True) → move 5m north, 2m up from current position

    The command uses MAVSDK offboard mode for precise positioning with real-time
    position verification and movement detection.
    """

    async def run(self, backend: AbstractBackend, **params) -> CommandResult:
        """Execute goto command with enhanced dual-mode positioning control.

        Args:
            backend: MAVSDK backend for drone control
            **params: Command parameters including positioning mode

        Returns:
            CommandResult with detailed execution information
        """
        # Extract and validate parameters
        north = params.get("north", 0.0)
        east = params.get("east", 0.0)
        down = params.get("down", -5.0)  # Default 5m altitude (NED: negative = up)
        yaw = params.get("yaw", 0.0)
        relative = params.get("relative", False)  # New: positioning mode
        tolerance = params.get("tolerance", 2.0)  # meters
        timeout = params.get("timeout", 60.0)  # seconds
        max_speed = params.get("max_speed", 2.0)  # m/s - maximum horizontal speed
        approach_speed = params.get(
            "approach_speed", 0.5
        )  # m/s - speed when close to target

        # Determine positioning mode description
        mode_desc = "relative" if relative else "absolute"

        logger.info(
            "goto_command_started",
            command_id=id(self),
            positioning_mode=mode_desc,
            input_north=north,
            input_east=east,
            input_down=down,
            yaw=yaw,
            relative=relative,
            tolerance=tolerance,
            max_speed=max_speed,
            approach_speed=approach_speed,
            drone_id=backend.drone_id,
        )

        try:
            # Check if drone is flying
            initial_state = await backend.get_state()
            if initial_state not in [DroneState.FLYING, DroneState.TAKEOFF]:
                return CommandResult(
                    success=False,
                    message="Cannot goto: drone not flying",
                    error="Drone must be flying to execute goto command",
                )

            if initial_state == DroneState.DISCONNECTED:
                return CommandResult(
                    success=False,
                    message="Cannot goto: drone disconnected",
                    error="Drone not connected",
                )

            # Get current position for validation and relative positioning
            initial_telemetry = await backend.get_telemetry()
            if (
                not initial_telemetry
                or not initial_telemetry.position
                or initial_telemetry.position.north is None
            ):
                return CommandResult(
                    success=False,
                    message="Cannot goto: local position not available",
                    error="Local NED coordinates not available - ensure GPS and local position estimate are active",
                )

            current_pos = initial_telemetry.position

            # Calculate target coordinates based on positioning mode
            if relative:
                # RELATIVE MODE: Add deltas to current position
                target_north = current_pos.north + north
                target_east = current_pos.east + east
                target_down = current_pos.down + down

                logger.info(
                    "goto_relative_positioning",
                    current_north=current_pos.north,
                    current_east=current_pos.east,
                    current_down=current_pos.down,
                    delta_north=north,
                    delta_east=east,
                    delta_down=down,
                    target_north=target_north,
                    target_east=target_east,
                    target_down=target_down,
                    drone_id=backend.drone_id,
                )
            else:
                # ABSOLUTE MODE: Use coordinates directly (current behavior)
                target_north = north
                target_east = east
                target_down = down

                logger.info(
                    "goto_absolute_positioning",
                    target_north=target_north,
                    target_east=target_east,
                    target_down=target_down,
                    drone_id=backend.drone_id,
                )

            # Calculate distances for logging and validation
            initial_distance = math.sqrt(
                (current_pos.north - target_north) ** 2
                + (current_pos.east - target_east) ** 2
                + (current_pos.down - target_down) ** 2
            )

            # Validate target coordinates are reasonable
            if abs(target_north) > 1000 or abs(target_east) > 1000:
                return CommandResult(
                    success=False,
                    message=f"Target coordinates too far: N={target_north:.1f}, E={target_east:.1f}",
                    error="Target position exceeds safety limits (±1000m)",
                )

            if target_down > 10:  # More than 10m below ground
                return CommandResult(
                    success=False,
                    message=f"Target altitude unsafe: down={target_down:.1f}m (below ground)",
                    error="Target altitude would be below ground level",
                )

            logger.info(
                "goto_target_calculated",
                positioning_mode=mode_desc,
                current_position={
                    "north": current_pos.north,
                    "east": current_pos.east,
                    "down": current_pos.down,
                },
                target_position={
                    "north": target_north,
                    "east": target_east,
                    "down": target_down,
                },
                initial_distance=initial_distance,
                drone_id=backend.drone_id,
            )

            start_time = asyncio.get_event_loop().time()

            # Create target position
            target_position = Position(
                north=target_north, east=target_east, down=target_down
            )

            # Execute goto using offboard mode
            logger.info(
                "executing_goto_offboard",
                drone_id=backend.drone_id,
                mode=mode_desc,
                target=target_position.dict(),
                max_speed=max_speed,
            )

            await backend.goto_position(target_position, yaw, max_speed)
            await self.check_cancelled()

            # Wait for position reached with movement verification
            self._final_distance = float("inf")
            self._movement_detected = False
            success = await self._wait_for_position_reached_with_verification(
                backend, target_position, tolerance, timeout, current_pos, max_speed
            )

            duration = asyncio.get_event_loop().time() - start_time
            actual_distance = self._final_distance

            if success:
                logger.info(
                    "goto_command_completed",
                    command_id=id(self),
                    positioning_mode=mode_desc,
                    target_north=target_north,
                    target_east=target_east,
                    target_down=target_down,
                    final_distance=actual_distance,
                    movement_detected=self._movement_detected,
                    duration=duration,
                    drone_id=backend.drone_id,
                )

                return CommandResult(
                    success=True,
                    message=f"Goto ({mode_desc}) completed (reached within {actual_distance:.1f}m of target)",
                    duration=duration,
                    data={
                        "positioning_mode": mode_desc,
                        "target_north": target_north,
                        "target_east": target_east,
                        "target_down": target_down,
                        "target_yaw": yaw,
                        "final_distance": actual_distance,
                        "tolerance": tolerance,
                        "movement_detected": self._movement_detected,
                        "initial_distance": initial_distance,
                        "relative_mode": relative,
                    },
                )
            else:
                warning_msg = ""
                if not self._movement_detected:
                    warning_msg = " (NO MOVEMENT DETECTED - check offboard mode)"

                return CommandResult(
                    success=False,
                    message=f"Goto ({mode_desc}) failed - only reached within {actual_distance:.1f}m (tolerance: {tolerance}m){warning_msg}",
                    error="Position tolerance not achieved" + warning_msg,
                    duration=duration,
                    data={
                        "positioning_mode": mode_desc,
                        "target_north": target_north,
                        "target_east": target_east,
                        "target_down": target_down,
                        "final_distance": actual_distance,
                        "tolerance": tolerance,
                        "movement_detected": self._movement_detected,
                        "initial_distance": initial_distance,
                        "relative_mode": relative,
                    },
                )

        except asyncio.CancelledError:
            logger.info(
                "goto_command_cancelled",
                command_id=id(self),
                positioning_mode=mode_desc,
                drone_id=backend.drone_id,
            )
            return CommandResult(
                success=False,
                message=f"Goto ({mode_desc}) command was cancelled",
                error="Cancelled",
            )

        except Exception as e:
            logger.error(
                "goto_command_failed",
                command_id=id(self),
                positioning_mode=mode_desc,
                error=str(e),
                drone_id=backend.drone_id,
            )
            return CommandResult(
                success=False,
                message=f"Goto ({mode_desc}) failed: {str(e)}",
                error=str(e),
            )

    async def cancel(self) -> None:
        """Cancel goto command."""
        await super().cancel()

    async def _wait_for_position_reached_with_verification(
        self,
        backend: AbstractBackend,
        target_position: Position,
        tolerance: float = 2.0,
        timeout: float = 60.0,
        initial_position: Position = None,
        max_speed: float = 2.0,
    ) -> bool:
        """Wait for drone to reach target position with enhanced movement verification.

        This method provides real-time position monitoring, movement detection,
        and detailed progress logging for both absolute and relative positioning modes.

        Args:
            backend: MAVSDK backend for telemetry
            target_position: Target NED coordinates
            tolerance: Acceptable distance from target (meters)
            timeout: Maximum wait time (seconds)
            initial_position: Starting position for movement detection
            max_speed: Maximum expected speed for progress validation

        Returns:
            bool: True if target reached within tolerance, False otherwise
        """

        logger.info(
            "waiting_for_position_with_verification",
            target_north=target_position.north,
            target_east=target_position.east,
            target_down=target_position.down,
            tolerance=tolerance,
            timeout=timeout,
            max_speed=max_speed,
            drone_id=backend.drone_id,
        )

        # Store tracking variables
        self._final_distance = float("inf")
        self._movement_detected = False
        movement_threshold = 0.5  # meters - minimum movement to detect drone is moving

        async def check_position_reached():
            """Check if target position is reached with comprehensive movement verification."""
            max_checks = int(timeout / 0.5)
            best_distance = float("inf")
            previous_pos = initial_position
            max_distance_from_initial = 0.0
            stuck_counter = 0
            last_significant_movement_time = asyncio.get_event_loop().time()

            for check_num in range(max_checks):
                try:
                    await self.check_cancelled()

                    # Get current telemetry with retry
                    telemetry = await backend.get_telemetry()

                    if not telemetry or not telemetry.position:
                        await asyncio.sleep(0.5)
                        continue

                    current_pos = telemetry.position

                    # Skip if no local coordinates available
                    if (
                        current_pos.north is None
                        or current_pos.east is None
                        or current_pos.down is None
                    ):
                        if check_num % 4 == 0:  # Log every 2 seconds
                            logger.warning(
                                "waiting_for_local_coordinates",
                                drone_id=backend.drone_id,
                            )
                        await asyncio.sleep(0.5)
                        continue

                    # Calculate distance to target
                    distance_to_target = math.sqrt(
                        (current_pos.north - target_position.north) ** 2
                        + (current_pos.east - target_position.east) ** 2
                        + (current_pos.down - target_position.down) ** 2
                    )

                    best_distance = min(best_distance, distance_to_target)
                    self._final_distance = best_distance

                    # Enhanced movement detection from initial position
                    if initial_position and initial_position.north is not None:
                        distance_from_initial = math.sqrt(
                            (current_pos.north - initial_position.north) ** 2
                            + (current_pos.east - initial_position.east) ** 2
                            + (current_pos.down - initial_position.down) ** 2
                        )

                        max_distance_from_initial = max(
                            max_distance_from_initial, distance_from_initial
                        )

                        if distance_from_initial > movement_threshold:
                            self._movement_detected = True
                            last_significant_movement_time = (
                                asyncio.get_event_loop().time()
                            )
                            stuck_counter = 0
                        else:
                            stuck_counter += 1

                    # Check for position change between measurements
                    if previous_pos and previous_pos.north is not None:
                        movement_since_last = math.sqrt(
                            (current_pos.north - previous_pos.north) ** 2
                            + (current_pos.east - previous_pos.east) ** 2
                            + (current_pos.down - previous_pos.down) ** 2
                        )

                        if movement_since_last > 0.1:  # 10cm movement threshold
                            last_significant_movement_time = (
                                asyncio.get_event_loop().time()
                            )
                            stuck_counter = 0

                    previous_pos = current_pos

                    # Log detailed progress every 4 seconds
                    if check_num % 8 == 0:  # Every 4 seconds (8 * 0.5s)
                        logger.info(
                            "goto_progress_detailed",
                            current_north=current_pos.north,
                            current_east=current_pos.east,
                            current_down=current_pos.down,
                            target_north=target_position.north,
                            target_east=target_position.east,
                            target_down=target_position.down,
                            distance_to_target=distance_to_target,
                            tolerance=tolerance,
                            movement_detected=self._movement_detected,
                            max_distance_from_initial=max_distance_from_initial,
                            elapsed_time=check_num * 0.5,
                            drone_id=backend.drone_id,
                        )

                    # Success condition - target reached within tolerance
                    if distance_to_target <= tolerance:
                        logger.info(
                            "goto_position_reached",
                            achieved_distance=distance_to_target,
                            tolerance=tolerance,
                            movement_detected=self._movement_detected,
                            max_distance_from_initial=max_distance_from_initial,
                            drone_id=backend.drone_id,
                        )
                        self._final_distance = distance_to_target
                        return True

                    # Warning if no movement detected for extended period
                    time_since_movement = (
                        asyncio.get_event_loop().time() - last_significant_movement_time
                    )
                    if time_since_movement > 10.0 and not self._movement_detected:
                        logger.warning(
                            "goto_no_movement_detected",
                            time_since_movement=time_since_movement,
                            distance_to_target=distance_to_target,
                            max_distance_from_initial=max_distance_from_initial,
                            note="Check if offboard mode is active",
                            drone_id=backend.drone_id,
                        )

                    # Check drone state for critical failures
                    state = await backend.get_state()
                    if state in [DroneState.DISCONNECTED, DroneState.EMERGENCY]:
                        logger.error(
                            "goto_failed_bad_state",
                            state=state,
                            drone_id=backend.drone_id,
                        )
                        self._final_distance = best_distance
                        return False

                except Exception as e:
                    logger.warning(
                        "goto_check_error",
                        error=str(e),
                        check_number=check_num,
                        drone_id=backend.drone_id,
                    )

                await asyncio.sleep(0.5)

            # Timeout reached
            logger.warning(
                "goto_timeout_reached",
                timeout=timeout,
                best_distance=best_distance,
                tolerance=tolerance,
                movement_detected=self._movement_detected,
                max_distance_from_initial=max_distance_from_initial,
                drone_id=backend.drone_id,
            )
            self._final_distance = best_distance
            return False

        success = await self.wait_for_cancel_or_condition(
            check_position_reached(), timeout + 1
        )

        if self._final_distance == float("inf"):
            self._final_distance = 999.0

        return success
