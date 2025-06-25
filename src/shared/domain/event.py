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
