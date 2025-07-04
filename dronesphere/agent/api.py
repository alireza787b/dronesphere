"""Agent HTTP API for server communication."""

from fastapi import FastAPI
from typing import Optional

from ..core.models import DroneStatus, Telemetry
from .main import get_agent

# Create agent API
agent_api = FastAPI(title="DroneSphere Agent API")

@agent_api.get("/drones")
async def list_drones():
    """List connected drones."""
    agent = get_agent()
    return {"drones": list(agent.connections.keys())}

@agent_api.get("/drones/{drone_id}/status")
async def get_drone_status(drone_id: int) -> DroneStatus:
    """Get drone status."""
    agent = get_agent()
    connection = agent.get_connection(drone_id)
    runner = agent.get_runner(drone_id)
    
    state = await connection.get_state()
    current_execution = runner.get_current_execution()
    telemetry = await connection.get_telemetry()
    
    return DroneStatus(
        drone_id=drone_id,
        state=state,
        current_command=current_execution,
        queue_length=runner.get_queue_size(),
        last_telemetry=telemetry.timestamp if telemetry else None,
        health_status="ok" if connection.connected else "disconnected"
    )

@agent_api.get("/drones/{drone_id}/telemetry")
async def get_drone_telemetry(drone_id: int) -> Telemetry:
    """Get drone telemetry."""
    agent = get_agent()
    connection = agent.get_connection(drone_id)
    return await connection.get_telemetry()

@agent_api.post("/drones/{drone_id}/commands")
async def execute_command(drone_id: int, command_sequence: dict):
    """Execute command sequence."""
    agent = get_agent()
    runner = agent.get_runner(drone_id)
    
    from ..core.models import CommandEnvelope, CommandRequest
    
    envelope = CommandEnvelope(
        drone_id=drone_id,
        sequence=[CommandRequest(**cmd) for cmd in command_sequence["sequence"]]
    )
    
    command_id = await runner.enqueue_command(envelope)
    return {"command_id": command_id, "success": True}
