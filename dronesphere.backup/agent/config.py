"""Agent-specific configuration.

This module provides configuration settings for the DroneSphere agent service,
including network, hardware, and communication settings.
"""

from pydantic_settings import BaseSettings
from typing import Dict, Any


class AgentSettings(BaseSettings):
    """Agent configuration settings."""
    
    # Network settings
    host: str = "0.0.0.0"
    port: int = 8001
    
    # Hardware settings  
    drone_connection_string: str = "udp://:14540"
    telemetry_update_interval: float = 0.25
    telemetry_backend: str = "mavsdk"
    
    # Agent behavior
    heartbeat_interval: float = 30.0
    command_timeout: float = 300.0
    
    # Server communication
    server_host: str = "127.0.0.1"
    server_port: int = 8002
    
    class Config:
        env_prefix = "AGENT_"
        case_sensitive = False


def get_agent_settings() -> AgentSettings:
    """Get agent settings instance."""
    return AgentSettings()
