# agent/src/agent/connection.py
"""
Drone Connection Module

Handles the connection to the flight controller using MAVSDK.
Provides a unified interface for drone operations.
"""

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass

import structlog
from mavsdk import System
from mavsdk.offboard import VelocityNedYaw
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()


@dataclass
class DroneState:
    """Current state of the drone."""

    armed: bool = False
    is_flying: bool = False
    position: tuple[float, float, float] = (0.0, 0.0, 0.0)  # lat, lon, alt
    battery_percent: float = 0.0
    gps_fix: bool = False
    heading: float = 0.0
    groundspeed: float = 0.0
    mode: str = "UNKNOWN"


class DroneConnection:
    """
    Manages the connection to the drone via MAVSDK.

    This class provides:
    - Connection management with retry logic
    - High-level drone operations
    - State monitoring
    - Safety checks
    """

    def __init__(self, system_address: str = "udp://:14540", port: int = 50051):
        """
        Initialize drone connection.

        Args:
            system_address: MAVSDK system address
            port: MAVSDK server port (for future gRPC use)
        """
        self.system_address = system_address
        self.port = port
        self.drone = System()
        self._connected = False
        self._state = DroneState()
        self._telemetry_task: asyncio.Task | None = None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True,
    )
    async def connect(self) -> None:
        """
        Connect to the drone with retry logic.

        Raises:
            Exception: If connection fails after retries
        """
        logger.info("Connecting to drone", address=self.system_address)

        try:
            await self.drone.connect(system_address=self.system_address)

            # Wait for connection
            async for state in self.drone.core.connection_state():
                if state.is_connected:
                    logger.info("Drone connected")
                    self._connected = True
                    break

            # Start telemetry monitoring
            self._telemetry_task = asyncio.create_task(self._monitor_telemetry())

            # Get initial system info
            info = await self.drone.info.get_identification()
            logger.info(
                "Connected to system",
                hardware_uid=info.hardware_uid,
                legacy_uid=info.legacy_uid,
            )

        except Exception as e:
            logger.error("Failed to connect to drone", error=str(e))
            self._connected = False
            raise

    async def disconnect(self) -> None:
        """Disconnect from the drone and cleanup resources."""
        logger.info("Disconnecting from drone")

        if self._telemetry_task and not self._telemetry_task.done():
            self._telemetry_task.cancel()
            try:
                await self._telemetry_task
            except asyncio.CancelledError:
                pass

        self._connected = False

    async def is_connected(self) -> bool:
        """Check if drone is connected."""
        if not self._connected:
            return False

        # Double-check with actual connection state
        async for state in self.drone.core.connection_state():
            return state.is_connected

        return False

    @property
    def state(self) -> DroneState:
        """Get current drone state."""
        return self._state

    async def _monitor_telemetry(self) -> None:
        """Monitor and update drone telemetry."""
        try:
            # Monitor multiple telemetry streams concurrently
            await asyncio.gather(
                self._monitor_armed(),
                self._monitor_flight_mode(),
                self._monitor_position(),
                self._monitor_battery(),
                self._monitor_gps(),
            )
        except asyncio.CancelledError:
            logger.debug("Telemetry monitoring cancelled")
            raise
        except Exception as e:
            logger.error("Telemetry monitoring error", error=str(e))

    async def _monitor_armed(self) -> None:
        """Monitor armed state."""
        async for is_armed in self.drone.telemetry.armed():
            self._state.armed = is_armed

    async def _monitor_flight_mode(self) -> None:
        """Monitor flight mode."""
        async for flight_mode in self.drone.telemetry.flight_mode():
            self._state.mode = str(flight_mode)

    async def _monitor_position(self) -> None:
        """Monitor position."""
        async for position in self.drone.telemetry.position():
            self._state.position = (
                position.latitude_deg,
                position.longitude_deg,
                position.relative_altitude_m,
            )

    async def _monitor_battery(self) -> None:
        """Monitor battery."""
        async for battery in self.drone.telemetry.battery():
            self._state.battery_percent = battery.remaining_percent * 100

    async def _monitor_gps(self) -> None:
        """Monitor GPS info."""
        async for gps_info in self.drone.telemetry.gps_info():
            self._state.gps_fix = gps_info.fix_type >= 3  # 3D fix or better

    # High-level operations

    async def arm(self) -> None:
        """
        Arm the drone.

        Raises:
            Exception: If arming fails
        """
        logger.info("Arming drone")
        await self.drone.action.arm()

    async def disarm(self) -> None:
        """
        Disarm the drone.

        Raises:
            Exception: If disarming fails
        """
        logger.info("Disarming drone")
        await self.drone.action.disarm()

    async def takeoff(self, altitude: float = 10.0) -> None:
        """
        Take off to specified altitude.

        Args:
            altitude: Target altitude in meters

        Raises:
            Exception: If takeoff fails
        """
        logger.info("Taking off", altitude=altitude)
        await self.drone.action.set_takeoff_altitude(altitude)
        await self.drone.action.takeoff()

    async def land(self) -> None:
        """
        Land the drone.

        Raises:
            Exception: If landing fails
        """
        logger.info("Landing")
        await self.drone.action.land()

    async def return_to_launch(self) -> None:
        """
        Return to launch position.

        Raises:
            Exception: If RTL fails
        """
        logger.info("Returning to launch")
        await self.drone.action.return_to_launch()

    async def goto_location(
        self, latitude: float, longitude: float, altitude: float, yaw: float = 0.0
    ) -> None:
        """
        Fly to specified location.

        Args:
            latitude: Target latitude in degrees
            longitude: Target longitude in degrees
            altitude: Target altitude in meters (relative)
            yaw: Target yaw in degrees

        Raises:
            Exception: If goto fails
        """
        logger.info(
            "Flying to location", lat=latitude, lon=longitude, alt=altitude, yaw=yaw
        )
        await self.drone.action.goto_location(latitude, longitude, altitude, yaw)

    async def set_velocity_ned(
        self, north_m_s: float, east_m_s: float, down_m_s: float, yaw_deg: float
    ) -> None:
        """
        Set velocity in NED coordinates.

        Args:
            north_m_s: Velocity north in m/s
            east_m_s: Velocity east in m/s
            down_m_s: Velocity down in m/s
            yaw_deg: Yaw in degrees
        """
        velocity = VelocityNedYaw(north_m_s, east_m_s, down_m_s, yaw_deg)
        await self.drone.offboard.set_velocity_ned(velocity)

    async def emergency_stop(self) -> None:
        """Execute emergency stop - kill motors immediately."""
        logger.warning("EMERGENCY STOP ACTIVATED")
        await self.drone.action.kill()

    def get_telemetry_stream(self) -> AsyncIterator[dict]:
        """
        Get telemetry data stream.

        Yields:
            dict: Telemetry data
        """
        return self._create_telemetry_stream()

    async def _create_telemetry_stream(self) -> AsyncIterator[dict]:
        """Create combined telemetry stream."""
        async for position in self.drone.telemetry.position():
            # Combine with current state
            yield {
                "position": {
                    "latitude": position.latitude_deg,
                    "longitude": position.longitude_deg,
                    "altitude": position.relative_altitude_m,
                    "absolute_altitude": position.absolute_altitude_m,
                },
                "armed": self._state.armed,
                "mode": self._state.mode,
                "battery_percent": self._state.battery_percent,
                "gps_fix": self._state.gps_fix,
                "timestamp": asyncio.get_event_loop().time(),
            }
