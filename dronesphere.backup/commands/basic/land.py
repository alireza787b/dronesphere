"""Land command implementation with corrected imports."""

import asyncio

from dronesphere.backends.base import AbstractBackend
from dronesphere.core.models import CommandResult, DroneState
from dronesphere.core.logging import get_logger
from dronesphere.commands.base import BaseCommand

logger = get_logger(__name__)


class LandCommand(BaseCommand):
    """Command to land the drone."""
    
    async def run(self, backend: AbstractBackend, **params) -> CommandResult:
        """Execute land command."""
        timeout = params.get("timeout", 30)
        precision_land = params.get("precision_land", False)
        
        logger.info("land_command_started", 
                   command_id=id(self),
                   precision=precision_land,
                   drone_id=backend.drone_id)
        
        try:
            # Check if already on ground
            state = await backend.get_state()
            if state in [DroneState.DISARMED, DroneState.CONNECTED]:
                return CommandResult(
                    success=True,
                    message="Drone already on ground",
                    data={"already_landed": True}
                )
            
            if state == DroneState.DISCONNECTED:
                return CommandResult(
                    success=False,
                    message="Cannot land: drone disconnected",
                    error="Drone not connected"
                )
                
            start_time = asyncio.get_event_loop().time()
            
            # Execute landing
            logger.info("executing_land", drone_id=backend.drone_id)
            await backend.land()
            await self.check_cancelled()
            
            # Wait for landing completion
            success = await self._wait_for_landing_completion(backend, timeout)
            
            duration = asyncio.get_event_loop().time() - start_time
            
            if success:
                logger.info("land_command_completed",
                           command_id=id(self),
                           duration=duration,
                           drone_id=backend.drone_id)
                           
                return CommandResult(
                    success=True,
                    message="Landing completed successfully",
                    duration=duration
                )
            else:
                return CommandResult(
                    success=False,
                    message="Landing timed out or failed",
                    error="Timeout",
                    duration=duration
                )
                
        except asyncio.CancelledError:
            logger.info("land_command_cancelled", 
                       command_id=id(self),
                       drone_id=backend.drone_id)
            return CommandResult(
                success=False,
                message="Land command was cancelled",
                error="Cancelled"
            )
            
        except Exception as e:
            logger.error("land_command_failed",
                        command_id=id(self), 
                        error=str(e),
                        drone_id=backend.drone_id)
            return CommandResult(
                success=False,
                message=f"Landing failed: {str(e)}",
                error=str(e)
            )
            
    async def cancel(self) -> None:
        """Cancel land command."""
        await super().cancel()
        
    async def _wait_for_landing_completion(self, backend: AbstractBackend, timeout: float) -> bool:
        """Wait for landing to complete."""
        async def check_landed():
            max_checks = int(timeout / 0.5)
            
            for check_num in range(max_checks):
                try:
                    await self.check_cancelled()
                    
                    state = await backend.get_state()
                    
                    # Success: drone disarmed (landed)
                    if state in [DroneState.DISARMED, DroneState.CONNECTED]:
                        logger.info("landing_complete", drone_id=backend.drone_id)
                        return True
                        
                    # Failure: disconnected
                    if state == DroneState.DISCONNECTED:
                        logger.warning("landing_disconnected", drone_id=backend.drone_id)
                        return False
                    
                    # Log progress every 4 seconds
                    if check_num % 8 == 0:
                        logger.info("landing_progress", 
                                   state=state,
                                   elapsed_time=check_num * 0.5,
                                   drone_id=backend.drone_id)
                        
                except Exception as e:
                    logger.warning("landing_check_failed", error=str(e), drone_id=backend.drone_id)
                    
                await asyncio.sleep(0.5)
                
            logger.warning("landing_timeout", timeout=timeout, drone_id=backend.drone_id)
            return False
            
        return await self.wait_for_cancel_or_condition(check_landed(), timeout)