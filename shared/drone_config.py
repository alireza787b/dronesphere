# shared/drone_config.py
"""
Dynamic drone configuration loader for DroneSphere fleet management.

Loads drone definitions from YAML configuration file and provides
a clean API for accessing drone metadata and connection details.
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class DroneConfig:
    """Represents configuration for a single drone."""

    def __init__(self, config_data: Dict[str, Any]):
        """Initialize drone configuration from dictionary."""
        self.raw_config = config_data
        self.id = config_data["id"]
        self.name = config_data["name"]
        self.description = config_data["description"]
        self.type = config_data["type"]
        self.status = config_data["status"]

        # Connection details
        self.connection = config_data["connection"]
        self.ip = self.connection["ip"]
        self.port = self.connection["port"]
        self.protocol = self.connection["protocol"]
        # Auto-generate endpoint from ip:port
        self.endpoint = f"{self.ip}:{self.port}"

        # Hardware specifications
        self.hardware = config_data["hardware"]
        self.model = self.hardware["model"]
        self.firmware = self.hardware["firmware"]
        self.capabilities = self.hardware["capabilities"]
        self.max_altitude = self.hardware["max_altitude"]
        self.max_speed = self.hardware["max_speed"]
        self.battery_capacity = self.hardware["battery_capacity"]

        # Metadata
        self.metadata = config_data["metadata"]
        self.location = self.metadata["location"]
        self.origin_gps = self.metadata["origin_gps"]
        self.team = self.metadata["team"]
        self.priority = self.metadata["priority"]
        self.notes = self.metadata["notes"]

    @property
    def is_active(self) -> bool:
        """Check if drone is marked as active."""
        return self.status == "active"

    @property
    def is_simulation(self) -> bool:
        """Check if drone is a simulation."""
        return self.type == "simulation"

    @property
    def is_hardware(self) -> bool:
        """Check if drone is real hardware."""
        return self.type == "hardware"

    @property
    def full_endpoint(self) -> str:
        """Get full HTTP endpoint URL."""
        return f"{self.protocol}://{self.endpoint}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "type": self.type,
            "status": self.status,
            "connection": {
                "ip": self.ip,
                "port": self.port,
                "protocol": self.protocol,
                "endpoint": self.endpoint,
                "full_url": self.full_endpoint,
            },
            "hardware": self.hardware,
            "metadata": self.metadata,
        }


class FleetConfig:
    """Manages the entire drone fleet configuration."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize fleet configuration.

        Args:
            config_path: Path to drones.yaml file. If None, uses default location.
        """
        if config_path is None:
            config_path = project_root / "shared" / "drones.yaml"

        self.config_path = Path(config_path)
        self.config_data = self._load_config()
        self.drones = self._load_drones()

        # Fleet metadata
        self.fleet_info = self.config_data["fleet"]
        self.fleet_name = self.fleet_info["name"]
        self.fleet_version = self.fleet_info["version"]
        self.fleet_description = self.fleet_info["description"]

        # Fleet settings
        self.fleet_settings = self.config_data["fleet_settings"]
        self.defaults = self.config_data["fleet"]["defaults"]
        self.environments = self.config_data["environments"]

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Drone configuration file not found: {self.config_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in drone configuration: {e}")

    def _load_drones(self) -> Dict[int, DroneConfig]:
        """Load drone configurations."""
        drones = {}
        for drone_id, drone_data in self.config_data["drones"].items():
            drone_config = DroneConfig(drone_data)
            drones[drone_config.id] = drone_config
        return drones

    def get_drone(self, drone_id: int) -> Optional[DroneConfig]:
        """Get drone configuration by ID."""
        return self.drones.get(drone_id)

    def get_active_drones(self) -> List[DroneConfig]:
        """Get list of active drones."""
        return [drone for drone in self.drones.values() if drone.is_active]

    def get_simulation_drones(self) -> List[DroneConfig]:
        """Get list of simulation drones."""
        return [drone for drone in self.drones.values() if drone.is_simulation]

    def get_hardware_drones(self) -> List[DroneConfig]:
        """Get list of hardware drones."""
        return [drone for drone in self.drones.values() if drone.is_hardware]

    def get_drones_by_team(self, team: str) -> List[DroneConfig]:
        """Get drones assigned to specific team."""
        return [drone for drone in self.drones.values() if drone.team == team]

    def get_registry_dict(self) -> Dict[int, str]:
        """Get drone registry in the format expected by server (id: endpoint)."""
        return {drone.id: drone.endpoint for drone in self.drones.values()}

    def get_active_registry_dict(self) -> Dict[int, str]:
        """Get registry for active drones only."""
        return {drone.id: drone.endpoint for drone in self.get_active_drones()}

    def reload_config(self) -> None:
        """Reload configuration from file (for dynamic updates)."""
        self.config_data = self._load_config()
        self.drones = self._load_drones()
        print(f"🔄 Reloaded drone configuration: {len(self.drones)} drones")

    def to_dict(self) -> Dict[str, Any]:
        """Convert fleet configuration to dictionary for API responses."""
        return {
            "fleet": self.fleet_info,
            "drones": {str(drone_id): drone.to_dict() for drone_id, drone in self.drones.items()},
            "fleet_settings": self.fleet_settings,
            "environments": self.environments,
            "statistics": {
                "total_drones": len(self.drones),
                "active_drones": len(self.get_active_drones()),
                "simulation_drones": len(self.get_simulation_drones()),
                "hardware_drones": len(self.get_hardware_drones()),
            },
        }


# Global fleet configuration instance
_fleet_config: Optional[FleetConfig] = None


def get_fleet_config() -> FleetConfig:
    """Get the global fleet configuration instance."""
    global _fleet_config
    if _fleet_config is None:
        _fleet_config = FleetConfig()
    return _fleet_config


def reload_fleet_config() -> FleetConfig:
    """Reload the global fleet configuration."""
    global _fleet_config
    _fleet_config = FleetConfig()
    return _fleet_config


# Convenience functions for common operations
def get_drone_registry() -> Dict[int, str]:
    """Get drone registry for all drones."""
    return get_fleet_config().get_registry_dict()


def get_active_drone_registry() -> Dict[int, str]:
    """Get drone registry for active drones only."""
    return get_fleet_config().get_active_registry_dict()


def get_drone_info(drone_id: int) -> Optional[Dict[str, Any]]:
    """Get drone information by ID."""
    drone = get_fleet_config().get_drone(drone_id)
    return drone.to_dict() if drone else None


def list_available_drones() -> List[int]:
    """Get list of all available drone IDs."""
    return list(get_fleet_config().drones.keys())


def list_active_drones() -> List[int]:
    """Get list of active drone IDs."""
    return [drone.id for drone in get_fleet_config().get_active_drones()]


if __name__ == "__main__":
    # Test the configuration loader
    try:
        fleet = FleetConfig()
        print(f"✅ Loaded fleet: {fleet.fleet_name}")
        print(f"📊 Total drones: {len(fleet.drones)}")
        print(f"🟢 Active drones: {len(fleet.get_active_drones())}")

        for drone_id, drone in fleet.drones.items():
            status_emoji = "🟢" if drone.is_active else "🔴"
            type_emoji = "🖥️" if drone.is_simulation else "🚁"
            print(
                f"  {status_emoji} {type_emoji} Drone {drone.id}: {drone.name} ({drone.endpoint})"
            )

    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        sys.exit(1)
