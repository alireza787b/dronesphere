"""Server FastAPI application - multi-drone coordination.

This module provides the main server API for fleet management, telemetry caching,
and multi-drone coordination operations.
"""

import time

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from dronesphere.core.logging import get_logger
from dronesphere.core.models import APIResponse, CommandSequence

from .config import get_server_settings
from .coordinator import FleetManager, TelemetryCache

logger = get_logger(__name__)
settings = get_server_settings()

# Create FastAPI app
app = FastAPI(
    title="DroneSphere Server API",
    description="Multi-drone coordination and fleet management",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
fleet_manager: FleetManager | None = None
telemetry_cache: TelemetryCache | None = None


@app.on_event("startup")
async def startup():
    """Initialize server components."""
    global fleet_manager, telemetry_cache

    fleet_manager = FleetManager()
    await fleet_manager.start()

    telemetry_cache = TelemetryCache(fleet_manager)
    await telemetry_cache.start()

    logger.info("server_started")


@app.on_event("shutdown")
async def shutdown():
    """Cleanup server components."""
    global fleet_manager, telemetry_cache

    if telemetry_cache:
        await telemetry_cache.stop()

    if fleet_manager:
        await fleet_manager.stop()

    logger.info("server_stopped")


@app.get("/ping")
async def ping():
    """Server connectivity check."""
    return {"status": "ok", "timestamp": time.time(), "service": "dronesphere-server"}


@app.get("/health")
async def health():
    """Server and fleet health check."""
    try:
        if not fleet_manager:
            return {
                "status": "unhealthy",
                "error": "Fleet manager not initialized",
                "timestamp": time.time(),
            }

        total_drones = len(fleet_manager.drones)
        connected_drones = len(fleet_manager.get_connected_drones())

        status_result = "healthy"
        if connected_drones == 0:
            status_result = "unhealthy"
        elif connected_drones < total_drones:
            status_result = "degraded"

        return {
            "status": status_result,
            "server": "ok",
            "fleet": {
                "total_drones": total_drones,
                "connected_drones": connected_drones,
                "disconnected_drones": total_drones - connected_drones,
            },
            "timestamp": time.time(),
        }

    except Exception as e:
        logger.error("health_check_failed", error=str(e))
        return {"status": "unhealthy", "error": str(e), "timestamp": time.time()}


@app.get("/drones")
async def list_drones():
    """List all drones in the fleet."""
    try:
        if not fleet_manager:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Fleet manager not available",
            )

        drones = []
        for drone in fleet_manager.list_drones():
            drones.append(
                {
                    "id": drone.id,
                    "name": drone.name,
                    "type": drone.type,
                    "connected": drone.connected,
                    "health_status": drone.health_status,
                    "last_seen": drone.last_seen,
                    "capabilities": drone.capabilities,
                    "agent": {"host": drone.agent_host, "port": drone.agent_port},
                }
            )

        return APIResponse(
            success=True,
            message="Drone list",
            data={
                "drones": drones,
                "total": len(drones),
                "connected": len([d for d in drones if d["connected"]]),
            },
        )

    except Exception as e:
        logger.error("list_drones_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list drones: {str(e)}",
        )


@app.post("/drones/{drone_id}/commands")
async def send_command_to_drone(drone_id: int, command_sequence: CommandSequence):
    """Send command to specific drone."""
    try:
        if not fleet_manager:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Fleet manager not available",
            )

        logger.info(
            "command_request_received",
            drone_id=drone_id,
            sequence_length=len(command_sequence.sequence),
        )

        result = await fleet_manager.send_command_to_drone(
            drone_id, command_sequence.dict()
        )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Failed to send command to drone {drone_id}",
            )

        logger.info(
            "command_forwarded", drone_id=drone_id, command_id=result.get("command_id")
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error("send_command_failed", drone_id=drone_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send command: {str(e)}",
        )


@app.get("/commands")
async def list_commands():
    """List available commands."""
    try:
        from dronesphere.commands.registry import get_command_registry

        registry = get_command_registry()

        return APIResponse(
            success=True,
            message="Available commands",
            data={
                "commands": registry.list_commands(),
                "total": len(registry.list_commands()),
            },
        )

    except Exception as e:
        logger.error("list_commands_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list commands: {str(e)}",
        )


@app.post("/agents/heartbeat")
async def agent_heartbeat(heartbeat_data: dict):
    """Receive heartbeat from agent."""
    try:
        agent_port = heartbeat_data.get("agent_port")
        timestamp = heartbeat_data.get("timestamp")
        status = heartbeat_data.get("status")

        logger.debug(
            "heartbeat_received",
            agent_port=agent_port,
            status=status,
            timestamp=timestamp,
        )

        return {"status": "acknowledged", "timestamp": time.time()}

    except Exception as e:
        logger.error("heartbeat_processing_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process heartbeat: {str(e)}",
        )
