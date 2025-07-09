"""Server-specific configuration.

This module provides configuration settings for the DroneSphere server service,
including fleet management, network, and coordination settings.
"""


from pydantic_settings import BaseSettings


class ServerSettings(BaseSettings):
    """Server configuration settings."""

    # Network settings
    host: str = "0.0.0.0"
    port: int = 8002

    # Fleet management
    telemetry_cache_interval: float = 1.0
    agent_timeout: float = 10.0
    retry_max_attempts: int = 3
    retry_backoff: float = 1.5

    # CORS settings
    cors_origins: list[str] = ["*"]

    class Config:
        env_prefix = "SERVER_"
        case_sensitive = False


def get_server_settings() -> ServerSettings:
    """Get server settings instance."""
    return ServerSettings()
