"""DroneSphere Agent REST API - UPDATED VERSION.

Provides drone control endpoints for command execution, health monitoring,
and telemetry data. Runs on the drone or Raspberry Pi at port 8001.

Path: agent/api.py

CHANGES:
- Updated MAVSDKBackend initialization to use auto-detection
- Fixed startup event to handle boolean return from connect()
- Enhanced health checks with backend health information
- Improved error handling and logging
"""
import os
import sys
import time
from typing import Any, Dict

from fastapi import FastAPI, HTTPException

# Add parent directory to path for shared imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = FastAPI(
    title="DroneSphere Agent",
    version="2.0.0",
    description="Drone control agent for individual drone operations",
)

# Configuration
AGENT_ID = 1  # TODO: Load from config file
VERSION = "2.0.0"

# Global state
backend = None
executor = None
startup_time = time.time()


@app.on_event("startup")
async def startup_event():
    """Initialize agent backend and executor on startup."""
    global backend, executor

    try:
        print(f"Agent {AGENT_ID} starting up...")

        # Import here to avoid circular imports
        from .backends.mavsdk import MAVSDKBackend
        from .executor import CommandExecutor

        # Initialize MAVSDK backend with auto-detection
        backend = MAVSDKBackend()  # Auto-detect connection

        # Try to connect to drone (non-blocking for health checks)
        try:
            connection_success = await backend.connect()
            if connection_success:
                print("✅ MAVSDK backend connected")
            else:
                print("⚠️  MAVSDK connection failed - will retry on first request")
                print("Backend created but not connected - health endpoints will show disconnected")
        except Exception as e:
            print(f"⚠️  MAVSDK connection failed: {e}")
            print("Backend created but not connected - health endpoints will show disconnected")

        # Initialize command executor
        executor = CommandExecutor(backend)
        print("✅ Command executor initialized")

    except Exception as e:
        print(f"Startup error: {e}")
        print("Health endpoints will reflect initialization status")


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Basic health check endpoint.

    Returns:
        Health status with timestamp and agent info
    """
    current_time = time.time()
    uptime = current_time - startup_time

    return {
        "status": "healthy",
        "timestamp": current_time,
        "agent_id": AGENT_ID,
        "version": VERSION,
        "uptime_seconds": round(uptime, 2),
        "backend_connected": backend.connected if backend else False,
        "executor_ready": executor is not None,
    }


@app.get("/ping")
async def ping() -> Dict[str, float]:
    """Simple connectivity test endpoint.

    Returns:
        Timestamp for latency measurement
    """
    return {"pong": time.time()}


@app.get("/health/detailed")
async def detailed_health() -> Dict[str, Any]:
    """Detailed health check for debugging and monitoring.

    Returns:
        Comprehensive system status information
    """
    # Get basic backend info
    backend_info = {
        "connected": backend.connected if backend else False,
        "type": "mavsdk" if backend else None,
        "connection_string": getattr(backend, '_connection_string', None) if backend else None,
    }

    # Try to get enhanced health info if available
    if backend and hasattr(backend, 'health_check'):
        try:
            backend_health = await backend.health_check()
            backend_info.update(backend_health)
        except Exception as e:
            backend_info["health_check_error"] = str(e)

    return {
        "agent": {
            "status": "ok",
            "version": VERSION,
            "id": AGENT_ID,
            "uptime": round(time.time() - startup_time, 2),
        },
        "backend": backend_info,
        "executor": {
            "available": executor is not None,
            "commands": list(executor.command_map.keys()) if executor else [],
        },
        "system": {"python_version": sys.version.split()[0], "platform": sys.platform},
        "timestamp": time.time(),
    }


# Command execution endpoint
@app.post("/commands")
async def execute_commands(request: dict):
    """Execute command sequence.

    Args:
        request: Command request dictionary

    Returns:
        Execution results
    """
    # Import here to avoid circular imports
    from shared.models import Command, CommandMode, CommandRequest, QueueMode

    try:
        # Parse request manually to handle dataclass conversion
        commands_data = request.get("commands", [])
        commands = []

        for cmd_data in commands_data:
            cmd = Command(
                name=cmd_data["name"],
                params=cmd_data.get("params", {}),
                mode=CommandMode(cmd_data.get("mode", "continue")),
            )
            commands.append(cmd)

        queue_mode = QueueMode(request.get("queue_mode", "override"))
        target_drone = request.get("target_drone")

        # Validate target_drone
        if target_drone and target_drone != AGENT_ID:
            raise HTTPException(
                status_code=400,
                detail=f"Wrong drone. This is drone {AGENT_ID}, got target {target_drone}",
            )

        # Default to own ID if missing
        if not target_drone:
            target_drone = AGENT_ID

        # Check if executor is ready
        if not executor:
            raise HTTPException(status_code=503, detail="Command executor not initialized")

        # Check backend connection before executing commands
        if not backend or not backend.connected:
            # Try to reconnect
            if backend:
                print("🔄 Backend disconnected, attempting reconnection...")
                try:
                    connection_success = await backend.connect()
                    if not connection_success:
                        raise HTTPException(
                            status_code=503, detail="Backend not connected and reconnection failed"
                        )
                    print("✅ Reconnection successful")
                except Exception as e:
                    raise HTTPException(
                        status_code=503, detail=f"Backend connection failed: {str(e)}"
                    )
            else:
                raise HTTPException(status_code=503, detail="Backend not initialized")

        # Execute commands
        print(f"🎯 Received {len(commands)} commands for drone {target_drone}")
        results = await executor.execute_sequence(commands)

        return {
            "success": all(r.success for r in results),
            "results": [
                {
                    "success": r.success,
                    "message": r.message,
                    "error": r.error,
                    "duration": r.duration,
                }
                for r in results
            ],
            "drone_id": AGENT_ID,
            "timestamp": time.time(),
            "total_commands": len(results),
            "successful_commands": sum(1 for r in results if r.success),
        }

    except Exception as e:
        print(f"Command execution error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/telemetry")
async def get_telemetry():
    """Get current drone telemetry data.

    Returns:
        Current telemetry information
    """
    if not backend:
        raise HTTPException(status_code=503, detail="Backend not initialized")

    if not backend.connected:
        # Try to reconnect for telemetry requests
        print("🔄 Backend disconnected for telemetry, attempting reconnection...")
        try:
            connection_success = await backend.connect()
            if not connection_success:
                raise HTTPException(
                    status_code=503, detail="Backend not connected and reconnection failed"
                )
            print("✅ Reconnection successful for telemetry")
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Backend connection failed: {str(e)}")

    try:
        telemetry = await backend.get_telemetry()
        return {"drone_id": AGENT_ID, **telemetry}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Telemetry error: {str(e)}")
