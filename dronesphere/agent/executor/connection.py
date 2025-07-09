"""Drone connection management for agent.

This module provides the DroneConnection class that manages the connection
to a single drone and provides access to its telemetry and control functions.
"""


from dronesphere.backends.base import AbstractBackend, BackendFactory, TelemetryProvider
from dronesphere.core.errors import DroneConnectionError
from dronesphere.core.logging import get_logger
from dronesphere.core.models import DroneState, Telemetry

logger = get_logger(__name__)


class DroneConnection:
    """Manages connection to a single drone."""

    def __init__(self, drone_id: int, connection_string: str = None):
        self.drone_id = drone_id
        self.connection_string = connection_string or "udp://:14540"
        self.backend: AbstractBackend | None = None
        self.telemetry_provider: TelemetryProvider | None = None
        self.connected = False

    async def connect(self) -> None:
        """Connect to the drone."""
        try:
            logger.info(
                "connecting_to_drone",
                drone_id=self.drone_id,
                connection=self.connection_string,
            )

            # Create backend with all required parameters
            factory = BackendFactory()
            self.backend = factory.create_backend(
                backend_type="mavsdk",
                drone_id=self.drone_id,
                connection_string=self.connection_string,
            )

            # Connect backend
            await self.backend.connect()

            # Create telemetry provider using factory (FIX: Use factory method)
            self.telemetry_provider = factory.create_telemetry_provider(
                provider_type="mavsdk",  # Use MAVSDK telemetry provider
                drone_id=self.drone_id,
                connection_string=self.connection_string,
            )

            # Connect telemetry provider
            await self.telemetry_provider.connect()

            self.connected = True
            logger.info("drone_connected", drone_id=self.drone_id)

        except Exception as e:
            logger.error(
                "drone_connection_failed", drone_id=self.drone_id, error=str(e)
            )
            raise DroneConnectionError(
                f"Failed to connect to drone {self.drone_id}: {e}"
            )

    async def disconnect(self) -> None:
        """Disconnect from the drone."""
        try:
            if self.telemetry_provider:
                await self.telemetry_provider.disconnect()

            if self.backend:
                await self.backend.disconnect()

            self.connected = False
            logger.info("drone_disconnected", drone_id=self.drone_id)

        except Exception as e:
            logger.error(
                "drone_disconnection_error", drone_id=self.drone_id, error=str(e)
            )

    async def get_state(self) -> DroneState:
        """Get current drone state."""
        if not self.backend:
            raise DroneConnectionError("Not connected to drone")

        return await self.backend.get_state()

    async def get_telemetry(self) -> Telemetry | None:
        """Get current telemetry."""
        if not self.telemetry_provider:
            return None

        return await self.telemetry_provider.get_telemetry()

    async def emergency_stop(self) -> None:
        """Execute emergency stop."""
        if not self.backend:
            raise DroneConnectionError("Not connected to drone")

        logger.warning("emergency_stop_initiated", drone_id=self.drone_id)
        await self.backend.emergency_stop()
