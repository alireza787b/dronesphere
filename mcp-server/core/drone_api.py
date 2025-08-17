"""DroneSphere API Client - Non-blocking version.

Path: mcp-server/core/drone_api.py
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class DroneAPI:
    """Client for DroneSphere server API with non-blocking command execution."""

    def __init__(self, base_url: str, timeout: float = 30.0):
        """Initialize API client.

        Args:
            base_url: DroneSphere server URL (e.g., http://localhost:8002)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=2.0,  # Quick connection
                read=30.0,  # Allow time for execution
                write=5.0,
                pool=5.0,
            )
        )
        self._telemetry_cache = {}
        self._cache_time = {}
        self._command_status = {}  # Track command execution status

    async def send_commands(
        self, commands: List[Dict[str, Any]], drone_id: int = 1, queue_mode: str = "override"
    ) -> Dict[str, Any]:
        """Send commands to drone - returns immediately after queuing.

        Args:
            commands: List of command dicts
            drone_id: Target drone ID
            queue_mode: "override" or "append"

        Returns:
            Immediate acknowledgment with command ID for tracking
        """
        command_id = f"cmd_{datetime.now().timestamp()}"

        # Start execution in background (fire and forget)
        asyncio.create_task(
            self._execute_commands_background(commands, drone_id, queue_mode, command_id)
        )

        # Store initial status
        self._command_status[command_id] = {
            "status": "queued",
            "commands": commands,
            "drone_id": drone_id,
            "started_at": datetime.now().isoformat(),
            "completed": False,
        }

        # Return immediate acknowledgment
        return {
            "success": True,
            "message": f"Commands queued for execution ({len(commands)} commands)",
            "command_id": command_id,
            "status": "Commands will execute in background. Check status with command_id.",
            "commands_sent": [cmd.get("name", "unknown") for cmd in commands],
        }

    async def _execute_commands_background(
        self, commands: List[Dict[str, Any]], drone_id: int, queue_mode: str, command_id: str
    ):
        """Execute commands in background without blocking."""
        try:
            # Update status
            self._command_status[command_id]["status"] = "executing"

            # Send to drone server
            response = await self.client.post(
                f"{self.base_url}/fleet/commands",
                json={"commands": commands, "target_drone": drone_id, "queue_mode": queue_mode},
            )

            if response.status_code == 200:
                result = response.json()
                self._command_status[command_id].update(
                    {
                        "status": "completed",
                        "completed": True,
                        "result": result,
                        "completed_at": datetime.now().isoformat(),
                    }
                )
                logger.info(f"Command {command_id} completed successfully")
            else:
                self._command_status[command_id].update(
                    {
                        "status": "failed",
                        "error": f"Server returned {response.status_code}",
                        "completed": True,
                        "completed_at": datetime.now().isoformat(),
                    }
                )
                logger.error(f"Command {command_id} failed: {response.status_code}")

        except Exception as e:
            self._command_status[command_id].update(
                {
                    "status": "error",
                    "error": str(e),
                    "completed": True,
                    "completed_at": datetime.now().isoformat(),
                }
            )
            logger.error(f"Command {command_id} error: {e}")

    async def get_command_status(self, command_id: str) -> Dict[str, Any]:
        """Get status of a previously sent command.

        Args:
            command_id: Command ID from send_commands

        Returns:
            Command execution status
        """
        if command_id not in self._command_status:
            return {"error": "Command ID not found"}

        return self._command_status.get(command_id, {})

    async def get_telemetry(self, drone_id: int = 1, use_cache: bool = True) -> Dict[str, Any]:
        """Get telemetry with caching to avoid timeouts.

        Args:
            drone_id: Target drone ID
            use_cache: Use cached data if recent (within 2 seconds)

        Returns:
            Telemetry dict
        """
        cache_key = f"drone_{drone_id}"
        now = datetime.now().timestamp()

        # Check cache (2 second validity)
        if use_cache and cache_key in self._telemetry_cache:
            cache_age = now - self._cache_time.get(cache_key, 0)
            if cache_age < 2.0:
                logger.debug(f"Using cached telemetry (age: {cache_age:.1f}s)")
                return self._telemetry_cache[cache_key]

        try:
            # Quick telemetry fetch with short timeout
            response = await asyncio.wait_for(
                self.client.get(f"{self.base_url}/fleet/telemetry/{drone_id}"),
                timeout=1.5,  # Very short timeout for telemetry
            )

            if response.status_code == 200:
                telemetry = response.json()
                # Update cache
                self._telemetry_cache[cache_key] = telemetry
                self._cache_time[cache_key] = now
                return telemetry
            else:
                logger.warning(f"Telemetry fetch failed: {response.status_code}")

        except asyncio.TimeoutError:
            logger.warning("Telemetry fetch timeout, using defaults")
        except Exception as e:
            logger.warning(f"Telemetry error: {e}")

        # Return cached or default telemetry
        if cache_key in self._telemetry_cache:
            return self._telemetry_cache[cache_key]

        # Default telemetry when nothing available
        return {
            "position": {
                "latitude": 47.3977,
                "longitude": 8.5456,
                "altitude": 488.0,
                "relative_altitude": 0.0,
            },
            "battery": {"voltage": 12.6, "remaining_percent": 100.0},
            "flight_mode": "UNKNOWN",
            "armed": False,
            "connected": False,
        }

    async def close(self):
        """Close the API client."""
        await self.client.aclose()
