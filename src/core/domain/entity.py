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