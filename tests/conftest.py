# tests/conftest.py
# ===================================

"""Test configuration and fixtures."""

import asyncio
import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from dronesphere.agent.connection import DroneConnection
from dronesphere.agent.runner import CommandRunner
from dronesphere.backends.base import AbstractBackend, TelemetryProvider
from dronesphere.commands.registry import get_command_registry, CommandRegistry
from dronesphere.core.config import Settings
from dronesphere.core.models import (
    CommandResult, DroneState, Telemetry, Position, 
    Attitude, Velocity, Battery, GPS
)
from dronesphere.server.client import DroneSphereClient


# Test configuration
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings():
    """Test settings with temporary paths."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create test command files
        commands_path = temp_path / "commands"
        commands_path.mkdir()
        
        takeoff_yaml = commands_path / "takeoff.yaml"
        takeoff_yaml.write_text("""
apiVersion: v1
kind: DroneCommand
metadata:
  name: takeoff
  version: 1.0.0
  category: flight
  tags: [basic]
spec:
  description:
    brief: "Test takeoff command"
  parameters:
    altitude:
      type: float
      default: 10.0
      constraints: {min: 1.0, max: 50.0}
  implementation:
    handler: "dronesphere.commands.takeoff.TakeoffCommand"
    supported_backends: [mavsdk]
    timeout: 30
  telemetry_feedback:
    start: "Taking off..."
    success: "Takeoff complete"
""")

        land_yaml = commands_path / "land.yaml"
        land_yaml.write_text("""
apiVersion: v1
kind: DroneCommand
metadata:
  name: land
  version: 1.0.0
  category: flight
  tags: [basic]
spec:
  description:
    brief: "Test land command"
  parameters: {}
  implementation:
    handler: "dronesphere.commands.land.LandCommand"
    supported_backends: [mavsdk]
    timeout: 60
  telemetry_feedback:
    start: "Landing..."
    success: "Landing complete"
""")
        
        settings = Settings(
            testing=True,
            debug=True,
            paths={
                "shared_config_path": temp_path,
                "command_library_path": commands_path
            },
            logging={"level": "WARNING"},  # Reduce noise in tests
            agent={
                "drone_connection_string": "udp://:14540",
                "telemetry_update_interval": 0.1
            },
            server={
                "host": "127.0.0.1",
                "port": 8001  # Different port for tests
            }
        )
        
        yield settings


@pytest.fixture
def mock_backend():
    """Mock drone backend."""
    backend = MagicMock(spec=AbstractBackend)
    backend.drone_id = 1
    backend.connection_string = "udp://:14540"
    backend.connected = True
    
    # Mock async methods
    backend.connect = AsyncMock()
    backend.disconnect = AsyncMock()
    backend.arm = AsyncMock()
    backend.disarm = AsyncMock()
    backend.takeoff = AsyncMock()
    backend.land = AsyncMock()
    backend.return_to_launch = AsyncMock()
    backend.hold_position = AsyncMock()
    backend.goto_position = AsyncMock()
    backend.set_flight_mode = AsyncMock()
    backend.emergency_stop = AsyncMock()
    
    # Mock state methods
    backend.get_state = AsyncMock(return_value=DroneState.CONNECTED)
    backend.is_armed = AsyncMock(return_value=False)
    backend.get_flight_mode = AsyncMock(return_value="POSCTL")
    
    return backend


@pytest.fixture
def mock_telemetry_provider():
    """Mock telemetry provider."""
    provider = MagicMock(spec=TelemetryProvider)
    provider.drone_id = 1
    provider.connection_string = "udp://:14540"
    provider.connected = True
    
    # Mock async methods
    provider.connect = AsyncMock()
    provider.disconnect = AsyncMock()
    
    # Mock telemetry data
    test_telemetry = Telemetry(
        drone_id=1,
        state=DroneState.CONNECTED,
        armed=False,
        position=Position(
            latitude=47.6062,
            longitude=-122.3321,
            altitude_msl=56.0,
            altitude_relative=0.0
        ),
        attitude=Attitude(
            roll=0.0,
            pitch=0.0,
            yaw=0.0
        ),
        velocity=Velocity(
            ground_speed=0.0,
            north=0.0,
            east=0.0,
            down=0.0
        ),
        battery=Battery(
            voltage=12.6,
            remaining_percent=85.0
        ),
        gps=GPS(
            fix_type=3,
            satellites_visible=12
        ),
        health_all_ok=True,
        calibration_ok=True,
        connection_ok=True
    )
    
    provider.get_telemetry = AsyncMock(return_value=test_telemetry)
    
    return provider


@pytest.fixture
def mock_drone_connection(mock_backend, mock_telemetry_provider):
    """Mock drone connection."""
    connection = MagicMock(spec=DroneConnection)
    connection.drone_id = 1
    connection.backend = mock_backend
    connection.telemetry_provider = mock_telemetry_provider
    connection.connected = True
    
    # Mock async methods
    connection.connect = AsyncMock()
    connection.disconnect = AsyncMock()
    connection.emergency_stop = AsyncMock()
    connection.get_state = AsyncMock(return_value=DroneState.CONNECTED)
    connection.get_telemetry = AsyncMock(return_value=mock_telemetry_provider.get_telemetry.return_value)
    
    return connection


@pytest.fixture
def command_registry(test_settings):
    """Command registry with test commands loaded."""
    registry = CommandRegistry()
    
    # Load test commands from temporary directory
    os.environ["COMMAND_LIBRARY_PATH"] = str(test_settings.paths.command_library_path)
    
    from dronesphere.commands.registry import load_command_library
    load_command_library()
    
    return get_command_registry()


@pytest.fixture
async def command_runner(mock_drone_connection):
    """Command runner with mock connection."""
    runner = CommandRunner(mock_drone_connection)
    await runner.start()
    
    yield runner
    
    await runner.stop()


@pytest.fixture
async def api_client():
    """HTTP client for API testing."""
    client = DroneSphereClient("http://127.0.0.1:8001")
    
    yield client
    
    await client.close()