"""Abstract base class for drone backends.

Path: agent/backends/base.py
"""
from abc import ABC, abstractmethod
from typing import Any, Dict


class DroneBackend(ABC):
    """Abstract interface for drone communication backends."""

    @abstractmethod
    async def connect(self, connection_string: str = "udp://:14540") -> None:
        """Connect to the drone."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the drone."""
        pass

    @abstractmethod
    async def get_telemetry(self) -> Dict[str, Any]:
        """Get current telemetry data."""
        pass

    @property
    @abstractmethod
    def connected(self) -> bool:
        """Check if backend is connected to drone."""
        pass
