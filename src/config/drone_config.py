"""Drone configuration module.

Handles all drone-related configuration including connections,
limits, and safety parameters.
"""

import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings

class DroneConnectionConfig(BaseSettings):
    """Configuration for drone connections."""
    
    # Default connection settings from .env
    default_connection_string: str = Field(
        "udp://:14540",
        env="DRONE_CONNECTION_STRING",
        description="Default MAVLink connection string"
    )
    
    mavsdk_server_address: str = Field(
        "localhost",
        env="MAVSDK_SERVER_ADDRESS",
        description="MAVSDK server address"
    )
    
    mavsdk_server_port: int = Field(
        50051,
        env="MAVSDK_SERVER_PORT",
        description="MAVSDK server port"
    )
    
    connection_timeout_s: float = Field(
        30.0,
        env="DRONE_CONNECTION_TIMEOUT",
        description="Connection timeout in seconds"
    )
    
    # Backend selection
    backend: str = Field(
        "mavsdk",
        env="DRONE_BACKEND",
        description="Drone control backend (mavsdk, pymavlink, etc.)"
    )
    
    # Safety limits from .env
    max_altitude_m: float = Field(
        120.0,
        env="MAX_ALTITUDE_METERS",
        description="Maximum allowed altitude in meters"
    )
    
    max_velocity_m_s: float = Field(
        15.0,
        env="MAX_SPEED_MPS",
        description="Maximum allowed velocity in m/s"
    )
    
    max_distance_from_home_m: float = Field(
        500.0,
        env="MAX_DISTANCE_FROM_HOME",
        description="Maximum distance from home position"
    )
    
    # Battery limits from .env
    min_battery_percent: int = Field(
        20,
        env="MIN_BATTERY_PERCENT",
        description="Minimum battery percentage for operations"
    )
    
    critical_battery_percent: int = Field(
        10,
        env="CRITICAL_BATTERY_PERCENT",
        description="Critical battery percentage (force landing)"
    )
    
    # Multi-drone support
    enable_multi_drone: bool = Field(
        False,
        env="ENABLE_MULTI_DRONE",
        description="Enable multi-drone support"
    )
    
    # Storage for dynamic drone configs
    drone_configs_path: str = Field(
        "data/drone_configs.json",
        env="DRONE_CONFIGS_PATH",
        description="Path to store dynamic drone configurations"
    )
    
    class Config:
        """Pydantic config."""
        env_file = ".env"
        env_file_encoding = "utf-8"


@dataclass
class DroneProfile:
    """Profile for a specific drone."""
    
    drone_id: str
    name: str
    connection_string: str
    backend: str = "mavsdk"
    max_altitude_m: Optional[float] = None
    max_velocity_m_s: Optional[float] = None
    capabilities: List[str] = field(default_factory=list)
    metadata: Dict[str, any] = field(default_factory=dict)
    
    # Additional connection details
    mavsdk_system_address: Optional[str] = None  # For specific MAVSDK system
    connection_type: str = "udp"  # udp, tcp, serial
    ip_address: Optional[str] = None
    port: Optional[int] = None
    baudrate: Optional[int] = None  # For serial connections
    
    def to_dict(self) -> Dict[str, any]:
        """Convert to dictionary for storage."""
        return {
            "drone_id": self.drone_id,
            "name": self.name,
            "connection_string": self.connection_string,
            "backend": self.backend,
            "max_altitude_m": self.max_altitude_m,
            "max_velocity_m_s": self.max_velocity_m_s,
            "capabilities": self.capabilities,
            "metadata": self.metadata,
            "mavsdk_system_address": self.mavsdk_system_address,
            "connection_type": self.connection_type,
            "ip_address": self.ip_address,
            "port": self.port,
            "baudrate": self.baudrate,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, any]) -> "DroneProfile":
        """Create from dictionary."""
        return cls(**data)


class MultiDroneConfig:
    """Configuration for multiple drones with persistence."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize multi-drone config."""
        self.drones: Dict[str, DroneProfile] = {}
        self.active_drone_id: Optional[str] = None
        self.config_path = Path(config_path or drone_config.drone_configs_path)
        self._load_configs()
    
    def _load_configs(self) -> None:
        """Load drone configurations from file."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                    for drone_data in data.get('drones', []):
                        profile = DroneProfile.from_dict(drone_data)
                        self.drones[profile.drone_id] = profile
                    self.active_drone_id = data.get('active_drone_id')
            except Exception as e:
                print(f"Error loading drone configs: {e}")
    
    def _save_configs(self) -> None:
        """Save drone configurations to file."""
        try:
            # Create directory if it doesn't exist
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                'drones': [drone.to_dict() for drone in self.drones.values()],
                'active_drone_id': self.active_drone_id
            }
            
            with open(self.config_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving drone configs: {e}")
    
    def add_drone(self, profile: DroneProfile) -> None:
        """Add a drone profile and persist."""
        self.drones[profile.drone_id] = profile
        self._save_configs()
    
    def update_drone(self, profile: DroneProfile) -> None:
        """Update a drone profile and persist."""
        if profile.drone_id in self.drones:
            self.drones[profile.drone_id] = profile
            self._save_configs()
    
    def remove_drone(self, drone_id: str) -> None:
        """Remove a drone profile and persist."""
        if drone_id in self.drones:
            del self.drones[drone_id]
            if self.active_drone_id == drone_id:
                self.active_drone_id = None
            self._save_configs()
    
    def get_drone(self, drone_id: str) -> Optional[DroneProfile]:
        """Get a drone profile by ID."""
        return self.drones.get(drone_id)
    
    def set_active_drone(self, drone_id: str) -> bool:
        """Set the active drone and persist."""
        if drone_id in self.drones:
            self.active_drone_id = drone_id
            self._save_configs()
            return True
        return False
    
    @property
    def active_drone(self) -> Optional[DroneProfile]:
        """Get the active drone profile."""
        if self.active_drone_id:
            return self.drones.get(self.active_drone_id)
        return None
    
    def create_default_profile(self) -> DroneProfile:
        """Create a default drone profile from environment config."""
        return DroneProfile(
            drone_id="default",
            name="Default Drone",
            connection_string=drone_config.default_connection_string,
            backend=drone_config.backend,
            max_altitude_m=drone_config.max_altitude_m,
            max_velocity_m_s=drone_config.max_velocity_m_s,
            capabilities=["telemetry", "offboard", "mission"],
            mavsdk_system_address=f"{drone_config.mavsdk_server_address}:{drone_config.mavsdk_server_port}"
        )


# Global configuration instances
drone_config = DroneConnectionConfig()
multi_drone_config = MultiDroneConfig()