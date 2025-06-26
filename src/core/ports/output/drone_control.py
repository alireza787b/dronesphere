"""Drone Control port definitions.

This module defines the interface for controlling drones in the system.
Following hexagonal architecture, this is a pure interface with no implementation.
Supports MAVSDK, ArduPilot, PX4, DJI SDK, and simulator backends.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, AsyncIterator, Dict, Optional, Tuple

from src.core.domain.entities.drone import Drone, DroneState
from src.core.domain.value_objects.battery import BatteryStatus
from src.core.domain.value_objects.command import DroneCommand
from src.core.domain.value_objects.position import Position


class ConnectionType(str, Enum):
    """Types of drone connections."""
    
    SERIAL = "serial"          # Direct serial/USB connection
    TCP = "tcp"                # TCP/IP connection
    UDP = "udp"                # UDP connection
    SIMULATION = "simulation"  # Simulator connection


class TelemetryType(str, Enum):
    """Types of telemetry data."""
    
    POSITION = "position"
    ATTITUDE = "attitude"
    BATTERY = "battery"
    GPS_INFO = "gps_info"
    FLIGHT_MODE = "flight_mode"
    ARMED = "armed"
    IN_AIR = "in_air"
    VELOCITY = "velocity"
    HOME = "home"
    HEALTH = "health"


@dataclass
class TelemetryData:
    """Container for telemetry data."""
    
    type: TelemetryType
    data: Dict[str, Any]
    timestamp: float
    
    def get_position(self) -> Optional[Position]:
        """Extract position from telemetry data."""
        if self.type == TelemetryType.POSITION:
            return Position(
                latitude=self.data["latitude"],
                longitude=self.data["longitude"],
                altitude=self.data["altitude_m"]
            )
        return None
    
    def get_battery(self) -> Optional[BatteryStatus]:
        """Extract battery status from telemetry data."""
        if self.type == TelemetryType.BATTERY:
            return BatteryStatus(
                level=self.data["remaining_percent"],
                voltage=self.data.get("voltage_v", 0.0)
            )
        return None


@dataclass
class CommandResult:
    """Result of executing a drone command."""
    
    success: bool
    command: DroneCommand
    message: Optional[str] = None
    error: Optional[Exception] = None
    execution_time_ms: float = 0.0
    
    @property
    def failed(self) -> bool:
        """Check if command failed."""
        return not self.success


class DroneControlPort(ABC):
    """Port for drone control operations.
    
    This interface defines how the core domain controls physical or simulated drones.
    Implementations can use MAVSDK, ArduPilot, PX4, DJI SDK, or simulators.
    """
    
    @abstractmethod
    async def connect(
        self,
        connection_string: str,
        connection_type: ConnectionType = ConnectionType.UDP
    ) -> bool:
        """Connect to a drone.
        
        Args:
            connection_string: Connection string (e.g., "udp://:14540", "serial:///dev/ttyACM0")
            connection_type: Type of connection
            
        Returns:
            True if connection successful
            
        Raises:
            ConnectionError: If connection fails
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the drone."""
        pass
    
    @abstractmethod
    async def execute_command(
        self,
        command: DroneCommand,
        timeout_seconds: Optional[float] = None
    ) -> CommandResult:
        """Execute a drone command.
        
        Args:
            command: The command to execute
            timeout_seconds: Optional timeout for command execution
            
        Returns:
            CommandResult with execution details
        """
        pass
    
    @abstractmethod
    async def arm(self) -> bool:
        """Arm the drone (enable motors).
        
        Returns:
            True if arming successful
            
        Raises:
            RuntimeError: If arming fails
        """
        pass
    
    @abstractmethod
    async def disarm(self) -> bool:
        """Disarm the drone (disable motors).
        
        Returns:
            True if disarming successful
        """
        pass
    
    @abstractmethod
    async def get_drone_state(self) -> Drone:
        """Get current drone state as domain entity.
        
        Returns:
            Drone entity with current state
        """
        pass
    
    @abstractmethod
    async def get_telemetry_stream(
        self,
        telemetry_types: Optional[list[TelemetryType]] = None
    ) -> AsyncIterator[TelemetryData]:
        """Get async stream of telemetry data.
        
        Args:
            telemetry_types: Types of telemetry to stream (None = all)
            
        Yields:
            TelemetryData objects as they arrive
        """
        pass
    
    @abstractmethod
    async def is_connected(self) -> bool:
        """Check if drone is connected."""
        pass
    
    @abstractmethod
    async def is_armed(self) -> bool:
        """Check if drone is armed."""
        pass
    
    @abstractmethod
    async def is_in_air(self) -> bool:
        """Check if drone is in air."""
        pass
    
    @abstractmethod
    async def get_home_position(self) -> Optional[Position]:
        """Get home position (where drone was armed)."""
        pass
    
    @abstractmethod
    async def set_home_position(self, position: Position) -> bool:
        """Set home position.
        
        Args:
            position: New home position
            
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    async def check_safety(self) -> Tuple[bool, Optional[str]]:
        """Check if it's safe to fly.
        
        Returns:
            Tuple of (is_safe, reason_if_not_safe)
        """
        pass
    
    @abstractmethod
    async def emergency_stop(self, reason: str) -> bool:
        """Execute emergency stop.
        
        Args:
            reason: Reason for emergency stop
            
        Returns:
            True if stop executed
        """
        pass
    
    @property
    @abstractmethod
    def backend_name(self) -> str:
        """Get the name of the control backend."""
        pass
    
    @property
    @abstractmethod
    def supports_simulation(self) -> bool:
        """Check if this backend supports simulation."""
        pass
    
    @property
    @abstractmethod
    def max_altitude_m(self) -> float:
        """Get maximum allowed altitude in meters."""
        pass
    
    @property
    @abstractmethod
    def max_velocity_m_s(self) -> float:
        """Get maximum allowed velocity in m/s."""
        pass