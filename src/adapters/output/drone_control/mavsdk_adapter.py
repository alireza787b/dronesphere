"""MAVSDK-based drone control adapter implementation.

This module implements the DroneControlPort using MAVSDK for MAVLink communication.
Supports PX4, ArduPilot, and compatible autopilots.
"""

import asyncio
import math
import time
from typing import Any, AsyncIterator, Dict, Optional, Set, Tuple

from mavsdk import System
from mavsdk.action import ActionError
from mavsdk.mission import MissionItem, MissionPlan
from mavsdk.offboard import (
    OffboardError,
    PositionNedYaw,
    VelocityBodyYawspeed,
    VelocityNedYaw,
)

from src.adapters.output.drone_control.base_adapter import BaseDroneAdapter
from src.core.domain.entities.drone import DroneState
from src.core.domain.value_objects.battery import BatteryStatus
from src.core.domain.value_objects.command import (
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
    TelemetryData,
    TelemetryType,
)


class MAVSDKAdapter(BaseDroneAdapter):
    """MAVSDK implementation of drone control.
    
    Uses MAVSDK Python library to communicate with PX4/ArduPilot drones
    via MAVLink protocol.
    """
    
    def __init__(self):
        """Initialize MAVSDK adapter."""
        super().__init__()
        self._drone: Optional[System] = None
        self._telemetry_tasks: Set[asyncio.Task] = set()
        self._offboard_active = False
        
    @property
    def backend_name(self) -> str:
        """Get backend name."""
        return "MAVSDK"
    
    @property
    def supports_simulation(self) -> bool:
        """MAVSDK supports both real and simulated drones."""
        return True
    
    async def connect(
        self,
        connection_string: str,
        connection_type: ConnectionType = ConnectionType.UDP
    ) -> bool:
        """Connect to drone via MAVSDK."""
        try:
            self._drone = System()
            
            # Parse connection string and connect
            if connection_type == ConnectionType.UDP:
                await self._drone.connect(system_address=connection_string)
            elif connection_type == ConnectionType.SERIAL:
                await self._drone.connect(system_address=connection_string)
            elif connection_type == ConnectionType.TCP:
                await self._drone.connect(system_address=connection_string)
            else:
                await self._drone.connect()  # Default connection
            
            # Wait for connection
            async for state in self._drone.core.connection_state():
                if state.is_connected:
                    self._connected = True
                    break
            
            # Start telemetry streams
            await self._start_telemetry_streams()
            
            return True
            
        except Exception as e:
            raise ConnectionError(f"Failed to connect: {str(e)}")
    
    async def disconnect(self) -> None:
        """Disconnect from drone."""
        # Cancel telemetry tasks
        for task in self._telemetry_tasks:
            task.cancel()
        self._telemetry_tasks.clear()
        
        self._connected = False
        self._drone = None
    
    async def arm(self) -> bool:
        """Arm the drone."""
        if not self._connected:
            raise RuntimeError("Drone not connected")
        
        try:
            await self._drone.action.arm()
            self._armed = True
            
            # Set home position when arming
            if self._current_position:
                self._home_position = self._current_position
                
            return True
            
        except ActionError as e:
            raise RuntimeError(f"Failed to arm: {str(e)}")
    
    async def disarm(self) -> bool:
        """Disarm the drone."""
        if not self._connected:
            return False
        
        try:
            await self._drone.action.disarm()
            self._armed = False
            return True
        except:
            return False
    
    async def is_connected(self) -> bool:
        """Check connection status."""
        return self._connected
    
    async def is_armed(self) -> bool:
        """Check armed status."""
        return self._armed
    
    async def is_in_air(self) -> bool:
        """Check if drone is flying."""
        return self._in_air
    
    async def get_home_position(self) -> Optional[Position]:
        """Get home position."""
        return self._home_position
    
    async def set_home_position(self, position: Position) -> bool:
        """Set home position."""
        if not self._connected:
            return False
        
        try:
            await self._drone.action.set_return_to_launch_altitude(position.altitude)
            # Note: MAVSDK doesn't directly support setting home lat/lon
            # This would need to be done via MAVLink command
            self._home_position = position
            return True
        except:
            return False
    
    async def emergency_stop(self, reason: str) -> bool:
        """Execute emergency stop."""
        if not self._connected:
            return False
        
        try:
            # First try to kill motors
            await self._drone.action.kill()
            return True
        except:
            try:
                # If kill fails, try emergency land
                await self._drone.action.land()
                return True
            except:
                return False
    
    async def get_telemetry_stream(
        self,
        telemetry_types: Optional[list[TelemetryType]] = None
    ) -> AsyncIterator[TelemetryData]:
        """Get telemetry data stream."""
        # If no types specified, stream all
        if telemetry_types is None:
            telemetry_types = list(TelemetryType)
        
        # Create queue for telemetry data
        queue = asyncio.Queue()
        
        # Start tasks for requested telemetry types
        tasks = []
        if TelemetryType.POSITION in telemetry_types:
            tasks.append(self._stream_position(queue))
        if TelemetryType.BATTERY in telemetry_types:
            tasks.append(self._stream_battery(queue))
        if TelemetryType.ATTITUDE in telemetry_types:
            tasks.append(self._stream_attitude(queue))
        
        # Start all tasks
        for task in tasks:
            asyncio.create_task(task)
        
        # Yield data from queue
        while True:
            data = await queue.get()
            yield data
    
    async def _start_telemetry_streams(self) -> None:
        """Start internal telemetry streams."""
        # Position telemetry
        self._telemetry_tasks.add(
            asyncio.create_task(self._monitor_position())
        )
        
        # Battery telemetry
        self._telemetry_tasks.add(
            asyncio.create_task(self._monitor_battery())
        )
        
        # Armed state telemetry
        self._telemetry_tasks.add(
            asyncio.create_task(self._monitor_armed_state())
        )
        
        # In-air state telemetry
        self._telemetry_tasks.add(
            asyncio.create_task(self._monitor_in_air_state())
        )
    
    async def _monitor_position(self) -> None:
        """Monitor position updates."""
        async for position in self._drone.telemetry.position():
            self._current_position = Position(
                latitude=position.latitude_deg,
                longitude=position.longitude_deg,
                altitude=position.relative_altitude_m
            )
    
    async def _monitor_battery(self) -> None:
        """Monitor battery updates."""
        async for battery in self._drone.telemetry.battery():
            self._current_battery = BatteryStatus(
                level=int(battery.remaining_percent * 100),
                voltage=battery.voltage_v
            )
    
    async def _monitor_armed_state(self) -> None:
        """Monitor armed state."""
        async for is_armed in self._drone.telemetry.armed():
            self._armed = is_armed
    
    async def _monitor_in_air_state(self) -> None:
        """Monitor in-air state."""
        async for in_air in self._drone.telemetry.in_air():
            self._in_air = in_air
    
    async def _stream_position(self, queue: asyncio.Queue) -> None:
        """Stream position data to queue."""
        async for position in self._drone.telemetry.position():
            data = TelemetryData(
                type=TelemetryType.POSITION,
                data={
                    "latitude": position.latitude_deg,
                    "longitude": position.longitude_deg,
                    "altitude_m": position.relative_altitude_m,
                    "absolute_altitude_m": position.absolute_altitude_m
                },
                timestamp=time.time()
            )
            await queue.put(data)
    
    async def _stream_battery(self, queue: asyncio.Queue) -> None:
        """Stream battery data to queue."""
        async for battery in self._drone.telemetry.battery():
            data = TelemetryData(
                type=TelemetryType.BATTERY,
                data={
                    "remaining_percent": battery.remaining_percent * 100,
                    "voltage_v": battery.voltage_v
                },
                timestamp=time.time()
            )
            await queue.put(data)
    
    async def _stream_attitude(self, queue: asyncio.Queue) -> None:
        """Stream attitude data to queue."""
        async for attitude in self._drone.telemetry.attitude_euler():
            data = TelemetryData(
                type=TelemetryType.ATTITUDE,
                data={
                    "roll_deg": attitude.roll_deg,
                    "pitch_deg": attitude.pitch_deg,
                    "yaw_deg": attitude.yaw_deg
                },
                timestamp=time.time()
            )
            await queue.put(data)
    
    # Command execution methods
    
    async def _execute_takeoff(self, command: TakeoffCommand) -> CommandResult:
        """Execute takeoff command."""
        try:
            # Set takeoff altitude
            await self._drone.action.set_takeoff_altitude(command.target_altitude)
            
            # Execute takeoff
            await self._drone.action.takeoff()
            
            return CommandResult(
                success=True,
                command=command,
                message=f"Taking off to {command.target_altitude}m"
            )
            
        except ActionError as e:
            return CommandResult(
                success=False,
                command=command,
                message=f"Takeoff failed: {str(e)}",
                error=e
            )
    
    async def _execute_land(self, command: LandCommand) -> CommandResult:
        """Execute land command."""
        try:
            await self._drone.action.land()
            
            return CommandResult(
                success=True,
                command=command,
                message="Landing"
            )
            
        except ActionError as e:
            return CommandResult(
                success=False,
                command=command,
                message=f"Landing failed: {str(e)}",
                error=e
            )
    
    async def _execute_move(self, command: MoveCommand) -> CommandResult:
        """Execute relative movement command."""
        try:
            # Get current position
            position = None
            async for pos in self._drone.telemetry.position():
                position = pos
                break
            
            if not position:
                raise RuntimeError("Could not get current position")
            
            # Calculate NED coordinates (North-East-Down)
            # Note: NED uses Down as positive, so we negate up_m
            north_m = command.forward_m
            east_m = command.right_m
            down_m = -command.up_m
            
            # Get current yaw
            attitude = None
            async for att in self._drone.telemetry.attitude_euler():
                attitude = att
                break
            
            current_yaw = attitude.yaw_deg if attitude else 0
            new_yaw = current_yaw + command.rotate_deg
            
            # Use offboard mode for precise control
            await self._drone.offboard.set_position_ned(
                PositionNedYaw(north_m, east_m, down_m, new_yaw)
            )
            
            # Start offboard mode
            await self._drone.offboard.start()
            self._offboard_active = True
            
            # Wait a bit for movement
            await asyncio.sleep(2)
            
            # Stop offboard mode
            await self._drone.offboard.stop()
            self._offboard_active = False
            
            return CommandResult(
                success=True,
                command=command,
                message=f"Moved: forward={command.forward_m}m, right={command.right_m}m, up={command.up_m}m, rotate={command.rotate_deg}°"
            )
            
        except Exception as e:
            if self._offboard_active:
                try:
                    await self._drone.offboard.stop()
                except:
                    pass
            
            return CommandResult(
                success=False,
                command=command,
                message=f"Movement failed: {str(e)}",
                error=e
            )
    
    async def _execute_goto(self, command: GoToCommand) -> CommandResult:
        """Execute go-to position command."""
        try:
            # Convert to absolute altitude if needed
            absolute_altitude = command.target_position.altitude
            
            # Fly to position
            await self._drone.action.goto_location(
                command.target_position.latitude,
                command.target_position.longitude,
                absolute_altitude,
                0  # yaw angle
            )
            
            return CommandResult(
                success=True,
                command=command,
                message=f"Flying to {command.target_position}"
            )
            
        except ActionError as e:
            return CommandResult(
                success=False,
                command=command,
                message=f"Go-to failed: {str(e)}",
                error=e
            )
    
    async def _execute_orbit(self, command: OrbitCommand) -> CommandResult:
        """Execute orbit command."""
        try:
            # MAVSDK orbit parameters
            radius = command.radius_m
            velocity = command.velocity_m_s
            yaw_behavior = 0  # 0 = pointing to center
            latitude = command.center.latitude
            longitude = command.center.longitude
            absolute_altitude = command.center.altitude
            
            # Start orbit
            # Note: orbit direction is determined by velocity sign
            if not command.clockwise:
                velocity = -velocity
            
            await self._drone.action.do_orbit(
                radius,
                velocity,
                yaw_behavior,
                latitude,
                longitude,
                absolute_altitude
            )
            
            message = f"Orbiting at {command.radius_m}m radius"
            if command.orbits:
                message += f" for {command.orbits} orbits"
                # Calculate orbit time and schedule stop
                orbit_time = (2 * math.pi * radius / abs(velocity)) * command.orbits
                asyncio.create_task(self._stop_orbit_after(orbit_time))
            
            return CommandResult(
                success=True,
                command=command,
                message=message
            )
            
        except ActionError as e:
            return CommandResult(
                success=False,
                command=command,
                message=f"Orbit failed: {str(e)}",
                error=e
            )
    
    async def _stop_orbit_after(self, seconds: float) -> None:
        """Stop orbit after specified time."""
        await asyncio.sleep(seconds)
        try:
            # Return to normal flight mode
            await self._drone.action.hold()
        except:
            pass
    
    async def _execute_return_home(self, command: ReturnHomeCommand) -> CommandResult:
        """Execute return to home command."""
        try:
            await self._drone.action.return_to_launch()
            
            return CommandResult(
                success=True,
                command=command,
                message="Returning to home position"
            )
            
        except ActionError as e:
            return CommandResult(
                success=False,
                command=command,
                message=f"Return home failed: {str(e)}",
                error=e
            )
    
    async def _execute_emergency_stop(self, command: EmergencyStopCommand) -> CommandResult:
        """Execute emergency stop command."""
        success = await self.emergency_stop(command.reason)
        
        return CommandResult(
            success=success,
            command=command,
            message="Emergency stop executed" if success else "Emergency stop failed"
        )