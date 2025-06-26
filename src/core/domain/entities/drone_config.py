"""Drone configuration entity for persistent storage."""

from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime

from src.shared.domain.entity import Entity


@dataclass
class DroneConfig(Entity):
    """Persistent drone configuration entity."""
    
    drone_id: str
    name: str
    connection_type: str  # udp, tcp, serial
    connection_string: str
    backend: str
    
    # Connection details
    ip_address: Optional[str] = None
    port: Optional[int] = None
    baudrate: Optional[int] = None
    mavsdk_system_address: Optional[str] = None
    
    # Limits
    max_altitude_m: Optional[float] = None
    max_velocity_m_s: Optional[float] = None
    max_distance_from_home_m: Optional[float] = None
    
    # Capabilities
    capabilities: List[str] = None
    
    # Metadata
    metadata: Dict[str, any] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_connected_at: Optional[datetime] = None
    
    # Status
    is_active: bool = True
    is_default: bool = False
    
    def __post_init__(self):
        """Initialize defaults."""
        if self.capabilities is None:
            self.capabilities = []
        if self.metadata is None:
            self.metadata = {}
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()