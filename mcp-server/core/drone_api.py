"""DroneSphere API Client - Wrapper for existing server endpoints.

Path: mcp-server/core/drone_api.py
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class DroneAPI:
    """Client for DroneSphere server API with robust async handling."""

    def __init__(self, base_url: str, timeout: float = 5.0):
        """Initialize API client.

        Args:
            base_url: DroneSphere server URL (e.g., http://localhost:8002)
            timeout: Request timeout in seconds (reduced for faster response)
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        # Use shorter timeout for better responsiveness
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=2.0,  # Connection timeout
                read=3.0,  # Read timeout
                write=3.0,  # Write timeout
                pool=5.0,  # Pool timeout
            )
        )
        self._telemetry_cache = {}
        self._cache_time = 0

    async def send_commands(
        self, commands: List[Dict[str, Any]], drone_id: int = 1, queue_mode: str = "override"
    ) -> Dict[str, Any]:
        """Send command sequence to drone with fire-and-forget option.

        Args:
            commands: List of command dicts
            drone_id: Target drone ID
            queue_mode: "override" or "append"

        Returns:
            API response dict or acknowledgment
        """
        try:
            # Fire and forget approach - don't wait for full execution
            response = await asyncio.wait_for(
                self.client.post(
                    f"{self.base_url}/fleet/commands",
                    json={"commands": commands, "target_drone": drone_id, "queue_mode": queue_mode},
                ),
                timeout=2.0,  # Quick acknowledgment timeout
            )

            if response.status_code == 200:
                return {
                    "success": True,
                    "message": "Commands queued for execution",
                    "status_code": response.status_code,
                }
            else:
                return {
                    "success": False,
                    "error": f"Server returned {response.status_code}",
                    "status_code": response.status_code,
                }

        except asyncio.TimeoutError:
            # Commands likely queued but response delayed
            logger.warning("Command acknowledgment timeout - commands may still execute")
            return {
                "success": True,
                "message": "Commands sent (acknowledgment timeout)",
                "warning": "Response delayed but commands likely executing",
            }
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return {"success": False, "error": str(e)}

    async def get_telemetry(self, drone_id: int = 1, use_cache: bool = True) -> Dict[str, Any]:
        """Get live telemetry from drone with intelligent caching.

        Args:
            drone_id: Target drone ID
            use_cache: Use cached data if recent (within 1 second)

        Returns:
            Telemetry dict with position, battery, etc.
        """
        import time

        current_time = time.time()

        # Return cached data if fresh (within 1 second)
        if use_cache and drone_id in self._telemetry_cache:
            if current_time - self._cache_time < 1.0:
                logger.debug("Using cached telemetry")
                return self._telemetry_cache[drone_id]

        try:
            response = await asyncio.wait_for(
                self.client.get(f"{self.base_url}/fleet/telemetry/{drone_id}/live"),
                timeout=2.0,  # Quick telemetry fetch
            )

            if response.status_code == 200:
                telemetry = response.json()
                # Cache the successful response
                self._telemetry_cache[drone_id] = telemetry
                self._cache_time = current_time
                return telemetry
            else:
                logger.warning(f"Telemetry fetch returned {response.status_code}")
                return self._get_default_telemetry(drone_id)

        except asyncio.TimeoutError:
            logger.warning("Telemetry fetch timeout, using defaults")
            return self._get_default_telemetry(drone_id)
        except Exception as e:
            logger.warning(f"Telemetry fetch failed: {e}")
            return self._get_default_telemetry(drone_id)

    def _get_default_telemetry(self, drone_id: int) -> Dict[str, Any]:
        """Return safe default telemetry when fetch fails.

        Args:
            drone_id: Drone ID

        Returns:
            Default telemetry structure
        """
        # Return cached data if available
        if drone_id in self._telemetry_cache:
            cached = self._telemetry_cache[drone_id].copy()
            cached["warning"] = "Using cached telemetry"
            return cached

        # Otherwise return safe defaults
        return {
            "drone_id": drone_id,
            "position": {
                "latitude": 47.3977509,
                "longitude": 8.5456079,
                "altitude": 0.0,
                "relative_altitude": 0.0,
            },
            "attitude": {"roll": 0.0, "pitch": 0.0, "yaw": 0.0},
            "battery": {"voltage": 12.6, "remaining_percent": 100.0},
            "flight_mode": "STABILIZE",
            "armed": False,
            "connected": False,
            "warning": "Telemetry unavailable - using defaults",
        }

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
