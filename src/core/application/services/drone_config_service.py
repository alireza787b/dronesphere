"""Service for managing drone configurations."""

from typing import List, Optional
from datetime import datetime

from src.core.domain.entities.drone_config import DroneConfig
from src.config.drone_config import DroneProfile, multi_drone_config


class DroneConfigService:
    """Service for managing drone configurations.
    
    This service provides a layer between the domain and infrastructure,
    allowing for both file-based and database storage of drone configs.
    """
    
    def __init__(self):
        """Initialize service."""
        self._configs = multi_drone_config
    
    async def create_drone_config(
        self,
        drone_id: str,
        name: str,
        connection_string: str,
        backend: str = "mavsdk",
        **kwargs
    ) -> DroneConfig:
        """Create a new drone configuration.
        
        Args:
            drone_id: Unique identifier
            name: Display name
            connection_string: Connection string (e.g., "udp://:14540")
            backend: Backend type
            **kwargs: Additional configuration
            
        Returns:
            Created drone configuration
        """
        # Create profile
        profile = DroneProfile(
            drone_id=drone_id,
            name=name,
            connection_string=connection_string,
            backend=backend,
            **kwargs
        )
        
        # Add to multi-drone config
        self._configs.add_drone(profile)
        
        # Create entity (for future database storage)
        config = DroneConfig(
            id=drone_id,
            drone_id=drone_id,
            name=name,
            connection_type=kwargs.get('connection_type', 'udp'),
            connection_string=connection_string,
            backend=backend,
            ip_address=kwargs.get('ip_address'),
            port=kwargs.get('port'),
            max_altitude_m=kwargs.get('max_altitude_m'),
            max_velocity_m_s=kwargs.get('max_velocity_m_s'),
            capabilities=kwargs.get('capabilities', []),
            metadata=kwargs.get('metadata', {})
        )
        
        return config
    
    async def get_drone_config(self, drone_id: str) -> Optional[DroneConfig]:
        """Get drone configuration by ID."""
        profile = self._configs.get_drone(drone_id)
        if not profile:
            return None
        
        # Convert to entity
        return DroneConfig(
            id=profile.drone_id,
            drone_id=profile.drone_id,
            name=profile.name,
            connection_type=profile.connection_type,
            connection_string=profile.connection_string,
            backend=profile.backend,
            ip_address=profile.ip_address,
            port=profile.port,
            max_altitude_m=profile.max_altitude_m,
            max_velocity_m_s=profile.max_velocity_m_s,
            capabilities=profile.capabilities,
            metadata=profile.metadata
        )
    
    async def list_drone_configs(self) -> List[DroneConfig]:
        """List all drone configurations."""
        configs = []
        for profile in self._configs.drones.values():
            config = await self.get_drone_config(profile.drone_id)
            if config:
                configs.append(config)
        return configs
    
    async def update_drone_config(
        self,
        drone_id: str,
        **updates
    ) -> Optional[DroneConfig]:
        """Update drone configuration."""
        profile = self._configs.get_drone(drone_id)
        if not profile:
            return None
        
        # Update profile
        for key, value in updates.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        
        profile.metadata['updated_at'] = datetime.utcnow().isoformat()
        self._configs.update_drone(profile)
        
        return await self.get_drone_config(drone_id)
    
    async def delete_drone_config(self, drone_id: str) -> bool:
        """Delete drone configuration."""
        if self._configs.get_drone(drone_id):
            self._configs.remove_drone(drone_id)
            return True
        return False
    
    async def set_active_drone(self, drone_id: str) -> bool:
        """Set active drone."""
        return self._configs.set_active_drone(drone_id)
    
    async def get_active_drone(self) -> Optional[DroneConfig]:
        """Get active drone configuration."""
        if self._configs.active_drone:
            return await self.get_drone_config(self._configs.active_drone.drone_id)
        return None