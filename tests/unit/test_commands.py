# tests/unit/test_commands.py
# ===================================

"""Test command implementations."""

import pytest
import asyncio
from unittest.mock import AsyncMock

from dronesphere.commands.takeoff import TakeoffCommand
from dronesphere.commands.land import LandCommand
from dronesphere.commands.wait import WaitCommand
from dronesphere.core.models import DroneState


class TestTakeoffCommand:
    """Test takeoff command."""
    
    @pytest.mark.asyncio
    async def test_successful_takeoff(self, mock_backend):
        """Test successful takeoff."""
        mock_backend.get_state.return_value = DroneState.DISARMED
        mock_backend.is_armed.return_value = False
        
        command = TakeoffCommand("takeoff", {"altitude": 10.0})
        result = await command.run(mock_backend, altitude=10.0)
        
        assert result.success is True
        assert "10" in result.message
        mock_backend.arm.assert_called_once()
        mock_backend.takeoff.assert_called_once_with(10.0)
        
    @pytest.mark.asyncio
    async def test_takeoff_already_flying(self, mock_backend):
        """Test takeoff when already flying."""
        mock_backend.get_state.return_value = DroneState.FLYING
        
        command = TakeoffCommand("takeoff", {"altitude": 10.0})
        result = await command.run(mock_backend, altitude=10.0)
        
        assert result.success is False
        assert "already airborne" in result.message
        mock_backend.arm.assert_not_called()
        mock_backend.takeoff.assert_not_called()
        
    @pytest.mark.asyncio
    async def test_takeoff_disconnected(self, mock_backend):
        """Test takeoff when disconnected."""
        mock_backend.get_state.return_value = DroneState.DISCONNECTED
        
        command = TakeoffCommand("takeoff", {"altitude": 10.0})
        result = await command.run(mock_backend, altitude=10.0)
        
        assert result.success is False
        assert "disconnected" in result.message
        
    @pytest.mark.asyncio
    async def test_takeoff_cancellation(self, mock_backend):
        """Test takeoff cancellation."""
        mock_backend.get_state.return_value = DroneState.DISARMED
        mock_backend.is_armed.return_value = False
        
        command = TakeoffCommand("takeoff", {"altitude": 10.0})
        
        # Cancel immediately
        await command.cancel()
        
        result = await command.run(mock_backend, altitude=10.0)
        
        assert result.success is False
        assert "cancelled" in result.message.lower()


class TestLandCommand:
    """Test land command."""
    
    @pytest.mark.asyncio
    async def test_successful_land(self, mock_backend):
        """Test successful landing."""
        mock_backend.get_state.return_value = DroneState.FLYING
        
        command = LandCommand("land", {})
        result = await command.run(mock_backend)
        
        assert result.success is True
        assert "successfully" in result.message.lower()
        mock_backend.land.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_land_already_grounded(self, mock_backend):
        """Test landing when already on ground."""
        mock_backend.get_state.return_value = DroneState.DISARMED
        
        command = LandCommand("land", {})
        result = await command.run(mock_backend)
        
        assert result.success is True
        assert "already on ground" in result.message
        mock_backend.land.assert_not_called()
        
    @pytest.mark.asyncio
    async def test_land_disconnected(self, mock_backend):
        """Test landing when disconnected."""
        mock_backend.get_state.return_value = DroneState.DISCONNECTED
        
        command = LandCommand("land", {})
        result = await command.run(mock_backend)
        
        assert result.success is False
        assert "disconnected" in result.message


class TestWaitCommand:
    """Test wait command."""
    
    @pytest.mark.asyncio
    async def test_successful_wait(self, mock_backend):
        """Test successful wait."""
        command = WaitCommand("wait", {"seconds": 0.1})
        result = await command.run(mock_backend, seconds=0.1)
        
        assert result.success is True
        assert "0.1" in result.message
        assert result.duration >= 0.1
        
    @pytest.mark.asyncio
    async def test_wait_cancellation(self, mock_backend):
        """Test wait cancellation."""
        command = WaitCommand("wait", {"seconds": 10.0})
        
        # Start wait and cancel after short delay
        async def cancel_after_delay():
            await asyncio.sleep(0.1)
            await command.cancel()
            
        cancel_task = asyncio.create_task(cancel_after_delay())
        result = await command.run(mock_backend, seconds=10.0)
        
        await cancel_task
        
        assert result.success is False
        assert "cancelled" in result.message.lower()
        assert result.duration < 1.0  # Should be much less than 10s