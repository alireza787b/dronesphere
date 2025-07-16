"""DroneSphere Server API for fleet management.

Routes commands to appropriate drone agents and provides fleet-wide monitoring.
Maintains the universal command protocol by forwarding exact payloads.

Path: server/api.py
"""
import time
import sys
import os
from typing import Dict, Any
import httpx
from fastapi import FastAPI, HTTPException

# Add project root to Python path  
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = FastAPI(
    title="DroneSphere Server", 
    version="2.0.0",
    description="Fleet management server for drone command routing"
)

# Drone registry (TODO: Load from drones.yaml)
DRONE_REGISTRY = {
    1: "127.0.0.1:8001"  # drone_id: ip:port
}

SERVER_START_TIME = time.time()


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Server health check endpoint."""
    uptime = time.time() - SERVER_START_TIME
    
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "service": "dronesphere-server",
        "version": "2.0.0",
        "uptime_seconds": round(uptime, 2),
        "registered_drones": len(DRONE_REGISTRY),
        "drone_ids": list(DRONE_REGISTRY.keys())
    }


@app.post("/fleet/commands")
async def route_commands(request: dict) -> Dict[str, Any]:
    """Route commands to appropriate drone agent.
    
    Maintains universal protocol by forwarding exact payload to agents.
    
    Args:
        request: Command request dictionary (same format as agent)
        
    Returns:
        Agent response forwarded directly
    """
    try:
        target_drone = request.get("target_drone")
        
        # Validate target_drone is specified
        if not target_drone:
            raise HTTPException(
                status_code=400, 
                detail="target_drone required for fleet commands"
            )
        
        # Validate drone exists in registry
        if target_drone not in DRONE_REGISTRY:
            raise HTTPException(
                status_code=404, 
                detail=f"Drone {target_drone} not found in registry. Available: {list(DRONE_REGISTRY.keys())}"
            )
        
        # Get drone endpoint
        drone_endpoint = f"http://{DRONE_REGISTRY[target_drone]}"
        
        print(f"🎯 Routing {len(request.get('commands', []))} commands to drone {target_drone} at {drone_endpoint}")
        
        # Forward exact payload to agent (universal protocol)
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{drone_endpoint}/commands",
                    json=request,  # Forward exact request
                    timeout=60.0   # Longer timeout for command execution
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ Commands routed successfully to drone {target_drone}")
                    return result
                else:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Agent returned error: {response.text}"
                    )
                    
            except httpx.TimeoutException:
                raise HTTPException(
                    status_code=504, 
                    detail=f"Timeout waiting for drone {target_drone} response"
                )
            except httpx.ConnectError:
                raise HTTPException(
                    status_code=503, 
                    detail=f"Cannot connect to drone {target_drone} at {drone_endpoint}"
                )
            except Exception as e:
                raise HTTPException(
                    status_code=503, 
                    detail=f"Communication error with drone {target_drone}: {str(e)}"
                )
                
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Server error: {str(e)}"
        )


@app.get("/fleet/health")
async def fleet_health() -> Dict[str, Any]:
    """Get health status of all registered drones.
    
    Returns:
        Health status for each drone in the fleet
    """
    health_status = {
        "timestamp": time.time(),
        "total_drones": len(DRONE_REGISTRY),
        "drones": {}
    }
    
    async with httpx.AsyncClient() as client:
        for drone_id, endpoint in DRONE_REGISTRY.items():
            try:
                response = await client.get(
                    f"http://{endpoint}/health", 
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    health_status["drones"][drone_id] = {
                        "status": "healthy",
                        "endpoint": endpoint,
                        **response.json()
                    }
                else:
                    health_status["drones"][drone_id] = {
                        "status": "error",
                        "endpoint": endpoint,
                        "error": f"HTTP {response.status_code}"
                    }
                    
            except httpx.TimeoutException:
                health_status["drones"][drone_id] = {
                    "status": "timeout",
                    "endpoint": endpoint,
                    "error": "Health check timeout"
                }
            except httpx.ConnectError:
                health_status["drones"][drone_id] = {
                    "status": "unreachable",
                    "endpoint": endpoint,
                    "error": "Connection refused"
                }
            except Exception as e:
                health_status["drones"][drone_id] = {
                    "status": "error",
                    "endpoint": endpoint,
                    "error": str(e)
                }
    
    # Add summary
    statuses = [drone["status"] for drone in health_status["drones"].values()]
    health_status["summary"] = {
        "healthy": statuses.count("healthy"),
        "unreachable": statuses.count("unreachable"),
        "error": statuses.count("error"),
        "timeout": statuses.count("timeout")
    }
    
    return health_status


@app.get("/fleet/registry")
async def get_registry() -> Dict[str, Any]:
    """Get current drone registry configuration."""
    return {
        "timestamp": time.time(),
        "drones": {
            str(drone_id): {
                "id": drone_id,
                "endpoint": f"http://{endpoint}",
                "ip": endpoint.split(":")[0],
                "port": int(endpoint.split(":")[1])
            }
            for drone_id, endpoint in DRONE_REGISTRY.items()
        },
        "total_count": len(DRONE_REGISTRY)
    }
