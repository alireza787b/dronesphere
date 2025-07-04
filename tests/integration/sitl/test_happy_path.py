# tests/integration/sitl/test_happy_path.py
# ===================================

"""SITL happy path integration test."""

import pytest
import asyncio
import httpx

from dronesphere.server.client import DroneSphereClient
from dronesphere.core.models import CommandRequest, DroneState


@pytest.mark.sitl
@pytest.mark.slow
class TestSITLIntegration:
    """Test SITL integration."""
    
    @pytest.mark.asyncio
    async def test_full_mission_sequence(self):
        """Test complete mission: takeoff → wait → land."""
        # This test requires SITL to be running
        client = DroneSphereClient("http://localhost:8000")
        
        try:
            # Wait for system to be ready
            for _ in range(30):  # Wait up to 30 seconds
                try:
                    health = await client.health_check()
                    ready = await client.readiness_check()
                    if health.success and ready.success:
                        break
                except httpx.RequestError:
                    pass
                await asyncio.sleep(1.0)
            else:
                pytest.skip("System not ready - SITL not running?")
            
            # Check initial status
            status = await client.get_drone_status(1)
            assert status.drone_id == 1
            
            # Execute mission sequence
            response = await client.takeoff_wait_land(
                drone_id=1,
                altitude=5.0,
                wait_time=2.0
            )
            
            assert response.success
            assert response.command_id is not None
            
            # Monitor execution
            max_wait = 120  # 2 minutes max
            completed = False
            
            for _ in range(max_wait):
                status = await client.get_drone_status(1)
                
                # Check if back on ground (mission complete)
                if status.state in [DroneState.DISARMED, DroneState.CONNECTED]:
                    if status.current_command is None:
                        completed = True
                        break
                        
                await asyncio.sleep(1.0)
                
            assert completed, "Mission did not complete within timeout"
            
            # Verify final state
            final_status = await client.get_drone_status(1)
            assert final_status.state in [DroneState.DISARMED, DroneState.CONNECTED]
            assert final_status.current_command is None
            
        finally:
            await client.close()
            
    @pytest.mark.asyncio
    async def test_telemetry_streaming(self):
        """Test telemetry data availability."""
        client = DroneSphereClient("http://localhost:8000")
        
        try:
            # Check telemetry availability
            telemetry = await client.get_telemetry(1)
            
            assert telemetry.drone_id == 1
            assert telemetry.state is not None
            assert telemetry.timestamp is not None
            
            # Check position data
            if telemetry.position:
                assert isinstance(telemetry.position.latitude, (int, float))
                assert isinstance(telemetry.position.longitude, (int, float))
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 503:
                pytest.skip("Telemetry not available")
            raise
        finally:
            await client.close()