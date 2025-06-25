"""Command value objects for drone control."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from src.shared.domain.value_object import ValueObject


class CommandType(str, Enum):
    """Types of drone commands."""
    
    # Basic flight
    TAKEOFF = "TAKEOFF"
    LAND = "LAND"
    MOVE = "MOVE"
    HOVER = "HOVER"
    RETURN_HOME = "RETURN_HOME"
    
    # Movement
    GO_TO = "GO_TO"
    ORBIT = "ORBIT"
    FOLLOW_PATH = "FOLLOW_PATH"
    
    # Camera
    TAKE_PHOTO = "TAKE_PHOTO"
    START_VIDEO = "START_VIDEO"
    STOP_VIDEO = "STOP_VIDEO"
    
    # System
    EMERGENCY_STOP = "EMERGENCY_STOP"
    SET_SPEED = "SET_SPEED"
    SET_ALTITUDE = "SET_ALTITUDE"


class CommandPriority(int, Enum):
    """Command priority levels."""
    
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass(frozen=True)
class DroneCommand(ValueObject, ABC):
    """Base class for drone commands."""
    
    command_type: CommandType
    priority: CommandPriority = CommandPriority.NORMAL
    
    @abstractmethod
    def validate(self) -> None:
        """Validate command parameters."""
        pass
    
    @abstractmethod
    def describe(self) -> str:
        """Get human-readable description."""
        pass


@dataclass(frozen=True)
class TakeoffCommand(DroneCommand):
    """Command to takeoff to specified altitude."""
    
    target_altitude: float  # meters
    command_type: CommandType = field(default=CommandType.TAKEOFF, init=False)
    
    def __post_init__(self):
        """Set command type after initialization."""
        object.__setattr__(self, 'command_type', CommandType.TAKEOFF)
    
    def validate(self) -> None:
        """Validate takeoff parameters."""
        if not 1 <= self.target_altitude <= 120:
            raise ValueError(f"Takeoff altitude must be 1-120m, got {self.target_altitude}")
    
    def describe(self) -> str:
        """Get command description."""
        return f"Takeoff to {self.target_altitude}m"


@dataclass(frozen=True)
class LandCommand(DroneCommand):
    """Command to land at current position."""
    
    command_type: CommandType = field(default=CommandType.LAND, init=False)
    
    def __post_init__(self):
        """Set command type after initialization."""
        object.__setattr__(self, 'command_type', CommandType.LAND)
    
    def validate(self) -> None:
        """No validation needed for land."""
        pass
    
    def describe(self) -> str:
        """Get command description."""
        return "Land at current position"


@dataclass(frozen=True)
class GoToCommand(DroneCommand):
    """Command to fly to specific position."""
    
    target_position: "Position"  # Forward reference
    speed_m_s: Optional[float] = None
    command_type: CommandType = field(default=CommandType.GO_TO, init=False)
    
    def __post_init__(self):
        """Set command type after initialization."""
        object.__setattr__(self, 'command_type', CommandType.GO_TO)
    
    def validate(self) -> None:
        """Validate goto parameters."""
        if self.speed_m_s is not None:
            if not 0.1 <= self.speed_m_s <= 20:
                raise ValueError(f"Speed must be 0.1-20 m/s, got {self.speed_m_s}")
    
    def describe(self) -> str:
        """Get command description."""
        speed_info = f" at {self.speed_m_s}m/s" if self.speed_m_s else ""
        return f"Go to {self.target_position}{speed_info}"


@dataclass(frozen=True)
class MoveCommand(DroneCommand):
    """Command for relative movement."""
    
    forward_m: float = 0.0  # Positive = forward, negative = backward
    right_m: float = 0.0    # Positive = right, negative = left
    up_m: float = 0.0       # Positive = up, negative = down
    rotate_deg: float = 0.0 # Positive = clockwise, negative = counter-clockwise
    command_type: CommandType = field(default=CommandType.MOVE, init=False)
    
    def __post_init__(self):
        """Set command type after initialization."""
        object.__setattr__(self, 'command_type', CommandType.MOVE)
    
    def validate(self) -> None:
        """Validate move parameters."""
        max_distance = 100  # Maximum relative movement
        if abs(self.forward_m) > max_distance:
            raise ValueError(f"Forward distance too large: {self.forward_m}")
        if abs(self.right_m) > max_distance:
            raise ValueError(f"Right distance too large: {self.right_m}")
        if abs(self.up_m) > max_distance:
            raise ValueError(f"Up distance too large: {self.up_m}")
        if abs(self.rotate_deg) > 180:
            raise ValueError(f"Rotation must be -180 to 180 degrees")
    
    def describe(self) -> str:
        """Get command description."""
        parts = []
        if self.forward_m != 0:
            direction = "forward" if self.forward_m > 0 else "backward"
            parts.append(f"{abs(self.forward_m)}m {direction}")
        if self.right_m != 0:
            direction = "right" if self.right_m > 0 else "left"
            parts.append(f"{abs(self.right_m)}m {direction}")
        if self.up_m != 0:
            direction = "up" if self.up_m > 0 else "down"
            parts.append(f"{abs(self.up_m)}m {direction}")
        if self.rotate_deg != 0:
            direction = "clockwise" if self.rotate_deg > 0 else "counter-clockwise"
            parts.append(f"rotate {abs(self.rotate_deg)}° {direction}")
        
        return "Move " + ", ".join(parts) if parts else "Hover in place"


@dataclass(frozen=True)
class ReturnHomeCommand(DroneCommand):
    """Command to return to home position."""
    
    command_type: CommandType = field(default=CommandType.RETURN_HOME, init=False)
    priority: CommandPriority = field(default=CommandPriority.HIGH)
    
    def __post_init__(self):
        """Set command type after initialization."""
        object.__setattr__(self, 'command_type', CommandType.RETURN_HOME)
    
    def validate(self) -> None:
        """No validation needed."""
        pass
    
    def describe(self) -> str:
        """Get command description."""
        return "Return to home position"


@dataclass(frozen=True)
class EmergencyStopCommand(DroneCommand):
    """Emergency stop command."""
    
    reason: str = "Emergency stop requested"
    command_type: CommandType = field(default=CommandType.EMERGENCY_STOP, init=False)
    priority: CommandPriority = field(default=CommandPriority.CRITICAL)
    
    def __post_init__(self):
        """Set command type after initialization."""
        object.__setattr__(self, 'command_type', CommandType.EMERGENCY_STOP)
    
    def validate(self) -> None:
        """No validation needed for emergency."""
        pass
    
    def describe(self) -> str:
        """Get command description."""
        return f"EMERGENCY STOP: {self.reason}"


@dataclass(frozen=True)
class OrbitCommand(DroneCommand):
    """Command to orbit around a point."""
    
    center: "Position"  # Forward reference
    radius_m: float
    velocity_m_s: float = 5.0
    clockwise: bool = True
    orbits: Optional[int] = None  # None = continuous
    command_type: CommandType = field(default=CommandType.ORBIT, init=False)
    
    def __post_init__(self):
        """Set command type after initialization."""
        object.__setattr__(self, 'command_type', CommandType.ORBIT)
    
    def validate(self) -> None:
        """Validate orbit parameters."""
        if not 5 <= self.radius_m <= 100:
            raise ValueError(f"Orbit radius must be 5-100m, got {self.radius_m}")
        if not 1 <= self.velocity_m_s <= 15:
            raise ValueError(f"Orbit velocity must be 1-15m/s, got {self.velocity_m_s}")
        if self.orbits is not None and self.orbits < 1:
            raise ValueError("Number of orbits must be positive")
    
    def describe(self) -> str:
        """Get command description."""
        direction = "clockwise" if self.clockwise else "counter-clockwise"
        orbits_info = f" for {self.orbits} orbits" if self.orbits else " continuously"
        return (
            f"Orbit {direction} around {self.center} "
            f"with radius {self.radius_m}m at {self.velocity_m_s}m/s{orbits_info}"
        )


# Import Position at the end to resolve forward references
from src.core.domain.value_objects.position import Position

# Update forward references
GoToCommand.__annotations__["target_position"] = Position
OrbitCommand.__annotations__["center"] = Position
