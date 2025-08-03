"""DroneSphere Server API for fleet management with telemetry polling.

Enhanced fleet management server with dynamic YAML configuration and
background telemetry polling system for multi-drone monitoring.

Path: server/api.py
"""
import asyncio
import os
import sys
import threading
import time
from typing import Any, Dict, List, Optional

import httpx
import requests
from fastapi import FastAPI, HTTPException

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the dynamic drone configuration system
from shared.drone_config import get_fleet_config, reload_fleet_config

app = FastAPI(
    title="DroneSphere Server",
    version="2.0.1",
    description="Fleet management server with dynamic configuration and telemetry polling",
)

# Global state
SERVER_START_TIME = time.time()

# Telemetry polling system
telemetry_cache: Dict[int, Dict[str, Any]] = {}
telemetry_lock = threading.Lock()
telemetry_thread: Optional[threading.Thread] = None
is_polling = False


def get_drone_registry() -> Dict[int, str]:
    """Get current drone registry from YAML configuration."""
    return get_fleet_config().get_active_registry_dict()


def start_telemetry_polling():
    """Start background telemetry polling thread."""
    global telemetry_thread, is_polling

    if telemetry_thread is None or not telemetry_thread.is_alive():
        is_polling = True
        telemetry_thread = threading.Thread(target=_telemetry_polling_worker, daemon=True)
        telemetry_thread.start()
        print("🔄 Started fleet telemetry polling thread")


def stop_telemetry_polling():
    """Stop background telemetry polling."""
    global is_polling
    is_polling = False
    print("⏹️  Stopped fleet telemetry polling")


def _telemetry_polling_worker():
    """Background worker to poll drone telemetries.

    Polls all active drones every 2 seconds and caches the results.
    Handles connection errors gracefully and continues polling.
    """
    global telemetry_cache, is_polling

    print("🔄 Telemetry polling worker started")

    while is_polling:
        try:
            fleet_config = get_fleet_config()
            active_drones = fleet_config.get_active_drones()

            if not active_drones:
                print("⚠️  No active drones found, waiting...")
                time.sleep(5.0)
                continue

            # Poll each active drone
            for drone_config in active_drones:
                drone_id = drone_config.id
                endpoint = drone_config.endpoint

                try:
                    # Use requests for sync operation in thread
                    response = requests.get(f"http://{endpoint}/telemetry", timeout=5.0)

                    if response.status_code == 200:
                        telemetry_data = response.json()

                        # Add server metadata
                        telemetry_data.update(
                            {
                                "server_timestamp": time.time(),
                                "source": "polling",
                                "drone_endpoint": endpoint,
                                "drone_name": drone_config.name,
                                "drone_type": drone_config.type,
                                "drone_location": drone_config.location,
                            }
                        )

                        with telemetry_lock:
                            telemetry_cache[drone_id] = telemetry_data

                    else:
                        # Store error state
                        with telemetry_lock:
                            telemetry_cache[drone_id] = {
                                "error": f"HTTP {response.status_code}",
                                "server_timestamp": time.time(),
                                "source": "polling_error",
                                "drone_endpoint": endpoint,
                                "drone_name": drone_config.name,
                                "drone_type": drone_config.type,
                            }

                except requests.RequestException as e:
                    # Store connection error
                    with telemetry_lock:
                        telemetry_cache[drone_id] = {
                            "error": str(e),
                            "server_timestamp": time.time(),
                            "source": "connection_error",
                            "drone_endpoint": endpoint,
                            "drone_name": drone_config.name,
                            "drone_type": drone_config.type,
                        }

            # Sleep between polls (2 second interval)
            time.sleep(2.0)

        except Exception as e:
            print(f"❌ Telemetry polling error: {e}")
            time.sleep(5.0)  # Longer sleep on error

    print("⏹️  Telemetry polling worker stopped")


@app.on_event("startup")
async def startup_event():
    """Start telemetry polling on server startup."""
    print("🚀 Starting DroneSphere Server with fleet telemetry polling")
    fleet_config = get_fleet_config()
    print(f"📋 Loaded fleet: {fleet_config.fleet_name}")
    print(f"🚁 Active drones: {len(fleet_config.get_active_drones())}")
    start_telemetry_polling()


@app.on_event("shutdown")
async def shutdown_event():
    """Stop telemetry polling on server shutdown."""
    stop_telemetry_polling()


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Server health check endpoint with dynamic drone info."""
    uptime = time.time() - SERVER_START_TIME
    fleet_config = get_fleet_config()

    return {
        "status": "healthy",
        "timestamp": time.time(),
        "service": "dronesphere-server",
        "version": "2.0.1",
        "uptime_seconds": round(uptime, 2),
        "fleet": {
            "name": fleet_config.fleet_name,
            "version": fleet_config.fleet_version,
            "total_drones": len(fleet_config.drones),
            "active_drones": len(fleet_config.get_active_drones()),
            "drone_ids": list(fleet_config.drones.keys()),
            "active_drone_ids": [d.id for d in fleet_config.get_active_drones()],
        },
        "telemetry_polling": {
            "active": is_polling,
            "thread_alive": telemetry_thread.is_alive() if telemetry_thread else False,
            "cached_drones": len(telemetry_cache),
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


# =============================================================================
# FLEET TELEMETRY ENDPOINTS - New telemetry polling system
# =============================================================================


@app.get("/fleet/telemetry")
async def get_fleet_telemetry() -> Dict[str, Any]:
    """Get telemetry data for all drones in the fleet.

    Returns cached telemetry data with metadata about freshness and polling status.

    Returns:
        Dict containing fleet-wide telemetry data with timestamps and metadata
    """
    fleet_config = get_fleet_config()

    with telemetry_lock:
        fleet_telemetry = {
            "timestamp": time.time(),
            "fleet_name": fleet_config.fleet_name,
            "total_drones": len(fleet_config.drones),
            "active_drones": len(fleet_config.get_active_drones()),
            "polling_active": is_polling,
            "drones": {},
        }

        # Add telemetry for each drone in configuration
        for drone_id, drone_config in fleet_config.drones.items():
            if drone_id in telemetry_cache:
                telemetry = telemetry_cache[drone_id].copy()

                # Calculate data age
                server_timestamp = telemetry.get("server_timestamp", 0)
                data_age = time.time() - server_timestamp
                telemetry["data_age_seconds"] = round(data_age, 2)

                fleet_telemetry["drones"][drone_id] = telemetry
            else:
                # No cached data available
                fleet_telemetry["drones"][drone_id] = {
                    "error": "No telemetry data available",
                    "server_timestamp": time.time(),
                    "source": "no_data",
                    "drone_name": drone_config.name,
                    "drone_type": drone_config.type,
                    "configured_status": drone_config.status,
                }

        # Add summary statistics
        successful_drones = sum(1 for d in fleet_telemetry["drones"].values() if "error" not in d)
        total_configured = len(fleet_config.drones)

        fleet_telemetry["summary"] = {
            "successful": successful_drones,
            "failed": total_configured - successful_drones,
            "success_rate": f"{(successful_drones / total_configured * 100):.1f}%"
            if total_configured
            else "0%",
            "cache_size": len(telemetry_cache),
        }

        return fleet_telemetry


@app.get("/fleet/telemetry/{drone_id}")
async def get_drone_telemetry(drone_id: int) -> Dict[str, Any]:
    """Get telemetry data for a specific drone.

    Args:
        drone_id: ID of the drone to get telemetry for

    Returns:
        Latest cached telemetry data for the specified drone
    """
    fleet_config = get_fleet_config()
    drone_config = fleet_config.get_drone(drone_id)

    if not drone_config:
        raise HTTPException(
            status_code=404,
            detail=f"Drone {drone_id} not found in configuration. Available: {list(fleet_config.drones.keys())}",
        )

    with telemetry_lock:
        if drone_id in telemetry_cache:
            telemetry = telemetry_cache[drone_id].copy()

            # Calculate data age
            server_timestamp = telemetry.get("server_timestamp", 0)
            data_age = time.time() - server_timestamp
            telemetry["data_age_seconds"] = round(data_age, 2)

            return telemetry
        else:
            raise HTTPException(
                status_code=503,
                detail=f"No telemetry data available for drone {drone_id} ({drone_config.name}). Polling active: {is_polling}",
            )


@app.get("/fleet/telemetry/{drone_id}/live")
async def get_live_drone_telemetry(drone_id: int) -> Dict[str, Any]:
    """Get real-time telemetry directly from drone (bypasses cache).

    Args:
        drone_id: ID of the drone to get live telemetry for

    Returns:
        Fresh telemetry data directly from the drone agent
    """
    fleet_config = get_fleet_config()
    drone_config = fleet_config.get_drone(drone_id)

    if not drone_config:
        raise HTTPException(
            status_code=404,
            detail=f"Drone {drone_id} not found in configuration. Available: {list(fleet_config.drones.keys())}",
        )

    endpoint = drone_config.endpoint

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"http://{endpoint}/telemetry", timeout=10.0)

            if response.status_code == 200:
                telemetry = response.json()
                telemetry.update(
                    {
                        "server_timestamp": time.time(),
                        "source": "live_request",
                        "drone_endpoint": endpoint,
                        "drone_name": drone_config.name,
                        "drone_type": drone_config.type,
                        "drone_location": drone_config.location,
                        "data_age_seconds": 0.0,  # Fresh data
                    }
                )
                return telemetry
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Drone {drone_config.name} returned error: {response.text}",
                )

        except httpx.TimeoutException:
            raise HTTPException(
                status_code=504,
                detail=f"Timeout waiting for drone {drone_id} ({drone_config.name}) telemetry",
            )
        except httpx.ConnectError:
            raise HTTPException(
                status_code=503,
                detail=f"Cannot connect to drone {drone_id} ({drone_config.name}) at {endpoint}",
            )
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail=f"Communication error with drone {drone_id} ({drone_config.name}): {str(e)}",
            )


@app.get("/fleet/telemetry/status")
async def get_telemetry_status() -> Dict[str, Any]:
    """Get status of the telemetry polling system.

    Returns:
        Status information about the background polling system
    """
    fleet_config = get_fleet_config()

    with telemetry_lock:
        cache_info = {}
        for drone_id, data in telemetry_cache.items():
            cache_info[drone_id] = {
                "drone_name": data.get("drone_name", f"Drone {drone_id}"),
                "has_data": "error" not in data,
                "age_seconds": round(time.time() - data.get("server_timestamp", 0), 2),
                "source": data.get("source", "unknown"),
                "last_error": data.get("error") if "error" in data else None,
            }

    return {
        "timestamp": time.time(),
        "polling_status": {
            "active": is_polling,
            "thread_alive": telemetry_thread.is_alive() if telemetry_thread else False,
            "interval_seconds": 2.0,
        },
        "fleet_info": {
            "fleet_name": fleet_config.fleet_name,
            "total_drones": len(fleet_config.drones),
            "active_drones": len(fleet_config.get_active_drones()),
            "cached_drones": len(telemetry_cache),
        },
        "cache_details": cache_info,
        "system_health": {
            "cache_hit_rate": f"{(len(telemetry_cache) / max(len(fleet_config.get_active_drones()), 1) * 100):.1f}%",
            "oldest_data_age": max(
                [
                    time.time() - data.get("server_timestamp", time.time())
                    for data in telemetry_cache.values()
                ],
                default=0,
            )
            if telemetry_cache
            else 0,
        },
    }
