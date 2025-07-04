# dronesphere/server/api.py
# ===================================

"""FastAPI application and routers."""

import time
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from prometheus_client.core import CollectorRegistry
from starlette.responses import Response

from ..agent.main import get_agent
from ..core.config import get_settings
from ..core.errors import (
    CommandValidationError, DroneNotFoundError, CommandExecutionError
)
from ..core.logging import get_logger
from ..core.models import (
    APIResponse, CommandAcceptedResponse, CommandSequence, 
    DroneStatus, Telemetry, CommandEnvelope
)

logger = get_logger(__name__)

# Metrics
REQUEST_COUNT = Counter('dronesphere_requests_total', 'Total requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('dronesphere_request_duration_seconds', 'Request duration')

# Create FastAPI app
settings = get_settings()

app = FastAPI(
    title="DroneSphere API",
    description="Scalable drone command and control system",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.server.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware for metrics
@app.middleware("http")
async def metrics_middleware(request, call_next):
    """Collect request metrics."""
    start_time = time.time()
    
    response = await call_next(request)
    
    # Record metrics
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path
    ).inc()
    
    REQUEST_DURATION.observe(time.time() - start_time)
    
    return response


# Health check endpoints
@app.get("/health", response_model=APIResponse)
async def health_check():
    """Health check endpoint."""
    try:
        agent = get_agent()
        
        # Check if we have any connections
        drone_count = len(agent.connections)
        connected_drones = [
            drone_id for drone_id, conn in agent.connections.items()
            if conn.connected
        ]
        
        healthy = drone_count > 0 and len(connected_drones) > 0
        
        return APIResponse(
            success=healthy,
            message="Healthy" if healthy else "No connected drones",
            data={
                "total_drones": drone_count,
                "connected_drones": connected_drones,
                "timestamp": time.time()
            }
        )
        
    except Exception as e:
        logger.error("health_check_failed", error=str(e))
        return APIResponse(
            success=False,
            message="Health check failed",
            errors=[str(e)]
        )


@app.get("/ready", response_model=APIResponse)
async def readiness_check():
    """Readiness check endpoint."""
    try:
        agent = get_agent()
        
        # For MVP, check if drone 1 is connected and ready
        if 1 not in agent.connections:
            return APIResponse(
                success=False,
                message="Drone 1 not configured"
            )
            
        connection = agent.connections[1]
        ready = connection.connected
        
        return APIResponse(
            success=ready,
            message="Ready" if ready else "Not ready",
            data={"drone_1_connected": ready}
        )
        
    except Exception as e:
        logger.error("readiness_check_failed", error=str(e))
        return APIResponse(
            success=False,
            message="Readiness check failed",
            errors=[str(e)]
        )


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# Command endpoints
@app.post("/command/{drone_id}", response_model=CommandAcceptedResponse)
async def execute_command(drone_id: int, command_sequence: CommandSequence):
    """Execute command sequence on specified drone."""
    try:
        logger.info("command_request_received", 
                   drone_id=drone_id, 
                   sequence_length=len(command_sequence.sequence))
        
        agent = get_agent()
        
        # Validate drone exists
        if drone_id not in agent.runners:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Drone {drone_id} not found"
            )
            
        runner = agent.runners[drone_id]
        
        # Create command envelope
        envelope = CommandEnvelope(
            drone_id=drone_id,
            sequence=command_sequence.sequence
        )
        
        # Enqueue command
        command_id = await runner.enqueue_command(envelope)
        
        # Estimate duration (simple heuristic)
        estimated_duration = len(command_sequence.sequence) * 30  # 30s per command average
        
        logger.info("command_accepted", 
                   drone_id=drone_id,
                   command_id=command_id,
                   estimated_duration=estimated_duration)
        
        return CommandAcceptedResponse(
            success=True,
            message="Command sequence accepted",
            command_id=command_id,
            estimated_duration=estimated_duration
        )
        
    except CommandValidationError as e:
        logger.warning("command_validation_failed", 
                      drone_id=drone_id, 
                      error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("command_execution_failed", 
                    drone_id=drone_id, 
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Command execution failed: {str(e)}"
        )


@app.get("/status/{drone_id}", response_model=DroneStatus)
async def get_drone_status(drone_id: int):
    """Get current status of specified drone."""
    try:
        agent = get_agent()
        
        # Validate drone exists
        if drone_id not in agent.connections:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Drone {drone_id} not found"
            )
            
        connection = agent.connections[drone_id]
        runner = agent.runners[drone_id]
        
        # Get current state
        state = await connection.get_state()
        
        # Get current execution
        current_execution = runner.get_current_execution()
        
        # Get telemetry timestamp
        telemetry = await connection.get_telemetry()
        last_telemetry = telemetry.timestamp if telemetry else None
        
        # Determine health status
        health_status = "ok" if connection.connected else "disconnected"
        if telemetry and not telemetry.health_all_ok:
            health_status = "degraded"
            
        return DroneStatus(
            drone_id=drone_id,
            state=state,
            current_command=current_execution,
            queue_length=runner.get_queue_size(),
            last_telemetry=last_telemetry,
            health_status=health_status
        )
        
    except Exception as e:
        logger.error("get_status_failed", drone_id=drone_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get drone status: {str(e)}"
        )


@app.get("/telemetry/{drone_id}", response_model=Telemetry)
async def get_telemetry(drone_id: int):
    """Get current telemetry for specified drone."""
    try:
        agent = get_agent()
        
        # Validate drone exists
        if drone_id not in agent.connections:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Drone {drone_id} not found"
            )
            
        connection = agent.connections[drone_id]
        
        # Get telemetry
        telemetry = await connection.get_telemetry()
        
        if not telemetry:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Telemetry not available"
            )
            
        return telemetry
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_telemetry_failed", drone_id=drone_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get telemetry: {str(e)}"
        )


@app.get("/queue/{drone_id}", response_model=APIResponse)
async def get_command_queue(drone_id: int):
    """Get command queue status for specified drone."""
    try:
        agent = get_agent()
        
        # Validate drone exists
        if drone_id not in agent.runners:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Drone {drone_id} not found"
            )
            
        runner = agent.runners[drone_id]
        
        return APIResponse(
            success=True,
            message="Queue status retrieved",
            data={
                "queue_length": runner.get_queue_size(),
                "current_execution": runner.get_current_execution()
            }
        )
        
    except Exception as e:
        logger.error("get_queue_failed", drone_id=drone_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get queue status: {str(e)}"
        )


@app.get("/command/{command_id}/status", response_model=APIResponse)
async def get_command_status(command_id: str):
    """Get status of specific command execution."""
    try:
        agent = get_agent()
        
        # Search all runners for the command
        for runner in agent.runners.values():
            execution = runner.get_execution_history(command_id)
            if execution:
                return APIResponse(
                    success=True,
                    message="Command status retrieved",
                    data=execution.dict()
                )
                
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Command {command_id} not found"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_command_status_failed", command_id=command_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get command status: {str(e)}"
        )


@app.post("/emergency_stop/{drone_id}", response_model=APIResponse)
async def emergency_stop(drone_id: int):
    """Execute emergency stop for specified drone."""
    try:
        logger.warning("emergency_stop_requested", drone_id=drone_id)
        
        agent = get_agent()
        
        # Validate drone exists
        if drone_id not in agent.connections:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Drone {drone_id} not found"
            )
            
        connection = agent.connections[drone_id]
        runner = agent.runners[drone_id]
        
        # Stop current execution
        await runner.stop()
        
        # Emergency stop the drone
        await connection.emergency_stop()
        
        # Restart runner
        await runner.start()
        
        logger.warning("emergency_stop_executed", drone_id=drone_id)
        
        return APIResponse(
            success=True,
            message="Emergency stop executed"
        )
        
    except Exception as e:
        logger.error("emergency_stop_failed", drone_id=drone_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Emergency stop failed: {str(e)}"
        )


# List endpoints
@app.get("/drones", response_model=APIResponse)
async def list_drones():
    """List all configured drones."""
    try:
        agent = get_agent()
        
        drones = []
        for drone_id, connection in agent.connections.items():
            state = await connection.get_state()
            drones.append({
                "id": drone_id,
                "connected": connection.connected,
                "state": state
            })
            
        return APIResponse(
            success=True,
            message="Drones listed",
            data={"drones": drones}
        )
        
    except Exception as e:
        logger.error("list_drones_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list drones: {str(e)}"
        )



# Add these endpoints to dronesphere/server/api.py
# Insert after the existing endpoints but before error handlers

@app.get("/commands", response_model=APIResponse)
async def list_commands():
    """List all available commands with specifications."""
    try:
        from ..commands.registry import get_command_registry
        
        registry = get_command_registry()
        
        # Get all command names
        command_names = registry.list_commands()
        
        # Build command info with specs
        commands_info = []
        for name in command_names:
            try:
                spec = registry.get_spec(name)
                
                # Extract key information from spec
                command_info = {
                    "name": name,
                    "version": spec.metadata.version,
                    "category": spec.metadata.category,
                    "description": spec.spec.get("description", {}).get("brief", ""),
                    "parameters": {},
                    "tags": spec.metadata.tags
                }
                
                # Add parameter information
                parameters_spec = spec.spec.get("parameters", {})
                for param_name, param_info in parameters_spec.items():
                    command_info["parameters"][param_name] = {
                        "type": param_info.get("type", "str"),
                        "default": param_info.get("default"),
                        "description": param_info.get("description", ""),
                        "constraints": param_info.get("constraints", {})
                    }
                
                commands_info.append(command_info)
                
            except Exception as e:
                logger.warning("command_spec_load_failed", 
                              command=name, 
                              error=str(e))
                # Add basic info even if spec loading fails
                commands_info.append({
                    "name": name,
                    "version": "unknown",
                    "category": "unknown", 
                    "description": "Command specification not available",
                    "parameters": {},
                    "tags": []
                })
        
        # Sort by category and name
        commands_info.sort(key=lambda x: (x["category"], x["name"]))
        
        return APIResponse(
            success=True,
            message=f"Listed {len(commands_info)} available commands",
            data={
                "commands": commands_info,
                "total_count": len(commands_info),
                "categories": list(set(cmd["category"] for cmd in commands_info))
            }
        )
        
    except Exception as e:
        logger.error("list_commands_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list commands: {str(e)}"
        )


@app.get("/history/{drone_id}", response_model=APIResponse)
async def get_command_history(drone_id: int, limit: int = 50, offset: int = 0):
    """Get command execution history for specified drone."""
    try:
        agent = get_agent()
        
        # Validate drone exists
        if drone_id not in agent.runners:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Drone {drone_id} not found"
            )
            
        runner = agent.runners[drone_id]
        
        # Get execution history
        history = runner.execution_history
        
        # Convert to list and sort by start time (newest first)
        executions = []
        for execution_id, execution in history.items():
            execution_data = {
                "id": execution.id,
                "command_name": execution.command.name,
                "command_params": execution.command.params,
                "status": execution.status,
                "started_at": execution.started_at.isoformat() if execution.started_at else None,
                "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
                "result": execution.result.dict() if execution.result else None
            }
            executions.append(execution_data)
        
        # Sort by start time (newest first)
        executions.sort(
            key=lambda x: x["started_at"] or "1970-01-01T00:00:00", 
            reverse=True
        )
        
        # Apply pagination
        total_count = len(executions)
        paginated_executions = executions[offset:offset + limit]
        
        return APIResponse(
            success=True,
            message=f"Retrieved {len(paginated_executions)} command history entries",
            data={
                "executions": paginated_executions,
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": (offset + limit) < total_count
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_history_failed", drone_id=drone_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get command history: {str(e)}"
        )


@app.get("/commands/{command_name}", response_model=APIResponse)
async def get_command_details(command_name: str):
    """Get detailed information about a specific command."""
    try:
        from ..commands.registry import get_command_registry
        
        registry = get_command_registry()
        
        # Get command specification
        try:
            spec = registry.get_spec(command_name)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Command '{command_name}' not found"
            )
        
        # Build detailed command information
        command_detail = {
            "name": command_name,
            "metadata": {
                "version": spec.metadata.version,
                "category": spec.metadata.category,
                "tags": spec.metadata.tags
            },
            "description": spec.spec.get("description", {}),
            "parameters": spec.spec.get("parameters", {}),
            "implementation": spec.spec.get("implementation", {}),
            "telemetry_feedback": spec.spec.get("telemetry_feedback", {})
        }
        
        return APIResponse(
            success=True,
            message=f"Command '{command_name}' details retrieved",
            data=command_detail
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_command_details_failed", 
                    command=command_name, 
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get command details: {str(e)}"
        )

# Error handlers
@app.exception_handler(DroneNotFoundError)
async def drone_not_found_handler(request, exc):
    """Handle drone not found errors."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"success": False, "message": str(exc)}
    )


@app.exception_handler(CommandValidationError)
async def command_validation_handler(request, exc):
    """Handle command validation errors."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"success": False, "message": str(exc)}
    )


@app.exception_handler(CommandExecutionError)
async def command_execution_handler(request, exc):
    """Handle command execution errors."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"success": False, "message": str(exc)}
    )


