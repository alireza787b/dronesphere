"""Drone connection management."""

import asyncio
from typing import Optional

from ..backends.base import AbstractBackend, BackendFactory, TelemetryProvider
from ..core.config import get_settings
from ..core.errors import DroneConnectionError
from ..core.logging import get_logger
from ..core.models import DroneState, Telemetry

logger = get_logger(__name__)


class DroneConnection:
    """Manages connection to a single drone."""
    
    def __init__(self, drone_id: int):
        self.drone_id = drone_id
        self.backend: Optional[AbstractBackend] = None
        self.telemetry_provider: Optional[TelemetryProvider] = None
        self._connected = False
        self._telemetry_cache: Optional[Telemetry] = None
        self._telemetry_task: Optional[asyncio.Task] = None
        
    async def connect(self) -> None:
        """Connect to the drone."""
        settings = get_settings()
        
        try:
            logger.info("connecting_drone", drone_id=self.drone_id)
            
            # Create backend
            self.backend = BackendFactory.create_backend(
                backend_type=settings.backend.default_backend,
                drone_id=self.drone_id,
                connection_string=settings.agent.drone_connection_string
            )
            
            # Create telemetry provider (using same backend for now)
            self.telemetry_provider = BackendFactory.create_telemetry_provider(
                provider_type=settings.backend.telemetry_backend,
                drone_id=self.drone_id,
                connection_string=settings.agent.drone_connection_string
            )
            
            # Connect backend
            await self.backend.connect()
            
            # Connect telemetry
            await self.telemetry_provider.connect()
            
            self._connected = True
            
            # Start telemetry updates
            await self._start_telemetry_updates()
            
            logger.info("drone_connected", 
                       drone_id=self.drone_id,
                       backend=settings.backend.default_backend,
                       telemetry=settings.backend.telemetry_backend)
            
        except Exception as e:
            logger.error("drone_connection_failed", 
                        drone_id=self.drone_id, 
                        error=str(e))
            await self.disconnect()
            raise DroneConnectionError(f"Failed to connect drone {self.drone_id}: {e}")
            
    async def disconnect(self) -> None:
        """Disconnect from the drone."""
        try:
            logger.info("disconnecting_drone", drone_id=self.drone_id)
            
            # Stop telemetry updates
            if self._telemetry_task:
                self._telemetry_task.cancel()
                try:
                    await self._telemetry_task
                except asyncio.CancelledError:
                    pass
                self._telemetry_task = None
                
            # Disconnect telemetry provider
            if self.telemetry_provider:
                await self.telemetry_provider.disconnect()
                self.telemetry_provider = None
                
            # Disconnect backend
            if self.backend:
                await self.backend.disconnect()
                self.backend = None
                
            self._connected = False
            self._telemetry_cache = None
            
            logger.info("drone_disconnected", drone_id=self.drone_id)
            
        except Exception as e:
            logger.error("drone_disconnect_failed", 
                        drone_id=self.drone_id, 
                        error=str(e))
            
    @property
    def connected(self) -> bool:
        """Check if connected to drone."""
        return self._connected and self.backend and self.backend.connected
        
    async def get_telemetry(self) -> Optional[Telemetry]:
        """Get cached telemetry data."""
        return self._telemetry_cache
        
    async def get_state(self) -> DroneState:
        """Get current drone state."""
        if not self.backend or not self.connected:
            return DroneState.DISCONNECTED
            
        try:
            return await self.backend.get_state()
        except Exception as e:
            logger.error("get_state_failed", drone_id=self.drone_id, error=str(e))
            return DroneState.DISCONNECTED
            
    async def emergency_stop(self) -> None:
        """Execute emergency stop."""
        if self.backend and self.connected:
            try:
                logger.warning("emergency_stop_initiated", drone_id=self.drone_id)
                await self.backend.emergency_stop()
            except Exception as e:
                logger.error("emergency_stop_failed", 
                           drone_id=self.drone_id, 
                           error=str(e))
                
    async def _start_telemetry_updates(self) -> None:
        """Start background telemetry updates."""
        if self._telemetry_task:
            return  # Already running
            
        self._telemetry_task = asyncio.create_task(self._telemetry_update_loop())
        
    async def _telemetry_update_loop(self) -> None:
        """Background telemetry update loop."""
        settings = get_settings()
        update_interval = settings.agent.telemetry_update_interval
        
        logger.info("telemetry_updates_started", 
                   drone_id=self.drone_id,
                   interval=update_interval)
        
        try:
            while self._connected and self.telemetry_provider:
                try:
                    # Get fresh telemetry
                    telemetry = await self.telemetry_provider.get_telemetry()
                    self._telemetry_cache = telemetry
                    
                    logger.debug("telemetry_updated", 
                               drone_id=self.drone_id,
                               state=telemetry.state,
                               armed=telemetry.armed)
                    
                except Exception as e:
                    logger.warning("telemetry_update_failed", 
                                 drone_id=self.drone_id, 
                                 error=str(e))
                    
                await asyncio.sleep(update_interval)
                
        except asyncio.CancelledError:
            logger.info("telemetry_updates_cancelled", drone_id=self.drone_id)
        except Exception as e:
            logger.error("telemetry_loop_failed", 
                        drone_id=self.drone_id, 
                        error=str(e))
        finally:
            logger.info("telemetry_updates_stopped", drone_id=self.drone_id)
