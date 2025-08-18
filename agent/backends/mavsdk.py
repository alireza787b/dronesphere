"""MAVSDK drone backend implementation - FIXED VERSION.

Path: agent/backends/mavsdk.py
Provides telemetry and control via MAVSDK with enhanced GPS data.

FIXES:
- Updated connection string format (udpin:// instead of udp://)
- Docker bridge network detection and configuration
- Robust port binding with fallback options
- Environment-aware connection setup
"""
import asyncio
import logging
import os
import subprocess
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

    def __init__(self, connection_string: Optional[str] = None):
        """Initialize MAVSDK backend with smart connection detection.

        Args:
            connection_string: Override connection string (optional)
        """
        self.drone = System()
        self._connection_string = connection_string or self._detect_connection_string()
        self.connected = False

        # Task management
        self._telemetry_tasks: Set[asyncio.Task] = set()
        self._shutdown_event = asyncio.Event()

        # Telemetry state
        self._telemetry_state = TelemetryState()
        self._px4_origin: Optional[Dict[str, float]] = None
        self._origin_set = False

        logger.info(f"🔧 MAVSDK Backend initialized with connection: {self._connection_string}")

    def _detect_connection_string(self) -> str:
        """Detect the appropriate connection string based on environment."""
        # Check for environment variable override
        if env_conn := os.getenv("MAVSDK_CONNECTION_STRING"):
            logger.info(f"📡 Using env MAVSDK_CONNECTION_STRING: {env_conn}")
            return env_conn

        # Check if we're in Docker or if SITL container is running
        docker_bridge_ip = self._get_docker_bridge_ip()
        if docker_bridge_ip:
            conn_str = f"udpin://{docker_bridge_ip}:14540"
            logger.info(f"🐳 Detected Docker environment, using: {conn_str}")
            return conn_str

        # Check if SITL container is running and get its IP
        sitl_ip = self._get_sitl_container_ip()
        if sitl_ip:
            conn_str = f"udpin://{sitl_ip}:14540"
            logger.info(f"🚁 Detected SITL container at: {conn_str}")
            return conn_str

        # Default to localhost with new format
        logger.info("🏠 Using localhost connection")
        return "udpin://127.0.0.1:14540"

    def _get_docker_bridge_ip(self) -> Optional[str]:
        """Get Docker bridge network IP if available."""
        try:
            result = subprocess.run(
                ["docker", "network", "inspect", "bridge"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                import json

                network_info = json.loads(result.stdout)
                if network_info and len(network_info) > 0:
                    gateway = network_info[0].get("IPAM", {}).get("Config", [{}])[0].get("Gateway")
                    if gateway:
                        logger.debug(f"Found Docker bridge gateway: {gateway}")
                        return gateway
        except Exception as e:
            logger.debug(f"Could not detect Docker bridge IP: {e}")
        return None

    def _get_sitl_container_ip(self) -> Optional[str]:
        """Get SITL container IP if running."""
        try:
            result = subprocess.run(
                [
                    "docker",
                    "inspect",
                    "-f",
                    "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}",
                    "dronesphere-sitl",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                ip = result.stdout.strip()
                logger.debug(f"Found SITL container IP: {ip}")
                return ip
        except Exception as e:
            logger.debug(f"Could not get SITL container IP: {e}")
        return None

    def _check_port_availability(self, port: int) -> bool:
        """Check if a port is available for binding."""
        import socket

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.bind(('', port))
                return True
        except OSError:
            return False

    async def connect(self, connection_string: Optional[str] = None) -> bool:
        """Connect to drone via MAVSDK with intelligent fallback.

        Args:
            connection_string: Override connection string (optional)

        Returns:
            bool: True if connection successful
        """
        conn_str = connection_string or self._connection_string

        # Try multiple connection strategies
        connection_attempts = [
            conn_str,  # Primary connection string
            "udpin://127.0.0.1:14540",  # Localhost fallback
            "udpout://127.0.0.1:14550",  # Output port fallback
        ]

        # Add Docker bridge IP if available
        docker_ip = self._get_docker_bridge_ip()
        if docker_ip and f"udpin://{docker_ip}:14540" not in connection_attempts:
            connection_attempts.insert(-2, f"udpin://{docker_ip}:14540")

        for attempt, conn in enumerate(connection_attempts, 1):
            logger.info(f"🔄 Attempt {attempt}/{len(connection_attempts)}: Connecting to {conn}")

            try:
                start_time = time.time()

                # Connect with timeout
                try:
                    await asyncio.wait_for(self.drone.connect(system_address=conn), timeout=8.0)
                except asyncio.TimeoutError:
                    logger.warning(f"⏱️  Connection {attempt} timed out after 8s")
                    continue

                # Wait for connection state with proper timeout
                if await self._wait_for_connection(start_time):
                    await self._start_telemetry_collection()
                    self.connected = True
                    self._connection_string = conn  # Update successful connection string

                    elapsed = time.time() - start_time
                    logger.info(f"✅ Connected to drone at {conn} in {elapsed:.1f}s")
                    return True
                else:
                    logger.warning(f"⏱️  Connection {attempt} failed to establish")
                    continue

            except Exception as e:
                logger.warning(f"❌ Connection attempt {attempt} failed: {e}")
                continue

        logger.error("❌ All connection attempts failed")
        self.connected = False
        return False

    async def _wait_for_connection(self, start_time: float) -> bool:
        """Wait for drone connection with proper timeout handling."""
        timeout = min(15.0, self.DEFAULT_CONNECTION_TIMEOUT)  # Reduced timeout

        while time.time() - start_time < timeout:
            try:
                # Use timeout for each connection state check
                async with asyncio.timeout(3.0):
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
        tasks = [
            self._collect_position(),
            self._collect_attitude(),
            self._collect_battery(),
            self._collect_flight_mode(),
            self._collect_gps_info(),
            self._collect_armed_state(),
        ]

        for coro in tasks:
            task = asyncio.create_task(coro)
            self._telemetry_tasks.add(task)
            # Remove completed tasks
            task.add_done_callback(self._telemetry_tasks.discard)

        logger.info(f"📊 Started {len(tasks)} telemetry collection tasks")

    async def _collect_position(self) -> None:
        """Collect position data with error handling and PX4 origin tracking."""
        async for position in self.drone.telemetry.position():
            try:
                position_data = {
                    "latitude": float(position.latitude_deg),
                    "longitude": float(position.longitude_deg),
                    "altitude": float(position.absolute_altitude_m),
                    "relative_altitude": float(position.relative_altitude_m),
                }

                # Track PX4 origin (first valid GPS position)
                if (
                    not self._origin_set
                    and position_data["latitude"] != 0
                    and position_data["longitude"] != 0
                ):
                    self._px4_origin = {
                        "latitude": position_data["latitude"],
                        "longitude": position_data["longitude"],
                        "altitude": position_data["altitude"],
                    }
                    self._origin_set = True
                    logger.info(f"📍 PX4 origin set: {self._px4_origin}")

                self._telemetry_state.position = position_data

            except Exception as e:
                logger.error(f"Error processing position data: {e}")

    async def _collect_attitude(self) -> None:
        """Collect attitude data with error handling."""
        async for attitude in self.drone.telemetry.attitude_euler():
            try:
                self._telemetry_state.attitude = {
                    "roll": float(attitude.roll_deg),
                    "pitch": float(attitude.pitch_deg),
                    "yaw": float(attitude.yaw_deg),
                }
            except Exception as e:
                logger.error(f"Error processing attitude data: {e}")

    async def _collect_battery(self) -> None:
        """Collect battery data with error handling."""
        async for battery in self.drone.telemetry.battery():
            try:
                self._telemetry_state.battery = {
                    "voltage": float(battery.voltage_v),
                    "remaining": float(battery.remaining_percent),
                }
            except Exception as e:
                logger.error(f"Error processing battery data: {e}")

    async def _collect_flight_mode(self) -> None:
        """Collect flight mode data with error handling."""
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
