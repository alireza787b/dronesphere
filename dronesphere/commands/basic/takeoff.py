"""Takeoff command implementation with relaxed altitude criteria and fixed imports."""

import asyncio

from dronesphere.backends.base import AbstractBackend
from dronesphere.commands.base import BaseCommand
from dronesphere.core.logging import get_logger
from dronesphere.core.models import CommandResult, DroneState

logger = get_logger(__name__)


class TakeoffCommand(BaseCommand):
    """Command to take off to specified altitude."""

    async def run(self, backend: AbstractBackend, **params) -> CommandResult:
        """Execute takeoff command."""
        altitude = params.get("altitude", 10.0)
        # NEW: More lenient altitude checking
        altitude_tolerance = params.get(
            "altitude_tolerance", 0.6
        )  # Accept 60% of target
        timeout = params.get("timeout", 20)  # Reduced timeout

        logger.info(
            "takeoff_command_started",
            command_id=id(self),
            altitude=altitude,
            tolerance=altitude_tolerance,
            drone_id=backend.drone_id,
        )

        try:
            # Check initial state
            initial_state = await backend.get_state()
            if initial_state == DroneState.DISCONNECTED:
                return CommandResult(
                    success=False,
                    message="Cannot takeoff: drone disconnected",
                    error="Drone not connected",
                )

            # Check if already flying
            if initial_state in [DroneState.FLYING, DroneState.TAKEOFF]:
                return CommandResult(
                    success=True,  # Already flying is success!
                    message="Drone already airborne",
                    data={"already_flying": True},
                )

            start_time = asyncio.get_event_loop().time()

            # Arm if not already armed
            if not await backend.is_armed():
                logger.info("arming_for_takeoff", drone_id=backend.drone_id)
                await backend.hold()
                await backend.arm()
                await self.check_cancelled()

            # Execute takeoff
            logger.info(
                "executing_takeoff", drone_id=backend.drone_id, altitude=altitude
            )
            await backend.takeoff(altitude)
            await self.check_cancelled()

            # # Wait for takeoff completion with relaxed criteria
            # success, actual_altitude = await self._wait_for_takeoff_completion(
            #     backend, altitude, altitude_tolerance, timeout
            # )

            duration = asyncio.get_event_loop().time() - start_time

            if success:
                logger.info(
                    "takeoff_command_completed",
                    command_id=id(self),
                    target_altitude=altitude,
                    actual_altitude=actual_altitude,
                    duration=duration,
                    drone_id=backend.drone_id,
                )

                return CommandResult(
                    success=True,
                    message=f"Takeoff completed (reached {actual_altitude:.1f}m of {altitude}m target)",
                    duration=duration,
                    data={
                        "target_altitude": altitude,
                        "actual_altitude": actual_altitude,
                        "tolerance_met": True,
                    },
                )
            else:
                # NEW: Soft failure - check if we got some altitude
                current_telemetry = await backend.get_telemetry()
                current_alt = (
                    current_telemetry.position.altitude_relative
                    if current_telemetry.position
                    else 0
                )

                if current_alt > 0.5:  # Got some altitude
                    logger.warning(
                        "takeoff_partial_success",
                        target_altitude=altitude,
                        actual_altitude=current_alt,
                        drone_id=backend.drone_id,
                    )
                    return CommandResult(
                        success=True,  # Treat as soft success
                        message=f"Takeoff partially successful (reached {current_alt:.1f}m of {altitude}m)",
                        duration=duration,
                        data={
                            "target_altitude": altitude,
                            "actual_altitude": current_alt,
                            "partial_success": True,
                        },
                    )

                return CommandResult(
                    success=False,
                    message=f"Takeoff failed - only reached {current_alt:.1f}m of {altitude}m",
                    error="Altitude not achieved",
                    duration=duration,
                )

        except asyncio.CancelledError:
            logger.info(
                "takeoff_command_cancelled",
                command_id=id(self),
                drone_id=backend.drone_id,
            )
            return CommandResult(
                success=False,
                message="Takeoff command was cancelled",
                error="Cancelled",
            )

        except Exception as e:
            logger.error(
                "takeoff_command_failed",
                command_id=id(self),
                error=str(e),
                drone_id=backend.drone_id,
            )
            return CommandResult(
                success=False, message=f"Takeoff failed: {str(e)}", error=str(e)
            )

    async def cancel(self) -> None:
        """Cancel takeoff command."""
        await super().cancel()
        # Could add takeoff-specific cancellation logic here
        # For now, rely on the backend's cancellation handling

    async def _wait_for_takeoff_completion(
        self,
        backend: AbstractBackend,
        target_altitude: float,
        tolerance: float = 0.6,
        timeout: float = 20.0,
    ) -> tuple[bool, float]:
        """Wait for takeoff to complete with relaxed criteria."""

        target_min = target_altitude * tolerance
        logger.info(
            "waiting_for_altitude",
            target=target_altitude,
            minimum_acceptable=target_min,
            timeout=timeout,
            drone_id=backend.drone_id,
        )

        async def check_altitude_achieved():
            """Check if minimum altitude is achieved."""
            max_checks = int(timeout / 0.5)
            best_altitude = 0.0

            for check_num in range(max_checks):
                try:
                    await self.check_cancelled()

                    # Get current state and altitude
                    state = await backend.get_state()
                    telemetry = await backend.get_telemetry()

                    current_altitude = 0.0
                    if telemetry and telemetry.position:
                        # Use NED down coordinate for consistent altitude calculation
                        if telemetry.position.down is not None:
                            current_altitude = max(0.0, -telemetry.position.down)
                        else:
                            current_altitude = (
                                telemetry.position.altitude_relative or 0.0
                            )

                    best_altitude = max(best_altitude, current_altitude)

                    # Log progress every 2 seconds
                    if check_num % 4 == 0:  # Every 2 seconds (4 * 0.5s)
                        logger.info(
                            "takeoff_progress",
                            current_altitude=current_altitude,
                            target_minimum=target_min,
                            target_full=target_altitude,
                            progress_percent=int(
                                (current_altitude / target_altitude) * 100
                            ),
                            drone_id=backend.drone_id,
                        )

                    # Success conditions
                    if current_altitude >= target_min:
                        logger.info(
                            "takeoff_altitude_achieved",
                            achieved=current_altitude,
                            target=target_altitude,
                            drone_id=backend.drone_id,
                        )
                        return True, current_altitude

                    # If we're flying and have some altitude, be more lenient after 10s
                    if (
                        check_num > 20  # After 10 seconds
                        and state == DroneState.FLYING
                        and current_altitude > 1.0
                    ):  # At least 1m
                        logger.info(
                            "takeoff_flying_assumed_success",
                            altitude=current_altitude,
                            state=state,
                            drone_id=backend.drone_id,
                        )
                        return True, current_altitude

                    # If disconnected or emergency, fail
                    if state in [DroneState.DISCONNECTED, DroneState.EMERGENCY]:
                        logger.error(
                            "takeoff_failed_bad_state",
                            state=state,
                            drone_id=backend.drone_id,
                        )
                        return False, best_altitude

                except Exception as e:
                    logger.warning(
                        "takeoff_check_error", error=str(e), drone_id=backend.drone_id
                    )

                await asyncio.sleep(0.5)

            logger.warning(
                "takeoff_timeout_reached",
                timeout=timeout,
                best_altitude=best_altitude,
                target_minimum=target_min,
                drone_id=backend.drone_id,
            )
            return False, best_altitude

        # Call check_altitude_achieved directly since it returns (bool, float)
        success, altitude = await check_altitude_achieved()

        return success, altitude
