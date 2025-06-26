"""Factory for creating drone control adapters.

This module provides a factory pattern for creating different drone control
adapters based on configuration.
"""

from enum import Enum
from typing import Any, Dict, Optional

from src.adapters.output.drone_control.mavsdk_adapter import MAVSDKAdapter
from src.config.drone_config import drone_config, DroneProfile
from src.core.ports.output.drone_control import DroneControlPort

# Future imports when implemented:
# from src.adapters.output.drone_control.pymavlink_adapter import PyMAVLinkAdapter
# from src.adapters.output.drone_control.ardupilot_adapter import ArduPilotAdapter
# from src.adapters.output.drone_control.px4_adapter import PX4Adapter
# from src.adapters.output.drone_control.simulator_adapter import SimulatorAdapter
# from src.adapters.output.drone_control.dji_adapter import DJIAdapter


class DroneBackend(str, Enum):
    """Available drone control backends."""
    
    MAVSDK = "mavsdk"
    PYMAVLINK = "pymavlink"
    ARDUPILOT = "ardupilot"
    PX4 = "px4"
    DJI = "dji"
    SIMULATOR = "simulator"
    MOCK = "mock"  # For testing


class DroneControlFactory:
    """Factory for creating drone control adapters."""
    
    @staticmethod
    def create(
        backend: str,
        config: Optional[Dict[str, Any]] = None,
        profile: Optional[DroneProfile] = None
    ) -> DroneControlPort:
        """Create a drone control adapter.
        
        Args:
            backend: The backend to use (mavsdk, pymavlink, etc.)
            config: Backend-specific configuration
            profile: Optional drone profile with connection details
            
        Returns:
            DroneControlPort implementation
            
        Raises:
            ValueError: If backend is not supported
        """
        config = config or {}
        
        # Apply profile settings if provided
        if profile:
            config['connection_string'] = profile.connection_string
            config['drone_id'] = profile.drone_id
            if profile.max_altitude_m:
                config['max_altitude_m'] = profile.max_altitude_m
            if profile.max_velocity_m_s:
                config['max_velocity_m_s'] = profile.max_velocity_m_s
        
        # Apply global config defaults
        config.setdefault('connection_string', drone_config.default_connection_string)
        config.setdefault('connection_timeout', drone_config.connection_timeout_s)
        config.setdefault('max_altitude_m', drone_config.max_altitude_m)
        config.setdefault('max_velocity_m_s', drone_config.max_velocity_m_s)
        
        if backend == DroneBackend.MAVSDK:
            adapter = MAVSDKAdapter(config)
            return adapter
        
        # elif backend == DroneBackend.PYMAVLINK:
        #     from src.adapters.output.drone_control.pymavlink_adapter import PyMAVLinkAdapter
        #     return PyMAVLinkAdapter(**config)
        
        # elif backend == DroneBackend.ARDUPILOT:
        #     return ArduPilotAdapter(**config)
        
        # elif backend == DroneBackend.PX4:
        #     return PX4Adapter(**config)
        
        # elif backend == DroneBackend.DJI:
        #     return DJIAdapter(**config)
        
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
    def create_from_env(env_config: Optional[Dict[str, Any]] = None) -> DroneControlPort:
        """Create drone control adapter from environment configuration.
        
        Args:
            env_config: Optional environment configuration dictionary
            
        Returns:
            DroneControlPort implementation
        """
        # Use global config if no env_config provided
        backend = drone_config.backend
        
        # Build backend-specific config
        config = {
            'connection_string': drone_config.default_connection_string,
            'connection_timeout': drone_config.connection_timeout_s,
            'max_altitude_m': drone_config.max_altitude_m,
            'max_velocity_m_s': drone_config.max_velocity_m_s,
            'max_distance_from_home_m': drone_config.max_distance_from_home_m,
            'min_battery_percent': drone_config.min_battery_percent,
            'critical_battery_percent': drone_config.critical_battery_percent,
        }
        
        # Override with env_config if provided
        if env_config:
            backend = env_config.get("DRONE_BACKEND", backend)
            config.update(env_config)
        
        return DroneControlFactory.create(backend, config)
    
    @staticmethod
    def create_from_profile(profile: DroneProfile) -> DroneControlPort:
        """Create drone control adapter from a drone profile.
        
        Args:
            profile: Drone profile with connection details
            
        Returns:
            DroneControlPort implementation
        """
        return DroneControlFactory.create(
            backend=profile.backend,
            profile=profile
        )