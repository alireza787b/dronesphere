# dronesphere/core/models.py
# ================================

"""Core Pydantic models for DroneSphere."""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, validator


class DroneState(str, Enum):
    """Drone operational states."""
    
    DISCONNECTED = "disconnected"
    CONNECTED = "connected" 
    ARMED = "armed"
    DISARMED = "disarmed"
    TAKEOFF = "takeoff"
    FLYING = "flying"
    LANDING = "landing"
    EMERGENCY = "emergency"


class CommandStatus(str, Enum):
    """Command execution status."""
    
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class FlightMode(str, Enum):
    """PX4 flight modes."""
    
    MANUAL = "manual"
    ACRO = "acro"
    ALTCTL = "altitude_control"
    POSCTL = "position_control"
    AUTO_LOITER = "auto_loiter"
    AUTO_RTL = "auto_rtl"
    AUTO_MISSION = "auto_mission"
    AUTO_TAKEOFF = "auto_takeoff"
    AUTO_LAND = "auto_land"
    OFFBOARD = "offboard"


class Position(BaseModel):
    """3D position with coordinate system."""
    
    latitude: Optional[float] = Field(None, description="Latitude in degrees")
    longitude: Optional[float] = Field(None, description="Longitude in degrees")
    altitude_msl: Optional[float] = Field(None, description="Altitude MSL in meters")
    altitude_relative: Optional[float] = Field(None, description="Relative altitude in meters")
    
    # Local coordinates (NED frame)
    north: Optional[float] = Field(None, description="North position in meters")
    east: Optional[float] = Field(None, description="East position in meters") 
    down: Optional[float] = Field(None, description="Down position in meters")


class Attitude(BaseModel):
    """Drone attitude (orientation)."""
    
    roll: float = Field(description="Roll angle in radians")
    pitch: float = Field(description="Pitch angle in radians")
    yaw: float = Field(description="Yaw angle in radians")
    
    # Angular velocities
    roll_rate: Optional[float] = Field(None, description="Roll rate in rad/s")
    pitch_rate: Optional[float] = Field(None, description="Pitch rate in rad/s") 
    yaw_rate: Optional[float] = Field(None, description="Yaw rate in rad/s")


class Velocity(BaseModel):
    """Velocity in different frames."""
    
    # Ground velocity
    ground_speed: Optional[float] = Field(None, description="Ground speed in m/s")
    air_speed: Optional[float] = Field(None, description="Air speed in m/s")
    
    # NED frame velocities
    north: Optional[float] = Field(None, description="North velocity in m/s")
    east: Optional[float] = Field(None, description="East velocity in m/s")
    down: Optional[float] = Field(None, description="Down velocity in m/s")


class Battery(BaseModel):
    """Battery information."""
    
    voltage: Optional[float] = Field(None, description="Battery voltage in V")
    current: Optional[float] = Field(None, description="Battery current in A")
    remaining_percent: Optional[float] = Field(None, description="Remaining charge %")
    remaining_time: Optional[int] = Field(None, description="Remaining time in seconds")


class GPS(BaseModel):
    """GPS information."""
    
    fix_type: Optional[int] = Field(None, description="GPS fix type")
    satellites_visible: Optional[int] = Field(None, description="Visible satellites")
    hdop: Optional[float] = Field(None, description="Horizontal dilution of precision")
    vdop: Optional[float] = Field(None, description="Vertical dilution of precision")


class Telemetry(BaseModel):
    """Complete telemetry data."""
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    drone_id: int = Field(description="Drone identifier")
    
    # Core data
    state: DroneState = Field(description="Current drone state")
    flight_mode: Optional[FlightMode] = Field(None, description="Current flight mode")
    armed: bool = Field(default=False, description="Armed status")
    
    # Position and motion
    position: Optional[Position] = Field(None, description="Current position")
    attitude: Optional[Attitude] = Field(None, description="Current attitude")
    velocity: Optional[Velocity] = Field(None, description="Current velocity")
    
    # System status
    battery: Optional[Battery] = Field(None, description="Battery information")
    gps: Optional[GPS] = Field(None, description="GPS information")
    
    # Health indicators
    health_all_ok: bool = Field(default=True, description="Overall health status")
    calibration_ok: bool = Field(default=True, description="Calibration status")
    
    # Connection
    connection_ok: bool = Field(default=True, description="Connection status")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CommandParameter(BaseModel):
    """Command parameter specification."""
    
    type: str = Field(description="Parameter type (float, int, str, bool)")
    default: Optional[Any] = Field(None, description="Default value")
    constraints: Optional[Dict[str, Any]] = Field(None, description="Parameter constraints")
    description: Optional[str] = Field(None, description="Parameter description")
    unit: Optional[str] = Field(None, description="Parameter unit")


class CommandImplementation(BaseModel):
    """Command implementation details."""
    
    handler: str = Field(description="Python import path to command handler")
    supported_backends: List[str] = Field(description="Supported backend types")
    timeout: int = Field(default=60, description="Command timeout in seconds")


class CommandMetadata(BaseModel):
    """Command metadata."""
    
    name: str = Field(description="Command name (slug)")
    version: str = Field(description="Command version")
    category: str = Field(description="Command category")
    tags: List[str] = Field(default_factory=list, description="Command tags")


class CommandDescription(BaseModel):
    """Command description."""
    
    brief: str = Field(description="Brief description")
    detailed: Optional[str] = Field(None, description="Detailed description")


class TelemetryFeedback(BaseModel):
    """Telemetry feedback messages."""
    
    start: Optional[str] = Field(None, description="Command start message")
    success: Optional[str] = Field(None, description="Command success message")
    error: Optional[str] = Field(None, description="Command error message")


class CommandSpec(BaseModel):
    """Complete command specification from YAML."""
    
    apiVersion: str = Field(description="API version")
    kind: str = Field(description="Resource kind")
    metadata: CommandMetadata = Field(description="Command metadata")
    
    spec: Dict[str, Any] = Field(description="Command specification")
    
    @validator("kind")
    def validate_kind(cls, v):
        """Ensure kind is DroneCommand."""
        if v != "DroneCommand":
            raise ValueError("kind must be 'DroneCommand'")
        return v


class CommandRequest(BaseModel):
    """Single command request."""
    
    name: str = Field(description="Command name")
    params: Dict[str, Any] = Field(default_factory=dict, description="Command parameters")


class CommandSequence(BaseModel):
    """Sequence of commands to execute."""
    
    sequence: List[CommandRequest] = Field(description="Commands to execute in order")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Sequence metadata")


class CommandResult(BaseModel):
    """Result of command execution."""
    
    success: bool = Field(description="Whether command succeeded")
    message: Optional[str] = Field(None, description="Result message")
    data: Optional[Dict[str, Any]] = Field(None, description="Result data")
    duration: Optional[float] = Field(None, description="Execution duration in seconds")
    error: Optional[str] = Field(None, description="Error message if failed")


class CommandEnvelope(BaseModel):
    """Command envelope for internal processing."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique command ID")
    drone_id: int = Field(description="Target drone ID")
    sequence: List[CommandRequest] = Field(description="Commands to execute")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    priority: int = Field(default=0, description="Command priority")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CommandExecution(BaseModel):
    """Active command execution state."""
    
    id: str = Field(description="Command execution ID")
    command: CommandRequest = Field(description="Command being executed")
    status: CommandStatus = Field(description="Execution status")
    progress: float = Field(default=0.0, description="Execution progress (0-1)")
    started_at: Optional[datetime] = Field(None, description="Start time")
    completed_at: Optional[datetime] = Field(None, description="Completion time")
    result: Optional[CommandResult] = Field(None, description="Execution result")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DroneStatus(BaseModel):
    """Complete drone status."""
    
    drone_id: int = Field(description="Drone identifier")
    state: DroneState = Field(description="Current operational state")
    current_command: Optional[CommandExecution] = Field(None, description="Currently executing command")
    queue_length: int = Field(default=0, description="Number of queued commands")
    last_telemetry: Optional[datetime] = Field(None, description="Last telemetry update")
    health_status: str = Field(default="ok", description="Health status")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class APIResponse(BaseModel):
    """Standard API response format."""
    
    success: bool = Field(description="Request success status")
    message: Optional[str] = Field(None, description="Response message")
    data: Optional[Any] = Field(None, description="Response data")
    errors: Optional[List[str]] = Field(None, description="Error list")
    
    
class CommandAcceptedResponse(APIResponse):
    """Response for accepted command."""
    
    command_id: str = Field(description="Assigned command ID")
    estimated_duration: Optional[int] = Field(None, description="Estimated duration in seconds")
