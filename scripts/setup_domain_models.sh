#!/bin/bash
# Setup script to create all domain model files

echo "🚁 Setting up DroneSphere Domain Models..."

# Create shared domain base classes
echo "Creating shared domain base classes..."
cat > src/shared/domain/value_object.py << 'EOF'
"""Base value object for domain model."""

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
EOF

cat > src/shared/domain/entity.py << 'EOF'
"""Base entity for domain model."""

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
EOF

cat > src/shared/domain/event.py << 'EOF'
"""Base domain event."""

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
EOF

# Create all __init__.py files first
echo "Creating __init__.py files..."
echo '"""Shared domain components."""

from src.shared.domain.entity import Entity
from src.shared.domain.event import DomainEvent
from src.shared.domain.value_object import ValueObject

__all__ = ["Entity", "ValueObject", "DomainEvent"]' > src/shared/domain/__init__.py

echo '"""Domain entities."""

from src.core.domain.entities.drone import Drone, DroneState

__all__ = ["Drone", "DroneState"]' > src/core/domain/entities/__init__.py

echo '"""Domain value objects."""

from src.core.domain.value_objects.command import (
    CommandPriority,
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

__all__ = [
    "Position",
    "CommandType",
    "CommandPriority",
    "DroneCommand",
    "TakeoffCommand",
    "LandCommand",
    "GoToCommand",
    "MoveCommand",
    "OrbitCommand",
    "ReturnHomeCommand",
    "EmergencyStopCommand",
]' > src/core/domain/value_objects/__init__.py

echo '"""Domain events."""

from src.core.domain.events.drone_events import (
    DroneArmedEvent,
    DroneBatteryLowEvent,
    DroneConnectedEvent,
    DroneDisarmedEvent,
    DroneDisconnectedEvent,
    DroneEmergencyEvent,
    DroneLandedEvent,
    DroneMovedEvent,
    DroneStateChangedEvent,
    DroneTookOffEvent,
)

__all__ = [
    "DroneConnectedEvent",
    "DroneDisconnectedEvent",
    "DroneArmedEvent",
    "DroneDisarmedEvent",
    "DroneTookOffEvent",
    "DroneLandedEvent",
    "DroneMovedEvent",
    "DroneStateChangedEvent",
    "DroneBatteryLowEvent",
    "DroneEmergencyEvent",
]' > src/core/domain/events/__init__.py

echo '"""Domain layer containing business logic."""

from src.core.domain.entities.drone import Drone, DroneState
from src.core.domain.value_objects.command import (
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

__all__ = [
    # Entities
    "Drone",
    "DroneState",
    # Value Objects
    "Position",
    # Commands
    "DroneCommand",
    "TakeoffCommand",
    "LandCommand",
    "GoToCommand",
    "MoveCommand",
    "OrbitCommand",
    "ReturnHomeCommand",
    "EmergencyStopCommand",
]' > src/core/domain/__init__.py

echo "✅ Created all __init__.py files"
echo ""
echo "📝 Now you need to:"
echo "1. Copy Position value object to: src/core/domain/value_objects/position.py"
echo "2. Copy Drone entity to: src/core/domain/entities/drone.py"
echo "3. Copy Drone events to: src/core/domain/events/drone_events.py"
echo "4. Copy Command value objects to: src/core/domain/value_objects/command.py"
echo "5. Copy test script to: scripts/test_domain_models.py"
echo ""
echo "Then run: python scripts/test_domain_models.py"