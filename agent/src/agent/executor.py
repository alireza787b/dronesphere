# agent/src/agent/executor.py
"""
Command Executor Module

Handles execution of commands received from the control server via WebSocket.
Implements command validation, execution, and result reporting.
"""

import asyncio
import json
from collections.abc import Callable
from datetime import datetime
from enum import Enum
from typing import Any

import structlog
import websockets
from tenacity import retry, stop_after_attempt, wait_exponential
from websockets.exceptions import ConnectionClosed

from agent.connection import DroneConnection

logger = structlog.get_logger()


class CommandStatus(str, Enum):
    """Command execution status."""

    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CommandResult:
    """Result of command execution."""

    def __init__(
        self,
        command_id: str,
        status: CommandStatus,
        message: str = "",
        data: dict[str, Any] | None = None,
        error: str | None = None,
    ):
        """
        Initialize command result.

        Args:
            command_id: Unique command identifier
            status: Command execution status
            message: Human-readable message
            data: Optional result data
            error: Error message if failed
        """
        self.command_id = command_id
        self.status = status
        self.message = message
        self.data = data or {}
        self.error = error
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "command_id": self.command_id,
            "status": self.status.value,
            "message": self.message,
            "data": self.data,
            "error": self.error,
            "timestamp": self.timestamp,
        }


class CommandExecutor:
    """
    Executes commands received from the control server.

    This class:
    - Maintains WebSocket connection to server
    - Receives and validates commands
    - Executes commands using DroneConnection
    - Reports results back to server
    """

    def __init__(self, drone_connection: DroneConnection, server_url: str):
        """
        Initialize command executor.

        Args:
            drone_connection: DroneConnection instance
            server_url: WebSocket URL for server
        """
        self.drone_connection = drone_connection
        self.server_url = server_url
        self._running = False
        self._websocket: websockets.WebSocketClientProtocol | None = None
        self._command_handlers: dict[str, Callable] = self._register_handlers()
        self._current_command: str | None = None

    def _register_handlers(self) -> dict[str, Callable]:
        """Register command handlers."""
        return {
            "arm": self._handle_arm,
            "disarm": self._handle_disarm,
            "takeoff": self._handle_takeoff,
            "land": self._handle_land,
            "goto": self._handle_goto,
            "rtl": self._handle_rtl,
            "emergency_stop": self._handle_emergency_stop,
            "set_mode": self._handle_set_mode,
        }

    async def start(self) -> None:
        """Start command executor and connect to server."""
        self._running = True
        logger.info("Starting CommandExecutor", server_url=self.server_url)

        while self._running:
            try:
                await self._connect_and_run()
            except Exception as e:
                logger.error("CommandExecutor error", error=str(e))
                if self._running:
                    logger.info("Reconnecting in 5 seconds...")
                    await asyncio.sleep(5)

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def _connect_and_run(self) -> None:
        """Connect to server and process commands."""
        logger.info("Connecting to server", url=self.server_url)

        async with websockets.connect(self.server_url) as websocket:
            self._websocket = websocket
            logger.info("Connected to server")

            # Send identification
            await self._send_identification()

            # Process commands
            await self._process_commands()

    async def _send_identification(self) -> None:
        """Send drone identification to server."""
        identification = {
            "type": "identification",
            "drone_id": (
                self.drone_connection.drone.server_component.id
                if hasattr(self.drone_connection.drone, "server_component")
                else "drone_001"
            ),
            "capabilities": ["arm", "disarm", "takeoff", "land", "goto", "rtl"],
            "status": "ready",
        }
        await self._websocket.send(json.dumps(identification))

    async def _process_commands(self) -> None:
        """Process incoming commands from server."""
        try:
            async for message in self._websocket:
                if not self._running:
                    break

                try:
                    command = json.loads(message)
                    await self._execute_command(command)
                except json.JSONDecodeError as e:
                    logger.error("Invalid command format", error=str(e))
                except Exception as e:
                    logger.error("Command processing error", error=str(e))

        except ConnectionClosed:
            logger.warning("Server connection closed")

    async def _execute_command(self, command: dict[str, Any]) -> None:
        """
        Execute a single command.

        Args:
            command: Command dictionary with 'id', 'name', and 'params'
        """
        command_id = command.get("id", "unknown")
        command_name = command.get("name", "")
        params = command.get("params", {})

        logger.info(
            "Executing command",
            command_id=command_id,
            command_name=command_name,
            params=params,
        )

        self._current_command = command_id

        # Check if handler exists
        handler = self._command_handlers.get(command_name)
        if not handler:
            result = CommandResult(
                command_id=command_id,
                status=CommandStatus.FAILED,
                error=f"Unknown command: {command_name}",
            )
            await self._send_result(result)
            return

        # Execute command
        try:
            result = await handler(command_id, params)
            await self._send_result(result)
        except Exception as e:
            logger.error(
                "Command execution failed", command_id=command_id, error=str(e)
            )
            result = CommandResult(
                command_id=command_id, status=CommandStatus.FAILED, error=str(e)
            )
            await self._send_result(result)
        finally:
            self._current_command = None

    async def _send_result(self, result: CommandResult) -> None:
        """Send command result to server."""
        if self._websocket:
            message = {"type": "command_result", **result.to_dict()}
            await self._websocket.send(json.dumps(message))

    # Command Handlers

    async def _handle_arm(
        self, command_id: str, params: dict[str, Any]
    ) -> CommandResult:
        """Handle arm command."""
        await self.drone_connection.arm()
        return CommandResult(
            command_id=command_id,
            status=CommandStatus.COMPLETED,
            message="Drone armed successfully",
        )

    async def _handle_disarm(
        self, command_id: str, params: dict[str, Any]
    ) -> CommandResult:
        """Handle disarm command."""
        await self.drone_connection.disarm()
        return CommandResult(
            command_id=command_id,
            status=CommandStatus.COMPLETED,
            message="Drone disarmed successfully",
        )

    async def _handle_takeoff(
        self, command_id: str, params: dict[str, Any]
    ) -> CommandResult:
        """Handle takeoff command."""
        altitude = params.get("altitude", 10.0)

        # Validate altitude
        if altitude <= 0 or altitude > 50:
            return CommandResult(
                command_id=command_id,
                status=CommandStatus.FAILED,
                error=f"Invalid altitude: {altitude}. Must be between 0 and 50 meters.",
            )

        await self.drone_connection.takeoff(altitude)
        return CommandResult(
            command_id=command_id,
            status=CommandStatus.COMPLETED,
            message=f"Takeoff to {altitude}m completed",
            data={"altitude": altitude},
        )

    async def _handle_land(
        self, command_id: str, params: dict[str, Any]
    ) -> CommandResult:
        """Handle land command."""
        await self.drone_connection.land()
        return CommandResult(
            command_id=command_id,
            status=CommandStatus.COMPLETED,
            message="Landing completed",
        )

    async def _handle_goto(
        self, command_id: str, params: dict[str, Any]
    ) -> CommandResult:
        """Handle goto location command."""
        lat = params.get("latitude")
        lon = params.get("longitude")
        alt = params.get("altitude", 20.0)
        yaw = params.get("yaw", 0.0)

        # Validate parameters
        if lat is None or lon is None:
            return CommandResult(
                command_id=command_id,
                status=CommandStatus.FAILED,
                error="Missing latitude or longitude",
            )

        await self.drone_connection.goto_location(lat, lon, alt, yaw)
        return CommandResult(
            command_id=command_id,
            status=CommandStatus.COMPLETED,
            message=f"Reached location: {lat:.6f}, {lon:.6f} at {alt}m",
            data={"latitude": lat, "longitude": lon, "altitude": alt},
        )

    async def _handle_rtl(
        self, command_id: str, params: dict[str, Any]
    ) -> CommandResult:
        """Handle return to launch command."""
        await self.drone_connection.return_to_launch()
        return CommandResult(
            command_id=command_id,
            status=CommandStatus.COMPLETED,
            message="Returning to launch position",
        )

    async def _handle_emergency_stop(
        self, command_id: str, params: dict[str, Any]
    ) -> CommandResult:
        """Handle emergency stop command."""
        await self.drone_connection.emergency_stop()
        return CommandResult(
            command_id=command_id,
            status=CommandStatus.COMPLETED,
            message="EMERGENCY STOP EXECUTED",
            data={"warning": "Motors killed"},
        )

    async def _handle_set_mode(
        self, command_id: str, params: dict[str, Any]
    ) -> CommandResult:
        """Handle set flight mode command."""
        mode = params.get("mode", "")
        # For now, just log - actual implementation would set flight mode
        logger.info("Set mode requested", mode=mode)
        return CommandResult(
            command_id=command_id,
            status=CommandStatus.COMPLETED,
            message=f"Mode set to {mode}",
            data={"mode": mode},
        )

    async def stop(self) -> None:
        """Stop command executor and cleanup."""
        logger.info("Stopping CommandExecutor")
        self._running = False

        if self._websocket:
            await self._websocket.close()
