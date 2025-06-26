"""Base adapter class for drone control implementations.

Provides common functionality for all drone control adapters.
"""

import asyncio
import time
from abc import abstractmethod
from typing import Any, AsyncIterator, Dict, Optional, Set, Tuple

from src.core.domain.entities.drone import Drone, DroneState
from src.core.domain.value_objects.battery import BatteryStatus
from src.core.domain.value_objects.command import (
    CommandType,
    DroneCommand,
    EmergencyStopCommand,
    GoToCommand,
    LandCommand,
    MoveCommand,
    OrbitCommand,
    ReturnHomeCommand,
    TakeoffCommand,
)
from src.core.domain.value_objects.position import Position
from src.core.ports.output.drone_control import (
    CommandResult,
    ConnectionType,
    DroneControlPort,
    TelemetryData,
    TelemetryType,
)


class BaseDroneAdapter(DroneControlPort):
    """Base implementation of drone control adapter.
    
    Provides common functionality like command routing, safety checks,
    and telemetry management.
    """
    
    def __init__(self):
        """Initialize base adapter."""
        self._connected = False
        self._armed = False
        self._in_air = False
        self._home_position: Optional[Position] = None
        self._current_position: Optional[Position] = None
        self._current_battery: Optional[BatteryStatus] = None
        self._telemetry_handlers: Dict[TelemetryType, Set[callable]] = {}
        self._command_timeout = 30.0  # Default timeout
        
    async def execute_command(
        self,
        command: DroneCommand,
        timeout_seconds: Optional[float] = None
    ) -> CommandResult:
        """Execute a drone command with routing to specific handlers."""
        start_time = time.time()
        timeout = timeout_seconds or self._command_timeout
        
        try:
            # Validate command first
            command.validate()
            
            # Route to specific command handler
            handlers = {
                CommandType.TAKEOFF: self._execute_takeoff,
                CommandType.LAND: self._execute_land,
                CommandType.MOVE: self._execute_move,
                CommandType.GO_TO: self._execute_goto,
                CommandType.ORBIT: self._execute_orbit,
                CommandType.RETURN_HOME: self._execute_return_home,
                CommandType.EMERGENCY_STOP: self._execute_emergency_stop,
            }
            
            handler = handlers.get(command.command_type)
            if not handler:
                return CommandResult(
                    success=False,
                    command=command,
                    message=f"Command type {command.command_type} not implemented"
                )
            
            # Execute with timeout
            result = await asyncio.wait_for(
                handler(command),
                timeout=timeout
            )
            
            # Add execution time
            result.execution_time_ms = (time.time() - start_time) * 1000
            return result
            
        except asyncio.TimeoutError:
            return CommandResult(
                success=False,
                command=command,
                message=f"Command timed out after {timeout} seconds",
                execution_time_ms=(time.time() - start_time) * 1000
            )
        except Exception as e:
            return CommandResult(
                success=False,
                command=command,
                message=str(e),
                error=e,
                execution_time_ms=(time.time() - start_time) * 1000
            )
    
    async def check_safety(self) -> Tuple[bool, Optional[str]]:
        """Perform safety checks before operations."""
        if not self._connected:
            return False, "Drone not connected"
        
        if self._current_battery and self._current_battery.level < 20:
            return False, f"Battery too low: {self._current_battery.level}%"
        
        # Subclasses can add more checks
        return True, None
    
    async def get_drone_state(self) -> Drone:
        """Get current drone state as domain entity."""
        # Map internal state to domain state
        if not self._connected:
            state = DroneState.DISCONNECTED
        elif not self._armed:
            state = DroneState.DISARMED
        elif self._armed and not self._in_air:
            state = DroneState.ARMED
        elif self._in_air:
            state = DroneState.FLYING
        else:
            state = DroneState.UNKNOWN
        
        return Drone(
            drone_id="drone_1",  # TODO: Get from actual drone
            state=state,
            position=self._current_position,
            battery=self._current_battery,
            home_position=self._home_position
        )
    
    @property
    def max_altitude_m(self) -> float:
        """Default max altitude."""
        return 120.0  # Standard recreational limit
    
    @property
    def max_velocity_m_s(self) -> float:
        """Default max velocity."""
        return 15.0  # Conservative default
    
    # Abstract methods that subclasses must implement
    @abstractmethod
    async def _execute_takeoff(self, command: TakeoffCommand) -> CommandResult:
        """Execute takeoff command."""
        pass
    
    @abstractmethod
    async def _execute_land(self, command: LandCommand) -> CommandResult:
        """Execute land command."""
        pass
    
    @abstractmethod
    async def _execute_move(self, command: MoveCommand) -> CommandResult:
        """Execute move command."""
        pass
    
    @abstractmethod
    async def _execute_goto(self, command: GoToCommand) -> CommandResult:
        """Execute go-to command."""
        pass
    
    @abstractmethod
    async def _execute_orbit(self, command: OrbitCommand) -> CommandResult:
        """Execute orbit command."""
        pass
    
    @abstractmethod
    async def _execute_return_home(self, command: ReturnHomeCommand) -> CommandResult:
        """Execute return home command."""
        pass
    
    @abstractmethod
    async def _execute_emergency_stop(self, command: EmergencyStopCommand) -> CommandResult:
        """Execute emergency stop command."""
        pass