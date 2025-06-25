"""Domain events related to drone operations."""

from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID

from src.core.domain.value_objects.position import Position
from src.shared.domain.event import DomainEvent


@dataclass
class DroneConnectedEvent(DomainEvent):
    """Raised when drone connects."""
    
    position: Position = field(default=None)
    
    def __post_init__(self):
        """Ensure position is required."""
        if self.position is None:
            raise ValueError("Position is required for DroneConnectedEvent")


@dataclass
class DroneDisconnectedEvent(DomainEvent):
    """Raised when drone disconnects."""
    
    last_state: str = field(default="")
    
    def __post_init__(self):
        """Ensure last_state is required."""
        if not self.last_state:
            raise ValueError("last_state is required for DroneDisconnectedEvent")


@dataclass
class DroneArmedEvent(DomainEvent):
    """Raised when drone is armed."""
    
    home_position: Position = field(default=None)
    
    def __post_init__(self):
        """Ensure home_position is required."""
        if self.home_position is None:
            raise ValueError("home_position is required for DroneArmedEvent")


@dataclass
class DroneDisarmedEvent(DomainEvent):
    """Raised when drone is disarmed."""
    
    pass


@dataclass
class DroneTookOffEvent(DomainEvent):
    """Raised when drone takes off."""
    
    target_altitude: float = field(default=0.0)
    
    def __post_init__(self):
        """Validate altitude."""
        if self.target_altitude <= 0:
            raise ValueError("target_altitude must be positive")


@dataclass
class DroneLandedEvent(DomainEvent):
    """Raised when drone lands."""
    
    pass


@dataclass
class DroneMovedEvent(DomainEvent):
    """Raised when drone position changes."""
    
    old_position: Optional[Position] = None
    new_position: Position = field(default=None)
    
    def __post_init__(self):
        """Ensure new_position is required."""
        if self.new_position is None:
            raise ValueError("new_position is required for DroneMovedEvent")


@dataclass
class DroneStateChangedEvent(DomainEvent):
    """Raised when drone state changes."""
    
    old_state: str = field(default="")
    new_state: str = field(default="")
    
    def __post_init__(self):
        """Ensure states are required."""
        if not self.old_state or not self.new_state:
            raise ValueError("Both old_state and new_state are required")


@dataclass
class DroneBatteryLowEvent(DomainEvent):
    """Raised when battery is critically low."""
    
    battery_percent: float = field(default=0.0)
    
    def __post_init__(self):
        """Validate battery percent."""
        if not 0 <= self.battery_percent <= 100:
            raise ValueError("battery_percent must be between 0 and 100")


@dataclass
class DroneEmergencyEvent(DomainEvent):
    """Raised when emergency condition occurs."""
    
    reason: str = field(default="")
    severity: str = field(default="MEDIUM")  # LOW, MEDIUM, HIGH, CRITICAL
    
    def __post_init__(self):
        """Validate emergency event."""
        if not self.reason:
            raise ValueError("reason is required for DroneEmergencyEvent")
        if self.severity not in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]:
            raise ValueError(f"Invalid severity: {self.severity}")
