# agent/src/config/settings.py
"""
Agent Configuration Settings

Manages configuration for the drone agent using Pydantic for validation.
"""

from pathlib import Path

import yaml
from pydantic import BaseSettings, Field, validator


class AgentSettings(BaseSettings):
    """
    Agent configuration settings with validation.

    Settings can be loaded from:
    1. Environment variables (highest priority)
    2. Configuration file
    3. Default values
    """

    # Server connection
    server_url: str = Field(
        default="ws://localhost:8000/ws/agent",
        description="WebSocket URL for control server",
    )
    server_reconnect_interval: int = Field(
        default=5, description="Seconds between reconnection attempts"
    )

    # MAVSDK connection
    mavsdk_server_address: str = Field(
        default="udp://:14540", description="MAVSDK connection string"
    )
    mavsdk_server_port: int = Field(
        default=50051, description="MAVSDK server port for gRPC"
    )

    # Drone settings
    drone_id: str = Field(default="drone_001", description="Unique drone identifier")
    drone_name: str = Field(default="Alpha", description="Human-readable drone name")

    # Telemetry settings
    telemetry_rate: int = Field(default=10, description="Telemetry update rate in Hz")
    telemetry_buffer_size: int = Field(
        default=100, description="Telemetry message buffer size"
    )

    # Safety settings
    max_altitude: float = Field(
        default=50.0, description="Maximum allowed altitude in meters"
    )
    max_speed: float = Field(default=15.0, description="Maximum allowed speed in m/s")
    min_battery_percent: float = Field(
        default=20.0, description="Minimum battery percentage for operations"
    )
    geofence_radius: float = Field(
        default=500.0, description="Geofence radius in meters"
    )

    # Logging
    log_level: str = Field(
        default="INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )
    log_file: Path | None = Field(default=None, description="Optional log file path")

    # Command execution
    command_timeout: int = Field(
        default=30, description="Default command timeout in seconds"
    )
    command_retry_attempts: int = Field(
        default=3, description="Number of retry attempts for failed commands"
    )

    @validator("log_level")
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level. Must be one of: {valid_levels}")
        return v.upper()

    @validator("max_altitude")
    def validate_max_altitude(cls, v):
        """Validate maximum altitude."""
        if v <= 0 or v > 120:  # FAA limit for small UAS
            raise ValueError("Max altitude must be between 0 and 120 meters")
        return v

    @validator("telemetry_rate")
    def validate_telemetry_rate(cls, v):
        """Validate telemetry rate."""
        if v < 1 or v > 50:
            raise ValueError("Telemetry rate must be between 1 and 50 Hz")
        return v

    class Config:
        """Pydantic configuration."""

        env_prefix = "AGENT_"
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @classmethod
    def from_file(cls, file_path: str) -> "AgentSettings":
        """
        Load settings from YAML file.

        Args:
            file_path: Path to YAML configuration file

        Returns:
            AgentSettings instance
        """
        with open(file_path) as f:
            config_data = yaml.safe_load(f)

        # Override with environment variables
        settings = cls(**config_data)
        return settings

    def to_file(self, file_path: str) -> None:
        """
        Save settings to YAML file.

        Args:
            file_path: Path to save configuration
        """
        with open(file_path, "w") as f:
            yaml.dump(self.dict(), f, default_flow_style=False)

    def get_safety_checks(self) -> dict:
        """Get safety check parameters."""
        return {
            "max_altitude": self.max_altitude,
            "max_speed": self.max_speed,
            "min_battery": self.min_battery_percent,
            "geofence_radius": self.geofence_radius,
        }
