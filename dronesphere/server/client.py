"""HTTP client for testing and integration."""

from typing import Dict, List, Optional

import httpx

from ..core.models import (
    APIResponse, CommandAcceptedResponse, CommandRequest, 
    CommandSequence, DroneStatus, Telemetry
)


class DroneSphereClient:
    """HTTP client for DroneSphere API."""
    
    def __init__(self, base_url: str = "http://localhost:8001", timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)
        
    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
        
    async def health_check(self) -> APIResponse:
        """Check API health."""
        response = await self.client.get(f"{self.base_url}/health")
        response.raise_for_status()
        return APIResponse(**response.json())
        
    async def readiness_check(self) -> APIResponse:
        """Check API readiness."""
        response = await self.client.get(f"{self.base_url}/ready")
        response.raise_for_status()
        return APIResponse(**response.json())
        
    async def execute_command(
        self, 
        drone_id: int, 
        sequence: List[CommandRequest]
    ) -> CommandAcceptedResponse:
        """Execute command sequence."""
        command_sequence = CommandSequence(sequence=sequence)
        
        response = await self.client.post(
            f"{self.base_url}/command/{drone_id}",
            json=command_sequence.dict()
        )
        response.raise_for_status()
        return CommandAcceptedResponse(**response.json())
        
    async def get_drone_status(self, drone_id: int) -> DroneStatus:
        """Get drone status."""
        response = await self.client.get(f"{self.base_url}/status/{drone_id}")
        response.raise_for_status()
        return DroneStatus(**response.json())
        
    async def get_telemetry(self, drone_id: int) -> Telemetry:
        """Get drone telemetry."""
        response = await self.client.get(f"{self.base_url}/telemetry/{drone_id}")
        response.raise_for_status()
        return Telemetry(**response.json())
        
    async def get_command_queue(self, drone_id: int) -> APIResponse:
        """Get command queue status."""
        response = await self.client.get(f"{self.base_url}/queue/{drone_id}")
        response.raise_for_status()
        return APIResponse(**response.json())
        
    async def get_command_status(self, command_id: str) -> APIResponse:
        """Get command execution status."""
        response = await self.client.get(f"{self.base_url}/command/{command_id}/status")
        response.raise_for_status()
        return APIResponse(**response.json())
        
    async def emergency_stop(self, drone_id: int) -> APIResponse:
        """Execute emergency stop."""
        response = await self.client.post(f"{self.base_url}/emergency_stop/{drone_id}")
        response.raise_for_status()
        return APIResponse(**response.json())
        
    async def list_drones(self) -> APIResponse:
        """List all drones."""
        response = await self.client.get(f"{self.base_url}/drones")
        response.raise_for_status()
        return APIResponse(**response.json())
        
    # Convenience methods
    async def takeoff(self, drone_id: int, altitude: float = 10.0) -> CommandAcceptedResponse:
        """Execute takeoff command."""
        sequence = [CommandRequest(name="takeoff", params={"altitude": altitude})]
        return await self.execute_command(drone_id, sequence)
        
    async def land(self, drone_id: int) -> CommandAcceptedResponse:
        """Execute land command."""
        sequence = [CommandRequest(name="land")]
        return await self.execute_command(drone_id, sequence)
        
    async def wait(self, drone_id: int, seconds: float) -> CommandAcceptedResponse:
        """Execute wait command."""
        sequence = [CommandRequest(name="wait", params={"seconds": seconds})]
        return await self.execute_command(drone_id, sequence)
        
    async def takeoff_wait_land(
        self, 
        drone_id: int, 
        altitude: float = 10.0, 
        wait_time: float = 3.0
    ) -> CommandAcceptedResponse:
        """Execute complete takeoff → wait → land sequence."""
        sequence = [
            CommandRequest(name="takeoff", params={"altitude": altitude}),
            CommandRequest(name="wait", params={"seconds": wait_time}),
            CommandRequest(name="land")
        ]
        return await self.execute_command(drone_id, sequence)
