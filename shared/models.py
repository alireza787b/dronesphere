"""Shared data models for DroneSphere.

This module defines the universal data structures used across all components
of the DroneSphere system. These models ensure consistent communication
between the web interface, server, and drone agents.

Path: shared/models.py
"""
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class CommandMode(str, Enum):
    """Execution mode for individual commands.

    - CRITICAL: Failure triggers emergency RTL
    - CONTINUE: Failure continues to next command (default)
    - SKIP: Failure skips to next command
    """

    CRITICAL = "critical"
    CONTINUE = "continue"
    SKIP = "skip"


class QueueMode(str, Enum):
    """Queue handling mode for command sequences.

    - OVERRIDE: New commands replace current sequence (default)
    - APPEND: New commands add to existing queue
    """

    OVERRIDE = "override"
    APPEND = "append"


@dataclass
class Command:
    """Individual drone command with parameters and execution mode.

    Attributes:
        name: Command identifier (e.g., 'takeoff', 'goto', 'land')
        params: Command-specific parameters as key-value pairs
        mode: Execution mode determining failure behavior
    """

    name: str
    params: Dict[str, Any]
    mode: CommandMode = CommandMode.CONTINUE


@dataclass
class CommandRequest:
    """Complete command request for drone operations.

    This is the universal protocol used by all system components.
    Same format whether sending to server or directly to agent.

    Attributes:
        commands: Sequence of commands to execute
        queue_mode: How to handle existing command queue
        target_drone: Specific drone ID (required for server, optional for agent)
    """

    commands: List[Command]
    queue_mode: QueueMode = QueueMode.OVERRIDE
    target_drone: Optional[int] = None


@dataclass
class CommandResult:
    """Result of executing a single command.

    Attributes:
        success: Whether command completed successfully
        message: Human-readable result description
        error: Error identifier for programmatic handling
        duration: Command execution time in seconds
    """

    success: bool
    message: str
    error: Optional[str] = None
    duration: Optional[float] = None


@dataclass
class TelemetryData:
    """Current drone telemetry information.

    Standardized telemetry format across all drone types and backends.
    """

    timestamp: float
    position: Dict[str, float]  # lat, lon, alt, relative_alt
    attitude: Dict[str, float]  # roll, pitch, yaw
    battery: Dict[str, float]  # voltage, remaining_percent
    armed: bool
    flight_mode: str
    connected: bool
