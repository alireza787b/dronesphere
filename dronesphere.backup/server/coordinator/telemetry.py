# server/coordinator/telemetry.py
"""Telemetry caching for multi-drone coordination."""

import asyncio
import time
from typing import Dict, Optional, Any

from dronesphere.core.logging import get_logger
from ..config import get_server_settings
from .fleet import FleetManager

logger = get_logger(__name__)


class TelemetryCache:
    """Caches telemetry from all drones."""
    
    def __init__(self, fleet_manager: FleetManager):
        self.fleet_manager = fleet_manager
        self.settings = get_server_settings()
        self.cache: Dict[int, Dict[str, Any]] = {}
        self._running = False
        self._cache_task: Optional[asyncio.Task] = None
        
    async def start(self) -> None:
        """Start telemetry caching."""
        if self._running:
            return
            
        logger.info("telemetry_cache_starting",
                   interval=self.settings.telemetry_cache_interval)
        
        self._running = True
        self._cache_task = asyncio.create_task(self._cache_loop())
        
    async def stop(self) -> None:
        """Stop telemetry caching."""
        self._running = False
        
        if self._cache_task:
            self._cache_task.cancel()
            try:
                await self._cache_task
            except asyncio.CancelledError:
                pass
            self._cache_task = None
            
        logger.info("telemetry_cache_stopped")
        
    async def _cache_loop(self) -> None:
        """Telemetry caching loop."""
        while self._running:
            try:
                await self._update_cache()
            except Exception as e:
                logger.error("telemetry_cache_error", error=str(e))
                
            await asyncio.sleep(max(2.0, self.settings.telemetry_cache_interval))  # Min 2 second interval
            
    async def _update_cache(self) -> None:
        """Update telemetry cache for all drones."""
        connected_drones = self.fleet_manager.get_connected_drones()
        
        # Gather telemetry from all connected drones
        tasks = []
        for drone in connected_drones:
            task = self._get_drone_telemetry(drone.id, drone.agent_host, drone.agent_port)
            tasks.append(task)
            
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, result in enumerate(results):
                drone = connected_drones[i]
                if isinstance(result, Exception):
                    logger.warning("telemetry_fetch_failed", 
                                 drone_id=drone.id, 
                                 error=str(result))
                elif result:
                    self.cache[drone.id] = {
                        **result,
                        "cached_at": time.time()
                    }
                    
    async def _get_drone_telemetry(
        self, 
        drone_id: int, 
        agent_host: str, 
        agent_port: int
    ) -> Optional[Dict[str, Any]]:
        """Get telemetry from specific drone."""
        return await self.fleet_manager.client.get_agent_telemetry(agent_host, agent_port)
        
    def get_drone_telemetry(self, drone_id: int) -> Optional[Dict[str, Any]]:
        """Get cached telemetry for specific drone."""
        return self.cache.get(drone_id)
        
    def get_all_telemetry(self) -> Dict[int, Dict[str, Any]]:
        """Get cached telemetry for all drones."""
        return self.cache.copy()
        
    def get_cache_age(self, drone_id: int) -> Optional[float]:
        """Get age of cached telemetry in seconds."""
        telemetry = self.cache.get(drone_id)
        if not telemetry or "cached_at" not in telemetry:
            return None
            
        return time.time() - telemetry["cached_at"]