"""DroneSphere Agent REST API.

Provides drone control endpoints for command execution, health monitoring,
and telemetry data. Runs on the drone or Raspberry Pi at port 8001.

Path: agent/api.py
"""
import time
import sys
import os
from fastapi import FastAPI, HTTPException
from typing import Dict, Any

# Add parent directory to path for shared imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = FastAPI(
    title="DroneSphere Agent", 
    version="2.0.0",
    description="Drone control agent for individual drone operations"
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
        
        # Initialize MAVSDK backend
        backend = MAVSDKBackend("udp://:14540")
        
        # Try to connect to drone (non-blocking for health checks)
        try:
            await backend.connect()
            print("✅ MAVSDK backend connected")
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
        "executor_ready": executor is not None
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
    return {
        "agent": {
            "status": "ok", 
            "version": VERSION,
            "id": AGENT_ID,
            "uptime": round(time.time() - startup_time, 2)
        },
        "backend": {
            "connected": backend.connected if backend else False,
            "type": "mavsdk" if backend else None
        },
        "executor": {
            "available": executor is not None,
            "commands": list(executor.command_map.keys()) if executor else []
        },
        "system": {
            "python_version": sys.version.split()[0],
            "platform": sys.platform
        },
        "timestamp": time.time()
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
    from shared.models import CommandRequest, Command, CommandMode, QueueMode
    
    try:
        # Parse request manually to handle dataclass conversion
        commands_data = request.get("commands", [])
        commands = []
        
        for cmd_data in commands_data:
            cmd = Command(
                name=cmd_data["name"],
                params=cmd_data.get("params", {}),
                mode=CommandMode(cmd_data.get("mode", "continue"))
            )
            commands.append(cmd)
        
        queue_mode = QueueMode(request.get("queue_mode", "override"))
        target_drone = request.get("target_drone")
        
        # Validate target_drone
        if target_drone and target_drone != AGENT_ID:
            raise HTTPException(
                status_code=400,
                detail=f"Wrong drone. This is drone {AGENT_ID}, got target {target_drone}"
            )
        
        # Default to own ID if missing
        if not target_drone:
            target_drone = AGENT_ID
        
        # Check if executor is ready
        if not executor:
            raise HTTPException(
                status_code=503, 
                detail="Command executor not initialized"
            )
        
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
                    "duration": r.duration
                }
                for r in results
            ],
            "drone_id": AGENT_ID,
            "timestamp": time.time(),
            "total_commands": len(results),
            "successful_commands": sum(1 for r in results if r.success)
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
        raise HTTPException(
            status_code=503, 
            detail="Backend not initialized"
        )
    
    if not backend.connected:
        raise HTTPException(
            status_code=503, 
            detail="Backend not connected to drone"
        )
    
    try:
        telemetry = await backend.get_telemetry()
        return {
            "drone_id": AGENT_ID,
            **telemetry
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Telemetry error: {str(e)}"
        )