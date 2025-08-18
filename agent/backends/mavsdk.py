"""MAVSDK drone backend implementation.

Path: agent/backends/mavsdk.py
Provides telemetry and control via MAVSDK with enhanced GPS data.

Robust implementation that handles MAVSDK version differences and missing attributes.
"""
import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Set

from mavsdk import System

logger = logging.getLogger(__name__)


@dataclass
class TelemetryState:
    """Thread-safe telemetry state container."""

    position: Optional[Dict[str, float]] = None
    attitude: Optional[Dict[str, float]] = None
    battery: Optional[Dict[str, Any]] = None
    flight_mode: Optional[str] = None
    gps_info: Optional[Dict[str, Any]] = None
    armed: Optional[bool] = None
    connected: bool = False
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict, filtering None values."""
        return {k: v for k, v in self.__dict__.items() if v is not None}


class MAVSDKBackend:
    """MAVSDK backend for drone communication with robust error handling."""

    # Default connection parameters
    DEFAULT_CONNECTION_TIMEOUT = 30.0
    DEFAULT_CHECK_INTERVAL = 0.5

    # GPS fix type mapping for different MAVSDK versions
    GPS_FIX_TYPES = {
        0: "NO_GPS",
        1: "NO_FIX",
        2: "FIX_2D",
        3: "FIX_3D",
        4: "FIX_DGPS",
        5: "RTK_FLOAT",
        6: "RTK_FIXED",
    }

    def __init__(self, connection_string: str = "udp://:14540"):
        """Initialize MAVSDK backend.

        Args:
            connection_string: MAVSDK connection string
        """
        self.drone = System()
        self._connection_string = connection_string
        self.connected = False

        # Task management
        self._telemetry_tasks: Set[asyncio.Task] = set()
        self._shutdown_event = asyncio.Event()

        # Telemetry state
        self._telemetry_state = TelemetryState()
        self._px4_origin: Optional[Dict[str, float]] = None
        self._origin_set = False

    async def connect(self, connection_string: Optional[str] = None) -> bool:
        """Connect to drone via MAVSDK.

        Args:
            connection_string: Override connection string (optional)

        Returns:
            bool: True if connection successful
        """
        conn_str = connection_string or self._connection_string

        try:
            logger.info(f"Connecting to drone at {conn_str}")
            start_time = time.time()

            # Connect with timeout
            try:
                await asyncio.wait_for(self.drone.connect(system_address=conn_str), timeout=5.0)
            except asyncio.TimeoutError:
                logger.error("❌ MAVSDK connect() timed out")
                return False

            # Wait for connection state with proper timeout
            if await self._wait_for_connection(start_time):
                await self._start_telemetry_collection()
                self.connected = True

                elapsed = time.time() - start_time
                logger.info(f"✅ Connected to drone in {elapsed:.1f}s")
                return True
            else:
                logger.error(f"❌ Connection timeout after {self.DEFAULT_CONNECTION_TIMEOUT}s")
                return False

        except Exception as e:
            logger.error(f"❌ Connection failed: {e}")
            self.connected = False
            return False

    async def _wait_for_connection(self, start_time: float) -> bool:
        """Wait for drone connection with proper timeout handling."""
        while time.time() - start_time < self.DEFAULT_CONNECTION_TIMEOUT:
            try:
                # Use timeout for each connection state check
                async with asyncio.timeout(2.0):
                    async for state in self.drone.core.connection_state():
                        if state.is_connected:
                            return True
                        break  # Only check once per iteration

                await asyncio.sleep(self.DEFAULT_CHECK_INTERVAL)

            except asyncio.TimeoutError:
                logger.debug("Connection state check timed out, retrying...")
                continue
            except Exception as e:
                logger.warning(f"Error checking connection state: {e}")
                await asyncio.sleep(self.DEFAULT_CHECK_INTERVAL)

        return False

    async def _start_telemetry_collection(self) -> None:
        """Start all telemetry collection tasks with proper error handling."""
        collectors = [
            ("position", self._collect_position),
            ("attitude", self._collect_attitude),
            ("battery", self._collect_battery),
            ("flight_mode", self._collect_flight_mode),
            ("gps_info", self._collect_gps_info),
            ("armed_state", self._collect_armed_state),
        ]

        for name, collector in collectors:
            try:
                task = asyncio.create_task(
                    self._safe_collect(name, collector), name=f"telemetry_{name}"
                )
                self._telemetry_tasks.add(task)
                # Remove completed tasks automatically
                task.add_done_callback(self._telemetry_tasks.discard)

            except Exception as e:
                logger.error(f"Failed to start {name} collector: {e}")

    async def _safe_collect(self, name: str, collector_func) -> None:
        """Safely run telemetry collector with error handling and restart logic."""
        retry_count = 0
        max_retries = 3

        while not self._shutdown_event.is_set() and retry_count < max_retries:
            try:
                await collector_func()
                # If we get here, the collector ended normally
                break

            except asyncio.CancelledError:
                logger.debug(f"Telemetry collector {name} cancelled")
                break

            except Exception as e:
                retry_count += 1
                logger.error(f"Telemetry collector {name} failed (attempt {retry_count}): {e}")

                if retry_count < max_retries:
                    # Exponential backoff for retries
                    await asyncio.sleep(min(2**retry_count, 10))
                else:
                    logger.error(
                        f"Telemetry collector {name} failed permanently after {max_retries} attempts"
                    )

    async def _collect_position(self) -> None:
        """Collect position telemetry with robust error handling."""
        async for position in self.drone.telemetry.position():
            try:
                self._telemetry_state.position = {
                    "latitude": getattr(position, 'latitude_deg', 0.0),
                    "longitude": getattr(position, 'longitude_deg', 0.0),
                    "altitude": getattr(position, 'absolute_altitude_m', 0.0),
                    "relative_altitude": getattr(position, 'relative_altitude_m', 0.0),
                }

                # Set PX4 origin on first valid GPS fix
                await self._maybe_set_origin(position)

            except Exception as e:
                logger.error(f"Error processing position data: {e}")

    async def _maybe_set_origin(self, position) -> None:
        """Set PX4 origin on first valid GPS position with validation."""
        try:
            lat = getattr(position, 'latitude_deg', 0.0)
            lon = getattr(position, 'longitude_deg', 0.0)
            alt = getattr(position, 'absolute_altitude_m', 0.0)

            if (
                not self._origin_set
                and lat != 0.0
                and lon != 0.0
                and -90 <= lat <= 90
                and -180 <= lon <= 180
            ):
                self._px4_origin = {
                    "latitude": lat,
                    "longitude": lon,
                    "altitude": alt,
                }
                self._origin_set = True
                logger.info(f"PX4 origin set: {self._px4_origin}")

        except Exception as e:
            logger.error(f"Error setting PX4 origin: {e}")

    async def _collect_attitude(self) -> None:
        """Collect attitude telemetry with safe attribute access."""
        async for attitude in self.drone.telemetry.attitude_euler():
            try:
                self._telemetry_state.attitude = {
                    "roll": getattr(attitude, 'roll_deg', 0.0),
                    "pitch": getattr(attitude, 'pitch_deg', 0.0),
                    "yaw": getattr(attitude, 'yaw_deg', 0.0),
                }
            except Exception as e:
                logger.error(f"Error processing attitude data: {e}")

    async def _collect_battery(self) -> None:
        """Collect battery telemetry with version-safe attribute access."""
        async for battery in self.drone.telemetry.battery():
            try:
                # Use safe attribute access for version compatibility
                battery_data = {
                    "voltage": getattr(battery, 'voltage_v', 0.0),
                    "remaining_percent": getattr(battery, 'remaining_percent', 0.0) * 100,
                }

                # Optional attributes that may not exist in all MAVSDK versions
                if hasattr(battery, 'current_battery_a'):
                    battery_data["current"] = battery.current_battery_a

                # Try different capacity attribute names
                for capacity_attr in ['capacity_consumed_ah', 'consumed_ah', 'capacity_ah']:
                    if hasattr(battery, capacity_attr):
                        battery_data["capacity_consumed"] = getattr(battery, capacity_attr)
                        break

                self._telemetry_state.battery = battery_data

            except Exception as e:
                logger.error(f"Error processing battery data: {e}")

    async def _collect_flight_mode(self) -> None:
        """Collect flight mode telemetry with safe string conversion."""
        async for flight_mode in self.drone.telemetry.flight_mode():
            try:
                self._telemetry_state.flight_mode = str(flight_mode)
            except Exception as e:
                logger.error(f"Error processing flight mode data: {e}")

    async def _collect_gps_info(self) -> None:
        """Collect GPS information with robust attribute handling."""
        async for gps_info in self.drone.telemetry.gps_info():
            try:
                gps_data = {
                    "num_satellites": getattr(gps_info, 'num_satellites', 0),
                    "fix_type": self._get_fix_type_string(getattr(gps_info, 'fix_type', 0)),
                }

                # Optional precision attributes (may not exist in all versions)
                for attr_name in ['hdop', 'vdop', 'horizontal_accuracy_m', 'vertical_accuracy_m']:
                    if hasattr(gps_info, attr_name):
                        value = getattr(gps_info, attr_name)
                        if value is not None:
                            gps_data[attr_name] = value

                self._telemetry_state.gps_info = gps_data

            except Exception as e:
                logger.error(f"Error processing GPS info data: {e}")

    async def _collect_armed_state(self) -> None:
        """Collect armed state with error handling."""
        async for armed in self.drone.telemetry.armed():
            try:
                self._telemetry_state.armed = bool(armed)
            except Exception as e:
                logger.error(f"Error processing armed state data: {e}")

    def _get_fix_type_string(self, fix_type) -> str:
        """Convert GPS fix type to readable string with robust handling."""
        try:
            # Handle different MAVSDK versions
            if hasattr(fix_type, 'value'):
                fix_value = fix_type.value
            else:
                fix_value = int(fix_type)

            return self.GPS_FIX_TYPES.get(fix_value, f"UNKNOWN_{fix_value}")

        except Exception as e:
            logger.warning(f"Error converting fix type: {e}")
            return str(fix_type)

    async def get_telemetry(self) -> Dict[str, Any]:
        """Get current telemetry data with connection status.

        Returns:
            dict: Current telemetry including all available data
        """
        # Update connection status and timestamp
        self._telemetry_state.connected = self.connected
        self._telemetry_state.timestamp = time.time()

        # Get base telemetry
        telemetry = self._telemetry_state.to_dict()

        # Add PX4 origin
        if self._px4_origin:
            telemetry["px4_origin"] = self._px4_origin.copy()
        else:
            # Provide default origin if not yet set
            telemetry["px4_origin"] = {
                "latitude": 47.3977505,  # Zurich default
                "longitude": 8.5456072,
                "altitude": 488.0,
            }

        return telemetry

    async def get_px4_origin(self) -> Optional[Dict[str, float]]:
        """Get PX4 origin (first GPS fix position).

        Returns:
            Optional[dict]: Origin with latitude, longitude, altitude or None
        """
        return self._px4_origin.copy() if self._px4_origin else None

    async def disconnect(self) -> None:
        """Cleanly disconnect from drone with proper cleanup."""
        logger.info("Disconnecting from drone...")

        # Signal shutdown to all collectors
        self._shutdown_event.set()

        # Cancel all telemetry tasks
        if self._telemetry_tasks:
            for task in list(self._telemetry_tasks):
                if not task.done():
                    task.cancel()

            # Wait for tasks to complete cancellation
            if self._telemetry_tasks:
                await asyncio.gather(*self._telemetry_tasks, return_exceptions=True)

            self._telemetry_tasks.clear()

        # Reset state
        self.connected = False
        self._telemetry_state = TelemetryState()
        self._px4_origin = None
        self._origin_set = False
        self._shutdown_event.clear()

        logger.info("🔌 Disconnected from drone")

    def __del__(self) -> None:
        """Cleanup warning for proper resource management."""
        if self._telemetry_tasks and not asyncio.get_event_loop().is_closed():
            logger.warning("MAVSDKBackend deleted without proper disconnect() call")
