# server/src/server/core/config.py
"""
Server Configuration

Centralized configuration management using Pydantic Settings.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, validator
from pydantic_settings import BaseSettings


class ServerSettings(BaseSettings):
    """
    Server configuration settings.

    Settings are loaded from environment variables with DRONESPHERE_ prefix.
    """

    # Server settings
    host: str = Field(default="0.0.0.0", env="SERVER_HOST")
    port: int = Field(default=8001, env="SERVER_PORT")  # Changed default to 8001
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    # CORS settings
    cors_origins: list[str] = Field(
        default=["http://localhost:3010", "http://localhost:3000"], env="CORS_ORIGINS"
    )

    # Security settings
    secret_key: str = Field(
        default="your-secret-key-here-change-in-production", env="SECRET_KEY"
    )
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration_hours: int = Field(default=24, env="JWT_EXPIRATION_HOURS")

    # LLM settings
    llm_provider: str = Field(default="ollama", env="LLM_PROVIDER")
    ollama_host: str = Field(default="http://localhost:11434", env="OLLAMA_HOST")
    openai_api_key: str | None = Field(default=None, env="OPENAI_API_KEY")
    anthropic_api_key: str | None = Field(default=None, env="ANTHROPIC_API_KEY")
    deepseek_api_key: str | None = Field(default=None, env="DEEPSEEK_API_KEY")
    deepseek_api_base: str = Field(
        default="https://api.deepseek.com/v1", env="DEEPSEEK_API_BASE"
    )

    # Database settings (for future use)
    database_url: str = Field(default="sqlite:///./dronesphere.db", env="DATABASE_URL")

    # WebSocket settings
    ws_heartbeat_interval: int = Field(
        default=30, description="WebSocket heartbeat interval in seconds"
    )
    ws_max_connections: int = Field(
        default=100, description="Maximum WebSocket connections"
    )

    # Command settings
    command_timeout: int = Field(
        default=30, description="Default command timeout in seconds"
    )
    max_command_retries: int = Field(
        default=3, description="Maximum command retry attempts"
    )

    @validator("log_level")
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level. Must be one of: {valid_levels}")
        return v.upper()

    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            # Try to parse as JSON first
            if v.startswith("["):
                try:
                    import json

                    return json.loads(v)
                except:
                    pass
            # Otherwise split by comma
            return [origin.strip() for origin in v.split(",")]
        return v

    class Config:
        """Pydantic configuration."""

        env_prefix = ""  # No prefix
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Allow extra fields from .env

        # Look for .env in parent directory if not found
        if not Path(".env").exists() and Path("../.env").exists():
            env_file = "../.env"


@lru_cache
def get_settings() -> ServerSettings:
    """
    Get cached settings instance.

    Returns:
        ServerSettings instance
    """
    return ServerSettings()
