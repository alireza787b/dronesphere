"""Basic unit tests for command system."""

import pytest

from dronesphere.commands.base import BaseCommand
from dronesphere.commands.registry import get_command_registry


def test_command_registry():
    """Test command registry loading."""
    registry = get_command_registry()
    assert registry is not None


def test_command_registry_basic_commands():
    """Test that basic commands are registered."""
    from dronesphere.commands.registry import load_command_library

    load_command_library()
    registry = get_command_registry()

    # Check basic commands are loaded
    commands = list(registry._commands.keys())
    assert "takeoff" in commands
    assert "land" in commands
    assert "wait" in commands


def test_base_command_structure():
    """Test base command class structure."""

    # Check BaseCommand has required methods
    assert hasattr(BaseCommand, "run")
    assert hasattr(BaseCommand, "validate_parameters")


@pytest.mark.asyncio
async def test_command_creation():
    """Test command creation from registry."""
    from dronesphere.commands.registry import get_command_registry, load_command_library

    load_command_library()
    registry = get_command_registry()

    # Test creating a command
    if "wait" in registry._commands:
        command = registry.create_command("wait", {"duration": 1.0})
        assert command is not None
        assert hasattr(command, "parameters")
