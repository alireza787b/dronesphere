# dronesphere/core/models.py
# ================================

"""Core Pydantic models for DroneSphere."""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

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

    latitude: float | None = Field(None, description="Latitude in degrees")
    longitude: float | None = Field(None, description="Longitude in degrees")
    altitude_msl: float | None = Field(None, description="Altitude MSL in meters")
    altitude_relative: float | None = Field(
        None, description="Relative altitude in meters"
    )

    # Local coordinates (NED frame)
    north: float | None = Field(None, description="North position in meters")
    east: float | None = Field(None, description="East position in meters")
    down: float | None = Field(None, description="Down position in meters")


class Attitude(BaseModel):
    """Drone attitude (orientation)."""

    roll: float = Field(description="Roll angle in radians")
    pitch: float = Field(description="Pitch angle in radians")
    yaw: float = Field(description="Yaw angle in radians")

    # Angular velocities
    roll_rate: float | None = Field(None, description="Roll rate in rad/s")
    pitch_rate: float | None = Field(None, description="Pitch rate in rad/s")
    yaw_rate: float | None = Field(None, description="Yaw rate in rad/s")


class Velocity(BaseModel):
    """Velocity in different frames."""

    # Ground velocity
    ground_speed: float | None = Field(None, description="Ground speed in m/s")
    air_speed: float | None = Field(None, description="Air speed in m/s")

    # NED frame velocities
    north: float | None = Field(None, description="North velocity in m/s")
    east: float | None = Field(None, description="East velocity in m/s")
    down: float | None = Field(None, description="Down velocity in m/s")


class Battery(BaseModel):
    """Battery information."""

    voltage: float | None = Field(None, description="Battery voltage in V")
    current: float | None = Field(None, description="Battery current in A")
    remaining_percent: float | None = Field(None, description="Remaining charge %")
    remaining_time: int | None = Field(None, description="Remaining time in seconds")


class GPS(BaseModel):
    """GPS information."""

    fix_type: int | None = Field(None, description="GPS fix type")
    satellites_visible: int | None = Field(None, description="Visible satellites")
    hdop: float | None = Field(None, description="Horizontal dilution of precision")
    vdop: float | None = Field(None, description="Vertical dilution of precision")


class Telemetry(BaseModel):
    """Complete telemetry data."""

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    drone_id: int = Field(description="Drone identifier")

    # Core data
    state: DroneState = Field(description="Current drone state")
    flight_mode: FlightMode | None = Field(None, description="Current flight mode")
    armed: bool = Field(default=False, description="Armed status")

    # Position and motion
    position: Position | None = Field(None, description="Current position")
    attitude: Attitude | None = Field(None, description="Current attitude")
    velocity: Velocity | None = Field(None, description="Current velocity")

    # System status
    battery: Battery | None = Field(None, description="Battery information")
    gps: GPS | None = Field(None, description="GPS information")

    # Health indicators
    health_all_ok: bool = Field(default=True, description="Overall health status")
    calibration_ok: bool = Field(default=True, description="Calibration status")

    # Connection
    connection_ok: bool = Field(default=True, description="Connection status")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class CommandParameter(BaseModel):
    """Command parameter specification."""

    type: str = Field(description="Parameter type (float, int, str, bool)")
    default: Any | None = Field(None, description="Default value")
    constraints: dict[str, Any] | None = Field(
        None, description="Parameter constraints"
    )
    description: str | None = Field(None, description="Parameter description")
    unit: str | None = Field(None, description="Parameter unit")


class CommandImplementation(BaseModel):
    """Command implementation details."""

    handler: str = Field(description="Python import path to command handler")
    supported_backends: list[str] = Field(description="Supported backend types")
    timeout: int = Field(default=60, description="Command timeout in seconds")


class CommandMetadata(BaseModel):
    """Command metadata."""

    name: str = Field(description="Command name (slug)")
    version: str = Field(description="Command version")
    category: str = Field(description="Command category")
    tags: list[str] = Field(default_factory=list, description="Command tags")


class CommandDescription(BaseModel):
    """Command description."""

    brief: str = Field(description="Brief description")
    detailed: str | None = Field(None, description="Detailed description")


class TelemetryFeedback(BaseModel):
    """Telemetry feedback messages."""

    start: str | None = Field(None, description="Command start message")
    success: str | None = Field(None, description="Command success message")
    error: str | None = Field(None, description="Command error message")


class CommandSpec(BaseModel):
    """Complete command specification from YAML."""

    apiVersion: str = Field(description="API version")
    kind: str = Field(description="Resource kind")
    metadata: CommandMetadata = Field(description="Command metadata")

    spec: dict[str, Any] = Field(description="Command specification")

    @validator("kind")
    def validate_kind(cls, v):
        """Ensure kind is DroneCommand."""
        if v != "DroneCommand":
            raise ValueError("kind must be 'DroneCommand'")
        return v


class CommandRequest(BaseModel):
    """Single command request."""

    name: str = Field(description="Command name")
    params: dict[str, Any] = Field(
        default_factory=dict, description="Command parameters"
    )


class CommandSequence(BaseModel):
    """Sequence of commands to execute."""

    sequence: list[CommandRequest] = Field(description="Commands to execute in order")
    metadata: dict[str, Any] | None = Field(None, description="Sequence metadata")


class CommandResult(BaseModel):
    """Result of command execution."""

    success: bool = Field(description="Whether command succeeded")
    message: str | None = Field(None, description="Result message")
    data: dict[str, Any] | None = Field(None, description="Result data")
    duration: float | None = Field(None, description="Execution duration in seconds")
    error: str | None = Field(None, description="Error message if failed")


class CommandEnvelope(BaseModel):
    """Command envelope for internal processing."""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), description="Unique command ID"
    )
    drone_id: int = Field(description="Target drone ID")
    sequence: list[CommandRequest] = Field(description="Commands to execute")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    priority: int = Field(default=0, description="Command priority")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class CommandExecution(BaseModel):
    """Active command execution state."""

    id: str = Field(description="Command execution ID")
    command: CommandRequest = Field(description="Command being executed")
    status: CommandStatus = Field(description="Execution status")
    progress: float = Field(default=0.0, description="Execution progress (0-1)")
    started_at: datetime | None = Field(None, description="Start time")
    completed_at: datetime | None = Field(None, description="Completion time")
    result: CommandResult | None = Field(None, description="Execution result")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class DroneStatus(BaseModel):
    """Complete drone status."""

    drone_id: int = Field(description="Drone identifier")
    state: DroneState = Field(description="Current operational state")
    current_command: CommandExecution | None = Field(
        None, description="Currently executing command"
    )
    queue_length: int = Field(default=0, description="Number of queued commands")
    last_telemetry: datetime | None = Field(
        None, description="Last telemetry update"
    )
    health_status: str = Field(default="ok", description="Health status")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class APIResponse(BaseModel):
    """Standard API response format."""

    success: bool = Field(description="Request success status")
    message: str | None = Field(None, description="Response message")
    data: Any | None = Field(None, description="Response data")
    errors: list[str] | None = Field(None, description="Error list")


class CommandAcceptedResponse(APIResponse):
    """Response for accepted command."""

    command_id: str = Field(description="Assigned command ID")
    estimated_duration: int | None = Field(
        None, description="Estimated duration in seconds"
    )
