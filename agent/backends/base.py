"""Abstract base class for drone backends - UPDATED VERSION.

Path: agent/backends/base.py

CHANGES:
- Updated connection signature to support auto-detection
- Made connection_string optional to encourage smart defaults
- Added proper return type for connect method
- Enhanced documentation for modern backends
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class DroneBackend(ABC):
    """Abstract interface for drone communication backends.

    Modern drone backends should implement intelligent connection detection
    and provide robust error handling for various network configurations.
    """

    @abstractmethod
    async def connect(self, connection_string: Optional[str] = None) -> bool:
        """Connect to the drone with intelligent auto-detection.

        Args:
            connection_string: Optional override for connection string.
                             If None, backend should auto-detect the best connection.

        Returns:
            bool: True if connection successful, False otherwise.

        Note:
            Modern implementations should support:
            - Auto-detection of Docker/SITL containers
            - Fallback connection strategies
            - Environment variable overrides
            - Multiple connection format support (udpin://, udpout://, etc.)
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the drone and cleanup resources.

        Should properly cleanup:
        - Active connections
        - Background tasks
        - Telemetry subscriptions
        - Resource handles
        """
        pass

    @abstractmethod
    async def get_telemetry(self) -> Dict[str, Any]:
        """Get current telemetry data.

        Returns:
            dict: Current telemetry data including:
                - position: GPS coordinates and altitude
                - attitude: Roll, pitch, yaw
                - battery: Voltage and remaining percentage
                - flight_mode: Current flight mode string
                - gps_info: Satellite count and fix type
                - armed: Armed state boolean
                - connected: Connection status
                - timestamp: Data timestamp
        """
        pass

    @property
    @abstractmethod
    def connected(self) -> bool:
        """Check if backend is connected to drone.

        Returns:
            bool: True if connected and receiving telemetry, False otherwise.
        """
        pass

    # Optional methods that backends can implement for enhanced functionality
    async def get_px4_origin(self) -> Optional[Dict[str, float]]:
        """Get PX4 origin coordinates (first GPS fix position).

        Returns:
            Optional[dict]: Origin coordinates with latitude, longitude, altitude
                          or None if not available.
        """
        return None

    async def health_check(self) -> Dict[str, Any]:
        """Perform a comprehensive health check of the backend.

        Returns:
            dict: Health status including:
                - backend_type: Type of backend (e.g., "MAVSDK")
                - connection_string: Active connection string
                - connection_status: Detailed connection state
                - telemetry_active: Whether telemetry is flowing
                - last_telemetry_time: Timestamp of last telemetry update
                - error_count: Number of recent errors
        """
        return {
            "backend_type": self.__class__.__name__,
            "connection_string": getattr(self, '_connection_string', 'unknown'),
            "connection_status": self.connected,
            "telemetry_active": self.connected,
            "last_telemetry_time": None,
            "error_count": 0,
        }
