"""Base domain event."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4


@dataclass
class DomainEvent:
    """
    Base class for domain events.
    
    Events represent something that has happened in the domain.
    They are immutable and carry the information about what occurred.
    All fields have defaults to avoid field ordering issues in subclasses.
    """
    
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=datetime.utcnow)
    aggregate_id: Optional[UUID] = None
    
    @property
    def event_name(self) -> str:
        """Get the event name (class name by default)."""
        return self.__class__.__name__
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        result = {
            "event_id": str(self.event_id),
            "event_name": self.event_name,
            "occurred_at": self.occurred_at.isoformat(),
        }
        
        if self.aggregate_id:
            result["aggregate_id"] = str(self.aggregate_id)
        
        # Add any additional fields from subclasses
        for key, value in self.__dict__.items():
            if key not in ["event_id", "occurred_at", "aggregate_id"]:
                result[key] = value
                
        return result
