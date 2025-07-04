# tests/unit/test_config.py
# ===================================

"""Test configuration."""

import pytest
import tempfile
from pathlib import Path

from dronesphere.core.config import Settings, LoggingConfig, AgentConfig


class TestSettings:
    """Test settings configuration."""
    
    def test_default_settings(self):
        """Test default settings."""
        settings = Settings()
        
        assert settings.debug is False
        assert settings.testing is False
        assert settings.logging.level == "INFO"
        assert settings.agent.port == 8001
        assert settings.server.port == 8000
        
    def test_nested_config(self):
        """Test nested configuration."""
        settings = Settings(
            logging={"level": "DEBUG", "format": "text"},
            agent={"port": 9001}
        )
        
        assert settings.logging.level == "DEBUG"
        assert settings.logging.format == "text"
        assert settings.agent.port == 9001
        assert settings.server.port == 8000  # Unchanged
        
    def test_path_resolution(self):
        """Test path resolution."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(
                paths={
                    "shared_config_path": temp_dir,
                    "command_library_path": f"{temp_dir}/commands"
                }
            )
            
            # Paths should be resolved to absolute paths
            assert settings.paths.shared_config_path.is_absolute()
            assert settings.paths.command_library_path.is_absolute()