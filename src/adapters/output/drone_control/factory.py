"""Factory for creating drone control adapters.

This module provides a factory pattern for creating different drone control
adapters based on configuration.
"""

from enum import Enum
from typing import Any, Dict, Optional

from src.adapters.output.drone_control.mavsdk_adapter import MAVSDKAdapter
from src.core.ports.output.drone_control import DroneControlPort

# Future imports when implemented:
# from src.adapters.output.drone_control.ardupilot_adapter import ArduPilotAdapter
# from src.adapters.output.drone_control.px4_adapter import PX4Adapter
# from src.adapters.output.drone_control.simulator_adapter import SimulatorAdapter


class DroneBackend(str, Enum):
    """Available drone control backends."""
    
    MAVSDK = "mavsdk"
    ARDUPILOT = "ardupilot"
    PX4 = "px4"
    SIMULATOR = "simulator"
    MOCK = "mock"  # For testing


class DroneControlFactory:
    """Factory for creating drone control adapters."""
    
    @staticmethod
    def create(
        backend: str,
        config: Optional[Dict[str, Any]] = None
    ) -> DroneControlPort:
        """Create a drone control adapter.
        
        Args:
            backend: The backend to use (mavsdk, ardupilot, etc.)
            config: Backend-specific configuration
            
        Returns:
            DroneControlPort implementation
            
        Raises:
            ValueError: If backend is not supported
        """
        config = config or {}
        
        if backend == DroneBackend.MAVSDK:
            return MAVSDKAdapter()
        
        # elif backend == DroneBackend.ARDUPILOT:
        #     return ArduPilotAdapter(**config)
        
        # elif backend == DroneBackend.PX4:
        #     return PX4Adapter(**config)
        
        # elif backend == DroneBackend.SIMULATOR:
        #     sim_type = config.get("simulator", "gazebo")
        #     return SimulatorAdapter(simulator=sim_type, **config)
        
        # elif backend == DroneBackend.MOCK:
        #     from src.adapters.output.drone_control.mock_adapter import MockAdapter
        #     return MockAdapter(**config)
        
        else:
            raise ValueError(
                f"Unsupported drone backend: {backend}. "
                f"Supported backends: {', '.join([b.value for b in DroneBackend])}"
            )
    
    @staticmethod
    def create_from_env(env_config: Dict[str, Any]) -> DroneControlPort:
        """Create drone control adapter from environment configuration.
        
        Args:
            env_config: Environment configuration dictionary
            
        Returns:
            DroneControlPort implementation
        """
        backend = env_config.get("DRONE_BACKEND", DroneBackend.MAVSDK)
        
        # Build backend-specific config
        config = {}
        
        if backend == DroneBackend.MAVSDK:
            # MAVSDK doesn't need special config
            pass
        
        elif backend == DroneBackend.SIMULATOR:
            config["simulator"] = env_config.get("SIMULATOR_TYPE", "gazebo")
            config["headless"] = env_config.get("SIMULATOR_HEADLESS", "false").lower() == "true"
        
        return DroneControlFactory.create(backend, config)