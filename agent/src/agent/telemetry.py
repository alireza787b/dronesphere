# agent/src/agent/telemetry.py
"""
Telemetry Streamer Module

Handles streaming of drone telemetry data to the control server via WebSocket.
Provides real-time updates of drone state including position, battery, and status.
"""

import asyncio
import json
from datetime import datetime
from typing import Any

import structlog
import websockets
from websockets.exceptions import ConnectionClosed

from agent.connection import DroneConnection

logger = structlog.get_logger()


class TelemetryStreamer:
    """
    Streams telemetry data to the control server.

    This class:
    - Collects telemetry from DroneConnection
    - Formats telemetry data
    - Streams to server via WebSocket
    - Handles connection failures gracefully
    """

    def __init__(
        self, drone_connection: DroneConnection, server_url: str, stream_rate: int = 10
    ):
        """
        Initialize telemetry streamer.

        Args:
            drone_connection: DroneConnection instance
            server_url: WebSocket URL for server
            stream_rate: Telemetry update rate in Hz
        """
        self.drone_connection = drone_connection
        self.server_url = server_url.replace(
            "/agent", "/telemetry"
        )  # Use telemetry endpoint
        self.stream_rate = stream_rate
        self.stream_interval = 1.0 / stream_rate
        self._running = False
        self._websocket: websockets.WebSocketClientProtocol | None = None
        self._telemetry_task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start telemetry streaming."""
        self._running = True
        logger.info(
            "Starting TelemetryStreamer",
            server_url=self.server_url,
            rate_hz=self.stream_rate,
        )

        while self._running:
            try:
                await self._connect_and_stream()
            except Exception as e:
                logger.error("TelemetryStreamer error", error=str(e))
                if self._running:
                    logger.info("Reconnecting in 5 seconds...")
                    await asyncio.sleep(5)

    async def _connect_and_stream(self) -> None:
        """Connect to server and stream telemetry."""
        logger.info("Connecting to telemetry endpoint", url=self.server_url)

        async with websockets.connect(self.server_url) as websocket:
            self._websocket = websocket
            logger.info("Connected to telemetry endpoint")

            # Send identification
            await self._send_identification()

            # Start streaming
            await self._stream_telemetry()

    async def _send_identification(self) -> None:
        """Send drone identification to server."""
        identification = {
            "type": "telemetry_source",
            "drone_id": "drone_001",  # TODO: Get from config
            "stream_rate": self.stream_rate,
        }
        await self._websocket.send(json.dumps(identification))

    async def _stream_telemetry(self) -> None:
        """Stream telemetry data to server."""
        try:
            while self._running:
                # Collect telemetry data
                telemetry = await self._collect_telemetry()

                # Send to server
                await self._websocket.send(json.dumps(telemetry))

                # Wait for next update
                await asyncio.sleep(self.stream_interval)

        except ConnectionClosed:
            logger.warning("Telemetry connection closed")
        except Exception as e:
            logger.error("Telemetry streaming error", error=str(e))

    async def _collect_telemetry(self) -> dict[str, Any]:
        """
        Collect current telemetry data.

        Returns:
            Dictionary containing telemetry data
        """
        state = self.drone_connection.state

        # Get additional telemetry if available
        telemetry_data = {
            "type": "telemetry",
            "timestamp": datetime.utcnow().isoformat(),
            "drone_id": "drone_001",
            "flight": {
                "armed": state.armed,
                "is_flying": state.is_flying,
                "mode": state.mode,
            },
            "position": {
                "latitude": state.position[0],
                "longitude": state.position[1],
                "altitude": state.position[2],
                "heading": state.heading,
                "groundspeed": state.groundspeed,
            },
            "battery": {
                "percent": state.battery_percent,
                "voltage": 0.0,  # TODO: Get from telemetry
                "current": 0.0,  # TODO: Get from telemetry
            },
            "gps": {
                "fix": state.gps_fix,
                "satellites": 0,  # TODO: Get from telemetry
            },
            "status": {
                "connected": await self.drone_connection.is_connected(),
                "ready": state.armed or not state.is_flying,
            },
        }

        # Add additional telemetry streams if needed
        try:
            # Try to get more detailed telemetry
            await self._add_detailed_telemetry(telemetry_data)
        except Exception as e:
            logger.debug("Could not get detailed telemetry", error=str(e))

        return telemetry_data

    async def _add_detailed_telemetry(self, telemetry_data: dict[str, Any]) -> None:
        """
        Add detailed telemetry from direct streams.

        Args:
            telemetry_data: Dictionary to update with detailed data
        """
        # This would be implemented with direct telemetry subscriptions
        # For now, we're using the state from connection monitoring
        pass

    async def stop(self) -> None:
        """Stop telemetry streaming and cleanup."""
        logger.info("Stopping TelemetryStreamer")
        self._running = False

        if self._websocket:
            await self._websocket.close()

    def get_stream_stats(self) -> dict[str, Any]:
        """
        Get streaming statistics.

        Returns:
            Dictionary with streaming stats
        """
        return {
            "connected": self._websocket is not None and not self._websocket.closed,
            "stream_rate": self.stream_rate,
            "server_url": self.server_url,
        }
