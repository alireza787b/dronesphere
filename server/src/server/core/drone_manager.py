# server/src/server/core/drone_manager.py
"""
Drone Manager

Manages drone connections, sessions, and communication.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import structlog
from fastapi import WebSocket

logger = structlog.get_logger()


@dataclass
class DroneSession:
    """Represents a connected drone session."""

    drone_id: str
    websocket: WebSocket
    connected_at: datetime = field(default_factory=datetime.utcnow)
    capabilities: list = field(default_factory=list)
    status: str = "connected"
    last_telemetry: dict[str, Any] | None = None


@dataclass
class ClientSession:
    """Represents a connected client session."""

    client_id: str
    websocket: WebSocket
    connected_at: datetime = field(default_factory=datetime.utcnow)
    subscribed_drones: set[str] = field(default_factory=set)


class DroneManager:
    """
    Manages all drone and client connections.

    Singleton class that tracks:
    - Connected drones
    - Connected clients
    - Telemetry subscriptions
    - Command routing
    """

    _instance = None

    def __new__(cls):
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize drone manager."""
        if self._initialized:
            return

        self.drones: dict[str, DroneSession] = {}
        self.clients: dict[str, ClientSession] = {}
        self.pending_commands: dict[str, asyncio.Future] = {}
        self._initialized = True

    async def register_drone(self, drone_id: str, websocket: WebSocket) -> DroneSession:
        """
        Register a new drone connection.

        Args:
            drone_id: Unique drone identifier
            websocket: WebSocket connection

        Returns:
            DroneSession instance
        """
        session = DroneSession(drone_id=drone_id, websocket=websocket)
        self.drones[drone_id] = session

        # Notify clients
        await self._broadcast_drone_status(drone_id, "connected")

        logger.info("Drone registered", drone_id=drone_id)
        return session

    async def unregister_drone(self, drone_id: str) -> None:
        """
        Unregister a drone connection.

        Args:
            drone_id: Drone identifier
        """
        if drone_id in self.drones:
            del self.drones[drone_id]

            # Notify clients
            await self._broadcast_drone_status(drone_id, "disconnected")

            logger.info("Drone unregistered", drone_id=drone_id)

    async def register_client(
        self, client_id: str, websocket: WebSocket
    ) -> ClientSession:
        """
        Register a new client connection.

        Args:
            client_id: Unique client identifier
            websocket: WebSocket connection

        Returns:
            ClientSession instance
        """
        session = ClientSession(client_id=client_id, websocket=websocket)
        self.clients[client_id] = session

        logger.info("Client registered", client_id=client_id)
        return session

    async def unregister_client(self, client_id: str) -> None:
        """
        Unregister a client connection.

        Args:
            client_id: Client identifier
        """
        if client_id in self.clients:
            del self.clients[client_id]
            logger.info("Client unregistered", client_id=client_id)

    async def send_command(
        self, drone_id: str, command: dict[str, Any], timeout: int = 30
    ) -> dict[str, Any]:
        """
        Send command to drone and wait for result.

        Args:
            drone_id: Target drone ID
            command: Command dictionary
            timeout: Command timeout in seconds

        Returns:
            Command result

        Raises:
            ValueError: If drone not connected
            asyncio.TimeoutError: If command times out
        """
        if drone_id not in self.drones:
            raise ValueError(f"Drone {drone_id} not connected")

        drone = self.drones[drone_id]
        command_id = command.get("id", f"cmd_{id(command)}")

        # Create future for result
        future = asyncio.Future()
        self.pending_commands[command_id] = future

        try:
            # Send command
            await drone.websocket.send_json(command)

            # Wait for result
            result = await asyncio.wait_for(future, timeout=timeout)
            return result

        finally:
            # Cleanup
            self.pending_commands.pop(command_id, None)

    async def handle_command_result(
        self, drone_id: str, result: dict[str, Any]
    ) -> None:
        """
        Handle command result from drone.

        Args:
            drone_id: Source drone ID
            result: Command result
        """
        command_id = result.get("command_id")

        if command_id and command_id in self.pending_commands:
            future = self.pending_commands[command_id]
            if not future.done():
                future.set_result(result)

        # Also broadcast to interested clients
        await self._broadcast_to_clients(
            {"type": "command_result", "drone_id": drone_id, "result": result}
        )

    async def broadcast_telemetry(
        self, drone_id: str, telemetry: dict[str, Any]
    ) -> None:
        """
        Broadcast telemetry to subscribed clients.

        Args:
            drone_id: Source drone ID
            telemetry: Telemetry data
        """
        # Update drone's last telemetry
        if drone_id in self.drones:
            self.drones[drone_id].last_telemetry = telemetry

        # Broadcast to subscribed clients
        message = {"type": "telemetry", "drone_id": drone_id, "data": telemetry}

        for client in self.clients.values():
            if drone_id in client.subscribed_drones:
                try:
                    await client.websocket.send_json(message)
                except Exception as e:
                    logger.error(
                        "Failed to send telemetry to client",
                        client_id=client.client_id,
                        error=str(e),
                    )

    async def subscribe_client_to_drone(self, client_id: str, drone_id: str) -> None:
        """
        Subscribe client to drone telemetry.

        Args:
            client_id: Client ID
            drone_id: Drone ID to subscribe to
        """
        if client_id in self.clients:
            self.clients[client_id].subscribed_drones.add(drone_id)
            logger.info(
                "Client subscribed to drone", client_id=client_id, drone_id=drone_id
            )

    async def unsubscribe_client_from_drone(
        self, client_id: str, drone_id: str
    ) -> None:
        """
        Unsubscribe client from drone telemetry.

        Args:
            client_id: Client ID
            drone_id: Drone ID to unsubscribe from
        """
        if client_id in self.clients:
            self.clients[client_id].subscribed_drones.discard(drone_id)
            logger.info(
                "Client unsubscribed from drone", client_id=client_id, drone_id=drone_id
            )

    async def get_system_state(self) -> dict[str, Any]:
        """
        Get current system state.

        Returns:
            Dictionary with system state
        """
        return {
            "drones": {
                drone_id: {
                    "id": drone_id,
                    "status": session.status,
                    "connected_at": session.connected_at.isoformat(),
                    "capabilities": session.capabilities,
                    "last_telemetry": session.last_telemetry,
                }
                for drone_id, session in self.drones.items()
            },
            "clients": len(self.clients),
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def _broadcast_drone_status(self, drone_id: str, status: str) -> None:
        """Broadcast drone status change to all clients."""
        message = {
            "type": "drone_status",
            "drone_id": drone_id,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
        }

        await self._broadcast_to_clients(message)

    async def _broadcast_to_clients(self, message: dict[str, Any]) -> None:
        """Broadcast message to all connected clients."""
        disconnected_clients = []

        for client_id, client in self.clients.items():
            try:
                await client.websocket.send_json(message)
            except Exception as e:
                logger.error(
                    "Failed to broadcast to client", client_id=client_id, error=str(e)
                )
                disconnected_clients.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected_clients:
            await self.unregister_client(client_id)
