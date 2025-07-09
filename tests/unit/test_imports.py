"""Basic import tests to catch obvious issues."""



def test_core_imports():
    """Test that core modules can be imported."""
    from dronesphere.core import config, logging, models

    assert config is not None
    assert logging is not None
    assert models is not None


def test_agent_imports():
    """Test that agent modules can be imported."""
    from dronesphere.agent import api, config, main

    assert main is not None
    assert config is not None
    assert api is not None


def test_server_imports():
    """Test that server modules can be imported."""
    from dronesphere.server import api, config, main

    assert main is not None
    assert config is not None
    assert api is not None


def test_command_imports():
    """Test that command system can be imported."""
    from dronesphere.commands import base, registry

    assert registry is not None
    assert base is not None
