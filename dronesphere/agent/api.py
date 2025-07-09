"""Agent FastAPI application - single drone operations.

This module provides the FastAPI application for the DroneSphere agent,
handling single drone control and monitoring operations.
"""

import asyncio
import time

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from dronesphere.core.errors import CommandValidationError
from dronesphere.core.logging import get_logger
from dronesphere.core.models import (
    APIResponse,
    CommandEnvelope,
    CommandSequence,
    DroneStatus,
)

from .config import get_agent_settings
from .instance import get_agent  # Use instance module instead of main

logger = get_logger(__name__)
settings = get_agent_settings()

# Create FastAPI app
app = FastAPI(
    title="DroneSphere Agent API",
    description="Single drone control and monitoring",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/ping")
async def ping():
    """Agent connectivity check."""
    return {"status": "ok", "timestamp": time.time(), "agent_id": get_agent().drone_id}


@app.get("/health")
async def health():
    """Non-blocking health check that works during mission execution."""
    health_start_time = time.time()

    try:
        agent = get_agent()

        if not agent:
            return {
                "status": "unhealthy",
                "agent": "not_initialized",
                "timestamp": time.time(),
                "response_time": time.time() - health_start_time,
            }

        # Basic connection check (fast)
        if not agent.connection or not agent.connection.connected:
            return {
                "status": "unhealthy",
                "agent": "ok",
                "hardware": "disconnected",
                "drone_id": agent.drone_id,
                "timestamp": time.time(),
                "response_time": time.time() - health_start_time,
            }

        # Non-blocking status collection with minimal backend calls
        drone_state = "unknown"
        hardware_status = "ok"
        health_details = {}

        try:
            # Quick state check - this should be fast
            drone_state = await asyncio.wait_for(
                agent.connection.get_state(), timeout=0.5  # Very short timeout
            )

            # Skip telemetry during mission execution to avoid blocking
            runner_status = "ok" if agent.runner else "not_initialized"
            queue_size = agent.runner.get_queue_size() if agent.runner else 0
            current_command = (
                agent.runner.get_current_execution() if agent.runner else None
            )

            # If mission is running, use simplified health check
            if current_command or queue_size > 0:
                health_details = {
                    "mission_active": True,
                    "telemetry_check": "skipped_during_mission",
                }
                hardware_status = "mission_active"
            else:
                # Full telemetry check only when idle
                try:
                    telemetry = await asyncio.wait_for(
                        agent.connection.get_telemetry(), timeout=1.0
                    )

                    if telemetry:
                        health_details = {
                            "mission_active": False,
                            "health_all_ok": telemetry.health_all_ok,
                            "connection_ok": telemetry.connection_ok,
                            "armed": telemetry.armed,
                        }

                        if not telemetry.health_all_ok:
                            hardware_status = "degraded"
                    else:
                        hardware_status = "no_telemetry"

                except asyncio.TimeoutError:
                    health_details = {"telemetry_check": "timeout"}
                    hardware_status = "slow_response"

        except asyncio.TimeoutError:
            drone_state = "timeout"
            hardware_status = "timeout"
            health_details = {"error": "state_check_timeout"}
        except Exception as e:
            logger.warning("health_check_error", error=str(e))
            drone_state = "error"
            hardware_status = "error"
            health_details = {"error": str(e)}

        # Overall status determination
        if hardware_status in ["error", "timeout"]:
            overall_status = "unhealthy"
        elif hardware_status in ["mission_active", "slow_response"]:
            overall_status = "busy"  # New status for active missions
        elif hardware_status == "degraded":
            overall_status = "degraded"
        else:
            overall_status = "healthy"

        response_time = time.time() - health_start_time

        return {
            "status": overall_status,
            "agent": "ok",
            "hardware": hardware_status,
            "runner": runner_status if "runner_status" in locals() else "unknown",
            "drone_id": agent.drone_id,
            "drone_state": drone_state,
            "queue_size": queue_size if "queue_size" in locals() else 0,
            "current_command": (
                current_command.id
                if "current_command" in locals() and current_command
                else None
            ),
            "health_details": health_details,
            "timestamp": time.time(),
            "response_time": response_time,
        }

    except Exception as e:
        response_time = time.time() - health_start_time
        logger.error("health_check_critical_error", error=str(e))

        return {
            "status": "unhealthy",
            "agent": "error",
            "hardware": "unknown",
            "error": str(e),
            "timestamp": time.time(),
            "response_time": response_time,
        }


@app.get("/status")
async def get_status():
    """Get current drone status."""
    try:
        agent = get_agent()

        if not agent.connection:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Drone not connected",
            )

        state = await agent.connection.get_state()
        current_execution = (
            agent.runner.get_current_execution() if agent.runner else None
        )
        queue_length = agent.runner.get_queue_size() if agent.runner else 0

        # Get last telemetry timestamp
        telemetry = await agent.connection.get_telemetry()
        last_telemetry = telemetry.timestamp if telemetry else None

        health_status = "ok" if agent.connection.connected else "disconnected"
        if telemetry and not telemetry.health_all_ok:
            health_status = "degraded"

        return DroneStatus(
            drone_id=agent.drone_id,
            state=state,
            current_command=current_execution,
            queue_length=queue_length,
            last_telemetry=last_telemetry,
            health_status=health_status,
        )

    except Exception as e:
        logger.error("get_status_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get status: {str(e)}",
        )


@app.get("/telemetry")
async def get_telemetry():
    """Get current drone telemetry."""
    try:
        agent = get_agent()

        if not agent.connection:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Drone not connected",
            )

        telemetry = await agent.connection.get_telemetry()

        if not telemetry:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Telemetry not available",
            )

        return telemetry

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_telemetry_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get telemetry: {str(e)}",
        )


@app.get("/telemetry/position")
async def get_telemetry_position():
    """Get current drone position data specifically."""
    try:
        agent = get_agent()

        if not agent.connection:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Drone not connected",
            )

        telemetry = await agent.connection.get_telemetry()

        if not telemetry or not telemetry.position:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Position data not available",
            )

        # Return position data specifically
        return {
            "drone_id": agent.drone_id,
            "position": telemetry.position.dict(),
            "timestamp": telemetry.timestamp,
            "connection_ok": telemetry.connection_ok,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_position_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get position: {str(e)}",
        )


@app.get("/telemetry/state")
async def get_telemetry_state():
    """Get current drone state specifically."""
    try:
        agent = get_agent()

        if not agent.connection:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Drone not connected",
            )

        state = await agent.connection.get_state()
        telemetry = await agent.connection.get_telemetry()

        return {
            "drone_id": agent.drone_id,
            "state": state,
            "armed": telemetry.armed if telemetry else False,
            "health_all_ok": telemetry.health_all_ok if telemetry else False,
            "timestamp": telemetry.timestamp if telemetry else time.time(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_state_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get state: {str(e)}",
        )


@app.post("/commands")
async def execute_commands(command_sequence: CommandSequence):
    """Execute command sequence on this drone."""
    try:
        agent = get_agent()

        if not agent.runner:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Command runner not available",
            )

        logger.info(
            "command_request_received", sequence_length=len(command_sequence.sequence)
        )

        # Create command envelope
        envelope = CommandEnvelope(
            drone_id=agent.drone_id, sequence=command_sequence.sequence
        )

        # Enqueue command
        command_id = await agent.runner.enqueue_command(envelope)

        # Estimate duration
        estimated_duration = len(command_sequence.sequence) * 30

        logger.info(
            "command_accepted",
            command_id=command_id,
            estimated_duration=estimated_duration,
        )

        # FIX: Return proper JSON response
        return {
            "success": True,
            "message": "Command sequence accepted",
            "command_id": command_id,
            "estimated_duration": estimated_duration,
        }

    except CommandValidationError as e:
        logger.warning("command_validation_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("command_execution_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Command execution failed: {str(e)}",
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


@app.post("/emergency_stop")
async def emergency_stop():
    """Execute emergency stop."""
    try:
        agent = get_agent()

        logger.warning("emergency_stop_requested")

        if not agent.connection:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Drone not connected",
            )

        # Stop runner and emergency stop drone
        if agent.runner:
            await agent.runner.stop()

        await agent.connection.emergency_stop()

        # Restart runner
        if agent.runner:
            await agent.runner.start()

        logger.warning("emergency_stop_executed")

        return APIResponse(success=True, message="Emergency stop executed")

    except Exception as e:
        logger.error("emergency_stop_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Emergency stop failed: {str(e)}",
        )
