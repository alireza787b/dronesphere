"""Configuration management for DroneSphere - Clean MAVSDK focus."""

import os
from pathlib import Path
from typing import List, Literal

from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings


class LoggingConfig(BaseModel):
    """Logging configuration."""
    
    level: str = Field(default="INFO", description="Log level")
    format: Literal["json", "text"] = Field(default="json", description="Log format")


class AgentConfig(BaseModel):
    """Agent configuration."""
    
    host: str = Field(default="localhost", description="Agent bind host")
    port: int = Field(default=8002, description="Agent bind port") 
    drone_connection_string: str = Field(
        default="udp://:14540", 
        description="MAVLink connection string"
    )
    telemetry_update_interval: float = Field(
        default=0.25, 
        description="Telemetry update interval in seconds"
    )
    command_timeout: int = Field(
        default=300, 
        description="Default command timeout in seconds"
    )


class ServerConfig(BaseModel):
    """Server configuration."""
    
    host: str = Field(default="0.0.0.0", description="Server bind host")
    port: int = Field(default=8001, description="Server bind port")
    api_prefix: str = Field(default="/api/v1", description="API prefix")
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        description="CORS allowed origins"
    )


class BackendConfig(BaseModel):
    """Backend configuration."""
    
    default_backend: Literal["mavsdk", "pymavlink"] = Field(
        default="mavsdk", 
        description="Default drone backend"
    )
    telemetry_backend: Literal["mavsdk", "pymavlink"] = Field(
        default="mavsdk",
        description="Telemetry backend"
    )


class PathConfig(BaseModel):
    """Path configuration."""
    
    shared_config_path: Path = Field(
        default=Path("./shared"),
        description="Shared configuration directory"
    )
    command_library_path: Path = Field(
        default=Path("./shared/commands"),
        description="Command library directory" 
    )
    
    @validator("shared_config_path", "command_library_path", pre=True)
    def resolve_paths(cls, v):
        """Resolve relative paths."""
        if isinstance(v, str):
            v = Path(v)
        return v.resolve()


class MetricsConfig(BaseModel):
    """Metrics and monitoring configuration."""
    
    enabled: bool = Field(default=True, description="Enable metrics")
    port: int = Field(default=9090, description="Metrics port")
    health_check_interval: int = Field(
        default=10,
        description="Health check interval in seconds"
    )


class Settings(BaseSettings):
    """Main configuration class - Clean and efficient."""
    
    # Core settings
    debug: bool = Field(default=False, description="Debug mode")
    testing: bool = Field(default=False, description="Testing mode")
    
    # Logging
    log_level: str = Field(default="INFO")
    log_format: Literal["json", "text"] = Field(default="json")
    
    # Agent
    agent_host: str = Field(default="localhost")
    agent_port: int = Field(default=8002)
    drone_connection_string: str = Field(default="udp://:14540")
    telemetry_update_interval: float = Field(default=0.25)
    command_timeout: int = Field(default=300)
    
    # Server
    server_host: str = Field(default="0.0.0.0")
    server_port: int = Field(default=8001)
    api_prefix: str = Field(default="/api/v1")
    cors_origins: List[str] = Field(default=["http://localhost:3000", "http://localhost:8080"])
    
    # Backend - Simplified for pure MAVSDK
    default_backend: Literal["mavsdk", "pymavlink"] = Field(default="mavsdk")
    telemetry_backend: Literal["mavsdk", "pymavlink"] = Field(default="mavsdk")
    
    # Paths
    shared_config_path: Path = Field(default=Path("./shared"))
    command_library_path: Path = Field(default=Path("./shared/commands"))
    
    # Metrics
    metrics_enabled: bool = Field(default=True)
    metrics_port: int = Field(default=9090)
    health_check_interval: int = Field(default=10)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"
    
    @property
    def logging(self) -> LoggingConfig:
        """Get logging configuration."""
        return LoggingConfig(
            level=self.log_level,
            format=self.log_format
        )
    
    @property
    def agent(self) -> AgentConfig:
        """Get agent configuration."""
        return AgentConfig(
            host=self.agent_host,
            port=self.agent_port,
            drone_connection_string=self.drone_connection_string,
            telemetry_update_interval=self.telemetry_update_interval,
            command_timeout=self.command_timeout
        )
    
    @property
    def server(self) -> ServerConfig:
        """Get server configuration."""
        return ServerConfig(
            host=self.server_host,
            port=self.server_port,
            api_prefix=self.api_prefix,
            cors_origins=self.cors_origins
        )
    
    @property
    def backend(self) -> BackendConfig:
        """Get backend configuration."""
        return BackendConfig(
            default_backend=self.default_backend,
            telemetry_backend=self.telemetry_backend
        )
    
    @property
    def paths(self) -> PathConfig:
        """Get paths configuration."""
        return PathConfig(
            shared_config_path=self.shared_config_path,
            command_library_path=self.command_library_path
        )
    
    @property
    def metrics(self) -> MetricsConfig:
        """Get metrics configuration."""
        return MetricsConfig(
            enabled=self.metrics_enabled,
            port=self.metrics_port,
            health_check_interval=self.health_check_interval
        )


# Global settings instance
_settings = None

def get_settings() -> Settings:
    """Get the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings():
    """Reset settings for testing."""
    global _settings
    _settings = None
