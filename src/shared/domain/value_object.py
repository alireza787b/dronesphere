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
