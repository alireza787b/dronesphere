"""Basic unit tests for configuration."""

from dronesphere.core.config import get_settings


def test_settings_load():
    """Test that settings can be loaded."""
    settings = get_settings()
    assert settings is not None


def test_agent_config():
    """Test agent configuration loading."""
    from dronesphere.agent.config import get_agent_settings

    agent_settings = get_agent_settings()
    assert agent_settings is not None
    assert hasattr(agent_settings, "port")
    assert hasattr(agent_settings, "drone_connection_string")


def test_server_config():
    """Test server configuration loading."""
    from dronesphere.server.config import get_server_settings

    server_settings = get_server_settings()
    assert server_settings is not None
    assert hasattr(server_settings, "port")
