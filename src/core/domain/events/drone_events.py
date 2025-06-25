"""Domain events related to drone operations."""

from dataclasses import dataclass
from typing import Optional

from src.core.domain.value_objects.position import Position
from src.shared.domain.event import DomainEvent


@dataclass
class DroneConnectedEvent(DomainEvent):
    """Raised when drone connects."""
    
    position: Position


@dataclass
class DroneDisconnectedEvent(DomainEvent):
    """Raised when drone disconnects."""
    
    last_state: str


@dataclass
class DroneArmedEvent(DomainEvent):
    """Raised when drone is armed."""
    
    home_position: Position


@dataclass
class DroneDisarmedEvent(DomainEvent):
    """Raised when drone is disarmed."""
    
    pass


@dataclass
class DroneTookOffEvent(DomainEvent):
    """Raised when drone takes off."""
    
    target_altitude: float


@dataclass
class DroneLandedEvent(DomainEvent):
    """Raised when drone lands."""
    
    pass


@dataclass
class DroneMovedEvent(DomainEvent):
    """Raised when drone position changes."""
    
    old_position: Optional[Position]
    new_position: Position


@dataclass
class DroneStateChangedEvent(DomainEvent):
    """Raised when drone state changes."""
    
    old_state: str
    new_state: str


@dataclass
class DroneBatteryLowEvent(DomainEvent):
    """Raised when battery is critically low."""
    
    battery_percent: float


@dataclass
class DroneEmergencyEvent(DomainEvent):
    """Raised when emergency condition occurs."""
    
    reason: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
