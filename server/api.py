# server/api.py - Updated with dynamic drone configuration
"""DroneSphere Server API for fleet management.

Routes commands to appropriate drone agents and provides fleet-wide monitoring.
Uses dynamic YAML-based drone configuration for flexible fleet management.

Path: server/api.py
"""
import os
import sys
import time
from typing import Any, Dict

import httpx
from fastapi import FastAPI, HTTPException

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the new drone configuration system
from shared.drone_config import get_fleet_config, reload_fleet_config

app = FastAPI(
    title="DroneSphere Server",
    version="2.0.0",
    description="Fleet management server with dynamic drone configuration",
)

SERVER_START_TIME = time.time()


def get_drone_registry() -> Dict[int, str]:
    """Get current drone registry from YAML configuration."""
    return get_fleet_config().get_active_registry_dict()


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Server health check endpoint with dynamic drone info."""
    uptime = time.time() - SERVER_START_TIME
    fleet_config = get_fleet_config()

    return {
        "status": "healthy",
        "timestamp": time.time(),
        "service": "dronesphere-server",
        "version": "2.0.0",
        "uptime_seconds": round(uptime, 2),
        "fleet": {
            "name": fleet_config.fleet_name,
            "version": fleet_config.fleet_version,
            "total_drones": len(fleet_config.drones),
            "active_drones": len(fleet_config.get_active_drones()),
            "drone_ids": list(fleet_config.drones.keys()),
            "active_drone_ids": [d.id for d in fleet_config.get_active_drones()],
        },
    }


@app.post("/fleet/commands")
async def route_commands(request: dict) -> Dict[str, Any]:
    """Route commands to appropriate drone agent using dynamic configuration.

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
            raise HTTPException(status_code=400, detail="target_drone required for fleet commands")

        # Get current drone registry
        drone_registry = get_drone_registry()

        # Validate drone exists in registry
        if target_drone not in drone_registry:
            raise HTTPException(
                status_code=404,
                detail=f"Drone {target_drone} not found in active registry. Available: {list(drone_registry.keys())}",
            )

        # Get drone configuration
        fleet_config = get_fleet_config()
        drone_config = fleet_config.get_drone(target_drone)

        if not drone_config:
            raise HTTPException(
                status_code=404, detail=f"Drone {target_drone} configuration not found"
            )

        if not drone_config.is_active:
            raise HTTPException(
                status_code=503, detail=f"Drone {target_drone} ({drone_config.name}) is not active"
            )

        # Get drone endpoint
        drone_endpoint = f"http://{drone_config.endpoint}"

        print(
            f"🎯 Routing {len(request.get('commands', []))} commands to drone {target_drone} ({drone_config.name}) at {drone_endpoint}"
        )

        # Forward exact payload to agent (universal protocol)
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{drone_endpoint}/commands",
                    json=request,  # Forward exact request
                    timeout=60.0,  # Longer timeout for command execution
                )

                if response.status_code == 200:
                    result = response.json()
                    print(
                        f"✅ Commands routed successfully to drone {target_drone} ({drone_config.name})"
                    )
                    return result
                else:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Agent returned error: {response.text}",
                    )

            except httpx.TimeoutException:
                raise HTTPException(
                    status_code=504,
                    detail=f"Timeout waiting for drone {target_drone} ({drone_config.name}) response",
                )
            except httpx.ConnectError:
                raise HTTPException(
                    status_code=503,
                    detail=f"Cannot connect to drone {target_drone} ({drone_config.name}) at {drone_endpoint}",
                )
            except Exception as e:
                raise HTTPException(
                    status_code=503,
                    detail=f"Communication error with drone {target_drone} ({drone_config.name}): {str(e)}",
                )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


@app.get("/fleet/health")
async def fleet_health() -> Dict[str, Any]:
    """Get health status of all drones using dynamic configuration."""
    fleet_config = get_fleet_config()
    health_status = {
        "timestamp": time.time(),
        "fleet_name": fleet_config.fleet_name,
        "total_drones": len(fleet_config.drones),
        "active_drones": len(fleet_config.get_active_drones()),
        "drones": {},
    }

    async with httpx.AsyncClient() as client:
        # Check all drones (both active and inactive)
        for drone_id, drone_config in fleet_config.drones.items():
            endpoint = drone_config.endpoint

            drone_status = {
                "id": drone_id,
                "name": drone_config.name,
                "type": drone_config.type,
                "configured_status": drone_config.status,
                "endpoint": endpoint,
                "location": drone_config.location,
            }

            if drone_config.is_active:
                try:
                    response = await client.get(f"http://{endpoint}/health", timeout=5.0)

                    if response.status_code == 200:
                        agent_health = response.json()
                        drone_status.update(
                            {
                                "status": "healthy",
                                "backend_connected": agent_health.get("backend_connected", False),
                                "executor_ready": agent_health.get("executor_ready", False),
                                "uptime_seconds": agent_health.get("uptime_seconds", 0),
                            }
                        )
                    else:
                        drone_status.update(
                            {"status": "error", "error": f"HTTP {response.status_code}"}
                        )

                except httpx.TimeoutException:
                    drone_status.update({"status": "timeout", "error": "Health check timeout"})
                except httpx.ConnectError:
                    drone_status.update({"status": "unreachable", "error": "Connection refused"})
                except Exception as e:
                    drone_status.update({"status": "error", "error": str(e)})
            else:
                drone_status.update(
                    {"status": "inactive", "error": "Drone marked as inactive in configuration"}
                )

            health_status["drones"][drone_id] = drone_status

    # Add summary statistics
    statuses = [drone["status"] for drone in health_status["drones"].values()]
    health_status["summary"] = {
        "healthy": statuses.count("healthy"),
        "inactive": statuses.count("inactive"),
        "unreachable": statuses.count("unreachable"),
        "error": statuses.count("error"),
        "timeout": statuses.count("timeout"),
    }

    return health_status


@app.get("/fleet/registry")
async def get_registry() -> Dict[str, Any]:
    """Get current drone registry configuration from YAML."""
    fleet_config = get_fleet_config()

    return {
        "timestamp": time.time(),
        "fleet": {
            "name": fleet_config.fleet_name,
            "version": fleet_config.fleet_version,
            "description": fleet_config.fleet_description,
        },
        "drones": {
            str(drone_id): {
                "id": drone_id,
                "name": drone_config.name,
                "description": drone_config.description,
                "type": drone_config.type,
                "status": drone_config.status,
                "endpoint": f"http://{drone_config.endpoint}",
                "ip": drone_config.ip,
                "port": drone_config.port,
                "location": drone_config.location,
                "team": drone_config.team,
                "priority": drone_config.priority,
            }
            for drone_id, drone_config in fleet_config.drones.items()
        },
        "statistics": {
            "total_count": len(fleet_config.drones),
            "active_count": len(fleet_config.get_active_drones()),
            "simulation_count": len(fleet_config.get_simulation_drones()),
            "hardware_count": len(fleet_config.get_hardware_drones()),
        },
    }


@app.get("/fleet/config")
async def get_fleet_config_endpoint() -> Dict[str, Any]:
    """Get complete fleet configuration including settings and environments."""
    fleet_config = get_fleet_config()
    return fleet_config.to_dict()


@app.post("/fleet/config/reload")
async def reload_fleet_config_endpoint() -> Dict[str, Any]:
    """Reload fleet configuration from YAML file."""
    try:
        old_count = len(get_fleet_config().drones)
        fleet_config = reload_fleet_config()
        new_count = len(fleet_config.drones)

        return {
            "success": True,
            "message": f"Fleet configuration reloaded successfully",
            "timestamp": time.time(),
            "changes": {
                "old_drone_count": old_count,
                "new_drone_count": new_count,
                "fleet_name": fleet_config.fleet_name,
                "fleet_version": fleet_config.fleet_version,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reload configuration: {str(e)}")


@app.get("/fleet/drones/{drone_id}")
async def get_drone_info(drone_id: int) -> Dict[str, Any]:
    """Get detailed information for a specific drone."""
    fleet_config = get_fleet_config()
    drone_config = fleet_config.get_drone(drone_id)

    if not drone_config:
        raise HTTPException(status_code=404, detail=f"Drone {drone_id} not found in configuration")

    return {"timestamp": time.time(), "drone": drone_config.to_dict()}
