"""Abstract base classes for drone backends."""

import abc
from typing import Optional

from ..core.models import DroneState, FlightMode, Position, Telemetry
from ..core.errors import BackendError
from ..core.logging import get_logger

logger = get_logger(__name__)


class AbstractBackend(abc.ABC):
    """Abstract base class for drone command backends."""
    
    def __init__(self, drone_id: int, connection_string: str):
        self.drone_id = drone_id
        self.connection_string = connection_string
        self._connected = False
        
    @abc.abstractmethod
    async def connect(self) -> None:
        """Connect to the drone."""
        pass
        
    @abc.abstractmethod 
    async def disconnect(self) -> None:
        """Disconnect from the drone."""
        pass
        
    @property
    def connected(self) -> bool:
        """Check if connected to drone."""
        return self._connected
        
    @abc.abstractmethod
    async def arm(self) -> None:
        """Arm the drone."""
        pass
        
    @abc.abstractmethod
    async def disarm(self) -> None:
        """Disarm the drone."""
        pass
        
    @abc.abstractmethod
    async def takeoff(self, altitude: float) -> None:
        """Take off to specified altitude."""
        pass
        
    @abc.abstractmethod
    async def land(self) -> None:
        """Land the drone."""
        pass
        
    @abc.abstractmethod
    async def return_to_launch(self) -> None:
        """Return to launch position."""
        pass
        
    @abc.abstractmethod
    async def hold_position(self) -> None:
        """Hold current position."""
        pass
        
    @abc.abstractmethod
    async def goto_position(self, position: Position, yaw: Optional[float] = None) -> None:
        """Go to specified position."""
        pass
        
    @abc.abstractmethod
    async def set_flight_mode(self, mode: FlightMode) -> None:
        """Set flight mode."""
        pass
        
    @abc.abstractmethod
    async def get_state(self) -> DroneState:
        """Get current drone state."""
        pass
        
    @abc.abstractmethod
    async def is_armed(self) -> bool:
        """Check if drone is armed."""
        pass
        
    @abc.abstractmethod
    async def get_flight_mode(self) -> FlightMode:
        """Get current flight mode."""
        pass
        
    async def emergency_stop(self) -> None:
        """Emergency stop - default implementation."""
        try:
            await self.hold_position()
            logger.warning("emergency_stop_executed", drone_id=self.drone_id)
        except Exception as e:
            logger.error("emergency_stop_failed", drone_id=self.drone_id, error=str(e))
            raise BackendError(f"Emergency stop failed: {e}")


class TelemetryProvider(abc.ABC):
    """Abstract base class for telemetry providers."""
    
    def __init__(self, drone_id: int, connection_string: str):
        self.drone_id = drone_id
        self.connection_string = connection_string
        self._connected = False
        
    @abc.abstractmethod
    async def connect(self) -> None:
        """Connect to telemetry source."""
        pass
        
    @abc.abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from telemetry source."""
        pass
        
    @property
    def connected(self) -> bool:
        """Check if connected."""
        return self._connected
        
    @abc.abstractmethod
    async def get_telemetry(self) -> Telemetry:
        """Get current telemetry data."""
        pass


class BackendFactory:
    """Factory for creating backend instances."""
    
    _backends = {
        "mavsdk": "dronesphere.backends.mavsdk.MavsdkBackend",
        "pymavlink": "dronesphere.backends.pymavlink.PyMavlinkBackend",
    }
    
    _telemetry_providers = {
        "mavsdk": "dronesphere.backends.mavsdk.MavsdkTelemetryProvider",
        "mavlink2rest": "dronesphere.backends.mavlink2rest.Mavlink2RestTelemetryProvider",
        "mavlink2rest": "dronesphere.backends.mavlink2rest.Mavlink2RestTelemetryProvider",
    }
    
    @classmethod
    def create_backend(
        cls, 
        backend_type: str, 
        drone_id: int, 
        connection_string: str
    ) -> AbstractBackend:
        """Create backend instance."""
        if backend_type not in cls._backends:
            raise BackendError(f"Unknown backend type: {backend_type}")
            
        import importlib
        module_path, class_name = cls._backends[backend_type].rsplit(".", 1)
        module = importlib.import_module(module_path)
        backend_class = getattr(module, class_name)
        
        return backend_class(drone_id, connection_string)
    
    @classmethod  
    def create_telemetry_provider(
        cls,
        provider_type: str,
        drone_id: int, 
        connection_string: str
    ) -> TelemetryProvider:
        """Create telemetry provider instance."""
        if provider_type not in cls._telemetry_providers:
            raise BackendError(f"Unknown telemetry provider: {provider_type}")
            
        import importlib
        module_path, class_name = cls._telemetry_providers[provider_type].rsplit(".", 1)
        module = importlib.import_module(module_path)
        provider_class = getattr(module, class_name)
        
        return provider_class(drone_id, connection_string)
