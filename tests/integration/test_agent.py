# tests/integration/test_agent.py
# ===================================

"""Test agent integration."""

import pytest
import asyncio

from dronesphere.agent.connection import DroneConnection
from dronesphere.agent.runner import CommandRunner
from dronesphere.core.models import CommandEnvelope, CommandRequest


class TestAgentIntegration:
    """Test agent integration."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_connection_lifecycle(self, mock_backend, mock_telemetry_provider):
        """Test connection lifecycle."""
        connection = DroneConnection(1)
        
        # Mock the factory to return our mocks
        from dronesphere.backends.base import BackendFactory
        original_create_backend = BackendFactory.create_backend
        original_create_telemetry = BackendFactory.create_telemetry_provider
        
        BackendFactory.create_backend = lambda *args, **kwargs: mock_backend
        BackendFactory.create_telemetry_provider = lambda *args, **kwargs: mock_telemetry_provider
        
        try:
            # Test connection
            await connection.connect()
            assert connection.connected
            
            # Test telemetry
            telemetry = await connection.get_telemetry()
            assert telemetry is not None
            assert telemetry.drone_id == 1
            
            # Test disconnection
            await connection.disconnect()
            assert not connection.connected
            
        finally:
            # Restore factory
            BackendFactory.create_backend = original_create_backend
            BackendFactory.create_telemetry_provider = original_create_telemetry
            
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_command_execution(self, mock_drone_connection, command_registry):
        """Test command execution through runner."""
        runner = CommandRunner(mock_drone_connection)
        await runner.start()
        
        try:
            # Create command envelope
            envelope = CommandEnvelope(
                drone_id=1,
                sequence=[
                    CommandRequest(name="takeoff", params={"altitude": 5.0}),
                    CommandRequest(name="wait", params={"seconds": 0.1}),
                    CommandRequest(name="land")
                ]
            )
            
            # Execute command
            command_id = await runner.enqueue_command(envelope)
            assert command_id == envelope.id
            
            # Wait for execution to complete
            await asyncio.sleep(0.5)
            
            # Check execution history
            execution = runner.get_execution_history(f"{command_id}-0")
            assert execution is not None
            
        finally:
            await runner.stop()