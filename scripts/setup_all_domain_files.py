#!/usr/bin/env python3
"""Complete setup script that creates ALL domain files with content."""

import os
from pathlib import Path

# Colors
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def create_file(filepath: str, content: str) -> None:
    """Create a file with content."""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    print(f"{GREEN}✅ Created: {filepath}{RESET}")


def main():
    """Create all domain model files."""
    print(f"\n{YELLOW}🚀 Creating ALL DroneSphere Domain Model Files{RESET}")
    print("=" * 50)
    
    # 1. Base Value Object
    create_file("src/shared/domain/value_object.py", '''"""Base value object for domain model."""

from abc import ABC
from typing import Any


class ValueObject(ABC):
    """
    Base class for value objects.
    
    Value objects are immutable and compared by their attributes.
    They have no identity beyond their values.
    """
    
    def __eq__(self, other: Any) -> bool:
        """Compare value objects by their attributes."""
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.__dict__ == other.__dict__
    
    def __hash__(self) -> int:
        """Make value objects hashable for use in sets/dicts."""
        return hash(tuple(sorted(self.__dict__.items())))
''')

    # 2. Base Entity
    create_file("src/shared/domain/entity.py", '''"""Base entity for domain model."""

from abc import ABC
from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID, uuid4

from src.shared.domain.event import DomainEvent


class Entity(ABC):
    """
    Base class for domain entities.
    
    Entities have identity (ID) and can raise domain events.
    They are mutable and compared by ID.
    """
    
    def __init__(self, id: Optional[UUID] = None) -> None:
        """Initialize entity with ID and event list."""
        self._id = id or uuid4()
        self._events: List[DomainEvent] = []
        self._created_at = datetime.utcnow()
        self._updated_at = datetime.utcnow()
    
    @property
    def id(self) -> UUID:
        """Get entity ID."""
        return self._id
    
    @property
    def created_at(self) -> datetime:
        """Get creation timestamp."""
        return self._created_at
    
    @property
    def updated_at(self) -> datetime:
        """Get last update timestamp."""
        return self._updated_at
    
    def add_event(self, event: DomainEvent) -> None:
        """Add a domain event."""
        self._events.append(event)
    
    def pull_events(self) -> List[DomainEvent]:
        """Get and clear all pending events."""
        events = self._events.copy()
        self._events.clear()
        return events
    
    def mark_updated(self) -> None:
        """Update the updated_at timestamp."""
        self._updated_at = datetime.utcnow()
    
    def __eq__(self, other: Any) -> bool:
        """Compare entities by ID."""
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self._id == other._id
    
    def __hash__(self) -> int:
        """Make entities hashable using their ID."""
        return hash(self._id)
''')

    # 3. Domain Event
    create_file("src/shared/domain/event.py", '''"""Base domain event."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict
from uuid import UUID, uuid4


@dataclass
class DomainEvent:
    """
    Base class for domain events.
    
    Events represent something that has happened in the domain.
    They are immutable and carry the information about what occurred.
    """
    
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=datetime.utcnow)
    aggregate_id: UUID = field(default=None)
    
    @property
    def event_name(self) -> str:
        """Get the event name (class name by default)."""
        return self.__class__.__name__
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            "event_id": str(self.event_id),
            "event_name": self.event_name,
            "occurred_at": self.occurred_at.isoformat(),
            "aggregate_id": str(self.aggregate_id) if self.aggregate_id else None,
            **{k: v for k, v in self.__dict__.items() 
               if k not in ["event_id", "occurred_at", "aggregate_id"]}
        }
''')

    # 4. Shared domain __init__.py
    create_file("src/shared/domain/__init__.py", '''"""Shared domain components."""

from src.shared.domain.entity import Entity
from src.shared.domain.event import DomainEvent
from src.shared.domain.value_object import ValueObject

__all__ = ["Entity", "ValueObject", "DomainEvent"]
''')

    # 5. Position Value Object
    create_file("src/core/domain/value_objects/position.py", '''"""Position value object for drone location."""

from dataclasses import dataclass
from typing import Optional

from src.shared.domain.value_object import ValueObject


@dataclass(frozen=True)
class Position(ValueObject):
    """
    Represents a geographical position in 3D space.
    
    This is a value object - immutable and compared by value.
    Coordinates use WGS84 (GPS standard).
    """
    
    latitude: float  # Degrees (-90 to 90)
    longitude: float  # Degrees (-180 to 180)
    altitude: float  # Meters above sea level
    altitude_relative: Optional[float] = None  # Meters above takeoff point
    
    def __post_init__(self) -> None:
        """Validate position values."""
        if not -90 <= self.latitude <= 90:
            raise ValueError(f"Latitude must be between -90 and 90, got {self.latitude}")
        
        if not -180 <= self.longitude <= 180:
            raise ValueError(f"Longitude must be between -180 and 180, got {self.longitude}")
        
        if self.altitude < -1000:  # Dead Sea is ~430m below sea level
            raise ValueError(f"Altitude seems unrealistic: {self.altitude}")
    
    @property
    def coordinates_tuple(self) -> tuple[float, float, float]:
        """Get position as tuple (lat, lon, alt)."""
        return (self.latitude, self.longitude, self.altitude)
    
    def distance_to(self, other: "Position") -> float:
        """
        Calculate approximate distance to another position in meters.
        Uses simplified calculation suitable for small distances.
        """
        import math
        
        # Earth radius in meters
        R = 6371000
        
        # Convert to radians
        lat1 = math.radians(self.latitude)
        lat2 = math.radians(other.latitude)
        dlat = math.radians(other.latitude - self.latitude)
        dlon = math.radians(other.longitude - self.longitude)
        
        # Haversine formula
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        # Horizontal distance
        horizontal = R * c
        
        # Include altitude difference
        vertical = abs(other.altitude - self.altitude)
        
        return math.sqrt(horizontal ** 2 + vertical ** 2)
    
    def with_altitude(self, new_altitude: float) -> "Position":
        """Create new position with different altitude."""
        return Position(
            latitude=self.latitude,
            longitude=self.longitude,
            altitude=new_altitude,
            altitude_relative=self.altitude_relative,
        )
    
    def __str__(self) -> str:
        """Human-readable string representation."""
        return (
            f"Position(lat={self.latitude:.6f}, "
            f"lon={self.longitude:.6f}, "
            f"alt={self.altitude:.1f}m)"
        )
''')

    # 6. Drone Events
    create_file("src/core/domain/events/drone_events.py", '''"""Domain events related to drone operations."""

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
''')

    # 7. Commands (Fixed version without circular import)
    create_file("src/core/domain/value_objects/command.py", '''"""Command value objects for drone control."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
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
    command_type: CommandType = CommandType.TAKEOFF
    
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
    
    command_type: CommandType = CommandType.LAND
    
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
    command_type: CommandType = CommandType.GO_TO
    
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
    command_type: CommandType = CommandType.MOVE
    
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
    
    command_type: CommandType = CommandType.RETURN_HOME
    priority: CommandPriority = CommandPriority.HIGH
    
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
    command_type: CommandType = CommandType.EMERGENCY_STOP
    priority: CommandPriority = CommandPriority.CRITICAL
    
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
    command_type: CommandType = CommandType.ORBIT
    
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
''')

    # 8. Drone Entity
    create_file("src/core/domain/entities/drone.py", '''"""Drone entity - the main aggregate root."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from src.core.domain.events.drone_events import (
    DroneArmedEvent,
    DroneConnectedEvent,
    DroneDisarmedEvent,
    DroneDisconnectedEvent,
    DroneLandedEvent,
    DroneMovedEvent,
    DroneStateChangedEvent,
    DroneTookOffEvent,
)
from src.core.domain.value_objects.position import Position
from src.shared.domain.entity import Entity


class DroneState(str, Enum):
    """Drone operational states."""
    
    DISCONNECTED = "DISCONNECTED"
    CONNECTED = "CONNECTED"
    ARMED = "ARMED"
    TAKING_OFF = "TAKING_OFF"
    HOVERING = "HOVERING"
    FLYING = "FLYING"
    LANDING = "LANDING"
    LANDED = "LANDED"
    EMERGENCY = "EMERGENCY"
    
    def can_transition_to(self, new_state: "DroneState") -> bool:
        """Check if transition to new state is valid."""
        valid_transitions = {
            DroneState.DISCONNECTED: [DroneState.CONNECTED],
            DroneState.CONNECTED: [DroneState.ARMED, DroneState.DISCONNECTED],
            DroneState.ARMED: [DroneState.TAKING_OFF, DroneState.CONNECTED],
            DroneState.TAKING_OFF: [DroneState.HOVERING, DroneState.EMERGENCY],
            DroneState.HOVERING: [DroneState.FLYING, DroneState.LANDING, DroneState.EMERGENCY],
            DroneState.FLYING: [DroneState.HOVERING, DroneState.LANDING, DroneState.EMERGENCY],
            DroneState.LANDING: [DroneState.LANDED, DroneState.EMERGENCY],
            DroneState.LANDED: [DroneState.CONNECTED],
            DroneState.EMERGENCY: [DroneState.LANDED, DroneState.DISCONNECTED],
        }
        return new_state in valid_transitions.get(self, [])


class Drone(Entity):
    """
    Drone aggregate root.
    
    Represents a single drone with its state, position, and capabilities.
    Enforces business rules and raises domain events.
    """
    
    def __init__(
        self,
        id: Optional[UUID] = None,
        name: str = "Drone",
        model: str = "Generic",
        firmware_version: str = "1.0.0",
    ) -> None:
        """Initialize drone in disconnected state."""
        super().__init__(id)
        self._name = name
        self._model = model
        self._firmware_version = firmware_version
        self._state = DroneState.DISCONNECTED
        self._position: Optional[Position] = None
        self._home_position: Optional[Position] = None
        self._battery_percent: float = 100.0
        self._is_armed = False
        self._last_heartbeat: Optional[datetime] = None
        self._flight_time_seconds: int = 0
        self._total_distance_meters: float = 0.0
    
    # Properties
    @property
    def name(self) -> str:
        """Get drone name."""
        return self._name
    
    @property
    def model(self) -> str:
        """Get drone model."""
        return self._model
    
    @property
    def state(self) -> DroneState:
        """Get current drone state."""
        return self._state
    
    @property
    def position(self) -> Optional[Position]:
        """Get current position."""
        return self._position
    
    @property
    def home_position(self) -> Optional[Position]:
        """Get home position."""
        return self._home_position
    
    @property
    def battery_percent(self) -> float:
        """Get battery percentage."""
        return self._battery_percent
    
    @property
    def is_armed(self) -> bool:
        """Check if drone is armed."""
        return self._is_armed
    
    @property
    def is_connected(self) -> bool:
        """Check if drone is connected."""
        return self._state != DroneState.DISCONNECTED
    
    @property
    def is_flying(self) -> bool:
        """Check if drone is in flight."""
        return self._state in [
            DroneState.TAKING_OFF,
            DroneState.HOVERING,
            DroneState.FLYING,
            DroneState.LANDING,
        ]
    
    # State transitions
    def connect(self, initial_position: Position) -> None:
        """Connect to drone."""
        if self._state != DroneState.DISCONNECTED:
            raise ValueError(f"Cannot connect: drone is {self._state}")
        
        self._state = DroneState.CONNECTED
        self._position = initial_position
        self._last_heartbeat = datetime.utcnow()
        self.mark_updated()
        
        self.add_event(
            DroneConnectedEvent(
                aggregate_id=self.id,
                position=initial_position,
            )
        )
    
    def disconnect(self) -> None:
        """Disconnect from drone."""
        if self.is_flying:
            raise ValueError("Cannot disconnect while flying")
        
        old_state = self._state
        self._state = DroneState.DISCONNECTED
        self._last_heartbeat = None
        self.mark_updated()
        
        self.add_event(
            DroneDisconnectedEvent(
                aggregate_id=self.id,
                last_state=old_state,
            )
        )
    
    def arm(self) -> None:
        """Arm the drone for flight."""
        if self._state != DroneState.CONNECTED:
            raise ValueError(f"Cannot arm: drone is {self._state}")
        
        if self._battery_percent < 20:
            raise ValueError("Cannot arm: battery too low")
        
        self._state = DroneState.ARMED
        self._is_armed = True
        self._home_position = self._position
        self.mark_updated()
        
        self.add_event(
            DroneArmedEvent(
                aggregate_id=self.id,
                home_position=self._home_position,
            )
        )
    
    def disarm(self) -> None:
        """Disarm the drone."""
        if not self._is_armed:
            return
        
        if self.is_flying:
            raise ValueError("Cannot disarm while flying")
        
        self._state = DroneState.CONNECTED
        self._is_armed = False
        self.mark_updated()
        
        self.add_event(DroneDisarmedEvent(aggregate_id=self.id))
    
    def takeoff(self, target_altitude: float) -> None:
        """Initiate takeoff."""
        if self._state != DroneState.ARMED:
            raise ValueError(f"Cannot takeoff: drone is {self._state}")
        
        if target_altitude < 1 or target_altitude > 120:
            raise ValueError(f"Invalid takeoff altitude: {target_altitude}")
        
        self._state = DroneState.TAKING_OFF
        self.mark_updated()
        
        self.add_event(
            DroneTookOffEvent(
                aggregate_id=self.id,
                target_altitude=target_altitude,
            )
        )
    
    def land(self) -> None:
        """Initiate landing."""
        if not self.is_flying:
            raise ValueError(f"Cannot land: drone is {self._state}")
        
        self._state = DroneState.LANDING
        self.mark_updated()
        
        self.add_event(DroneLandedEvent(aggregate_id=self.id))
    
    def update_position(self, new_position: Position) -> None:
        """Update drone position."""
        if not self.is_connected:
            raise ValueError("Cannot update position: drone disconnected")
        
        old_position = self._position
        self._position = new_position
        
        # Update state based on movement
        if self._state == DroneState.TAKING_OFF and new_position.altitude > 1:
            self._state = DroneState.HOVERING
            self.add_event(
                DroneStateChangedEvent(
                    aggregate_id=self.id,
                    old_state=DroneState.TAKING_OFF,
                    new_state=DroneState.HOVERING,
                )
            )
        elif self._state == DroneState.LANDING and new_position.altitude < 0.5:
            self._state = DroneState.LANDED
            self._is_armed = False
            self.add_event(
                DroneStateChangedEvent(
                    aggregate_id=self.id,
                    old_state=DroneState.LANDING,
                    new_state=DroneState.LANDED,
                )
            )
        
        # Calculate distance traveled
        if old_position:
            distance = old_position.distance_to(new_position)
            self._total_distance_meters += distance
        
        self._last_heartbeat = datetime.utcnow()
        self.mark_updated()
        
        self.add_event(
            DroneMovedEvent(
                aggregate_id=self.id,
                old_position=old_position,
                new_position=new_position,
            )
        )
    
    def update_battery(self, battery_percent: float) -> None:
        """Update battery level."""
        if not 0 <= battery_percent <= 100:
            raise ValueError(f"Invalid battery percent: {battery_percent}")
        
        self._battery_percent = battery_percent
        self._last_heartbeat = datetime.utcnow()
        self.mark_updated()
        
        # Check for low battery
        if battery_percent < 15 and self.is_flying:
            self.emergency_land()
    
    def emergency_land(self) -> None:
        """Initiate emergency landing."""
        if not self.is_flying:
            return
        
        old_state = self._state
        self._state = DroneState.EMERGENCY
        self.mark_updated()
        
        self.add_event(
            DroneStateChangedEvent(
                aggregate_id=self.id,
                old_state=old_state,
                new_state=DroneState.EMERGENCY,
            )
        )
    
    def update_heartbeat(self) -> None:
        """Update last heartbeat timestamp."""
        self._last_heartbeat = datetime.utcnow()
    
    def is_connection_lost(self, timeout_seconds: int = 5) -> bool:
        """Check if connection is lost based on heartbeat."""
        if not self._last_heartbeat:
            return True
        
        time_since_heartbeat = (datetime.utcnow() - self._last_heartbeat).total_seconds()
        return time_since_heartbeat > timeout_seconds
''')

    print(f"\n{GREEN}🎉 ALL domain model files created successfully!{RESET}")
    print("\nNext step: Run the test script")
    print("  python scripts/test_domain_models.py")


if __name__ == "__main__":
    main()