# server/src/server/api/drones.py
"""
Drones API endpoints

Handles drone management and status.
"""


import structlog
from fastapi import APIRouter, HTTPException

from server.core.drone_manager import DroneManager

logger = structlog.get_logger()

router = APIRouter()

# Get drone manager instance
drone_manager = DroneManager()


@router.get("/")
async def list_drones():
    """List all connected drones."""
    state = await drone_manager.get_system_state()
    return {"drones": state["drones"]}


@router.get("/{drone_id}")
async def get_drone(drone_id: str):
    """Get specific drone information."""
    state = await drone_manager.get_system_state()

    if drone_id not in state["drones"]:
        raise HTTPException(status_code=404, detail="Drone not found")

    return state["drones"][drone_id]


@router.get("/{drone_id}/telemetry")
async def get_drone_telemetry(drone_id: str):
    """Get latest telemetry for a drone."""
    if drone_id not in drone_manager.drones:
        raise HTTPException(status_code=404, detail="Drone not found")

    drone = drone_manager.drones[drone_id]
    return {
        "drone_id": drone_id,
        "telemetry": drone.last_telemetry or {},
        "status": drone.status,
    }
