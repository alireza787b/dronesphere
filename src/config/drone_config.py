"""Drone configuration module.

Handles all drone-related configuration including connections,
limits, and safety parameters.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from pydantic import BaseSettings, Field


class DroneConnectionConfig(BaseSettings):
    """Configuration for drone connections."""
    
    # Default connection settings
    default_connection_string: str = Field(
        "udp://:14540",
        env="DRONE_CONNECTION_STRING",
        description="Default MAVLink connection string"
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
    
    # Safety limits
    max_altitude_m: float = Field(
        120.0,
        env="DRONE_MAX_ALTITUDE",
        description="Maximum allowed altitude in meters"
    )
    
    max_velocity_m_s: float = Field(
        15.0,
        env="DRONE_MAX_VELOCITY",
        description="Maximum allowed velocity in m/s"
    )
    
    max_distance_from_home_m: float = Field(
        500.0,
        env="DRONE_MAX_DISTANCE",
        description="Maximum distance from home position"
    )
    
    # Battery limits
    min_battery_percent: int = Field(
        20,
        env="DRONE_MIN_BATTERY",
        description="Minimum battery percentage for operations"
    )
    
    critical_battery_percent: int = Field(
        10,
        env="DRONE_CRITICAL_BATTERY",
        description="Critical battery percentage (force landing)"
    )
    
    # Multi-drone support
    enable_multi_drone: bool = Field(
        False,
        env="DRONE_ENABLE_MULTI",
        description="Enable multi-drone support"
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


class MultiDroneConfig:
    """Configuration for multiple drones."""
    
    def __init__(self):
        """Initialize multi-drone config."""
        self.drones: Dict[str, DroneProfile] = {}
        self.active_drone_id: Optional[str] = None
    
    def add_drone(self, profile: DroneProfile) -> None:
        """Add a drone profile."""
        self.drones[profile.drone_id] = profile
    
    def remove_drone(self, drone_id: str) -> None:
        """Remove a drone profile."""
        if drone_id in self.drones:
            del self.drones[drone_id]
            if self.active_drone_id == drone_id:
                self.active_drone_id = None
    
    def get_drone(self, drone_id: str) -> Optional[DroneProfile]:
        """Get a drone profile by ID."""
        return self.drones.get(drone_id)
    
    def set_active_drone(self, drone_id: str) -> bool:
        """Set the active drone."""
        if drone_id in self.drones:
            self.active_drone_id = drone_id
            return True
        return False
    
    @property
    def active_drone(self) -> Optional[DroneProfile]:
        """Get the active drone profile."""
        if self.active_drone_id:
            return self.drones.get(self.active_drone_id)
        return None


# Global configuration instance
drone_config = DroneConnectionConfig()
multi_drone_config = MultiDroneConfig()