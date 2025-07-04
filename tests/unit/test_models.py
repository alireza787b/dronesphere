# tests/unit/test_models.py
# ===================================

"""Test core models."""

import pytest
from datetime import datetime
from pydantic import ValidationError

from dronesphere.core.models import (
    CommandRequest, CommandSequence, Telemetry, Position,
    DroneState, CommandStatus, CommandResult
)


class TestCommandRequest:
    """Test CommandRequest model."""
    
    def test_valid_command_request(self):
        """Test valid command request creation."""
        cmd = CommandRequest(
            name="takeoff",
            params={"altitude": 10.0}
        )
        
        assert cmd.name == "takeoff"
        assert cmd.params["altitude"] == 10.0
        
    def test_command_request_defaults(self):
        """Test command request with defaults."""
        cmd = CommandRequest(name="land")
        
        assert cmd.name == "land"
        assert cmd.params == {}


class TestCommandSequence:
    """Test CommandSequence model."""
    
    def test_valid_sequence(self):
        """Test valid command sequence."""
        sequence = CommandSequence(
            sequence=[
                CommandRequest(name="takeoff", params={"altitude": 10.0}),
                CommandRequest(name="wait", params={"seconds": 3.0}),
                CommandRequest(name="land")
            ]
        )
        
        assert len(sequence.sequence) == 3
        assert sequence.sequence[0].name == "takeoff"
        assert sequence.sequence[2].name == "land"
        
    def test_empty_sequence(self):
        """Test empty sequence."""
        sequence = CommandSequence(sequence=[])
        assert len(sequence.sequence) == 0


class TestTelemetry:
    """Test Telemetry model."""
    
    def test_minimal_telemetry(self):
        """Test telemetry with minimal data."""
        telemetry = Telemetry(
            drone_id=1,
            state=DroneState.CONNECTED
        )
        
        assert telemetry.drone_id == 1
        assert telemetry.state == DroneState.CONNECTED
        assert telemetry.armed is False
        assert isinstance(telemetry.timestamp, datetime)
        
    def test_full_telemetry(self):
        """Test telemetry with all data."""
        position = Position(
            latitude=47.6062,
            longitude=-122.3321,
            altitude_msl=56.0
        )
        
        telemetry = Telemetry(
            drone_id=1,
            state=DroneState.FLYING,
            armed=True,
            position=position
        )
        
        assert telemetry.position.latitude == 47.6062
        assert telemetry.armed is True


class TestPosition:
    """Test Position model."""
    
    def test_gps_position(self):
        """Test GPS position."""
        pos = Position(
            latitude=47.6062,
            longitude=-122.3321,
            altitude_msl=56.0
        )
        
        assert pos.latitude == 47.6062
        assert pos.longitude == -122.3321
        assert pos.altitude_msl == 56.0
        
    def test_local_position(self):
        """Test local NED position."""
        pos = Position(
            north=10.0,
            east=5.0,
            down=-3.0
        )
        
        assert pos.north == 10.0
        assert pos.east == 5.0
        assert pos.down == -3.0


class TestCommandResult:
    """Test CommandResult model."""
    
    def test_successful_result(self):
        """Test successful command result."""
        result = CommandResult(
            success=True,
            message="Command completed successfully",
            duration=5.2
        )
        
        assert result.success is True
        assert result.message == "Command completed successfully"
        assert result.duration == 5.2
        assert result.error is None
        
    def test_failed_result(self):
        """Test failed command result."""
        result = CommandResult(
            success=False,
            message="Command failed",
            error="Connection lost"
        )
        
        assert result.success is False
        assert result.error == "Connection lost"