"""RTL (Return to Launch) command implementation using native PX4 RTL."""

import asyncio

from dronesphere.backends.base import AbstractBackend
from dronesphere.core.models import CommandResult, DroneState
from dronesphere.core.logging import get_logger
from dronesphere.commands.base import BaseCommand

logger = get_logger(__name__)


class RtlCommand(BaseCommand):
    """Command to return to launch position using native PX4 RTL."""
    
    async def run(self, backend: AbstractBackend, **params) -> CommandResult:
        """Execute RTL command."""
        timeout = params.get("timeout", 120.0)  # RTL can take longer
        wait_for_landing = params.get("wait_for_landing", True)  # Wait for complete RTL sequence
        
        logger.info("rtl_command_started", 
                   command_id=id(self),
                   timeout=timeout,
                   wait_for_landing=wait_for_landing,
                   drone_id=backend.drone_id)
        
        try:
            # Check if drone is flying or can RTL
            initial_state = await backend.get_state()
            if initial_state == DroneState.DISCONNECTED:
                return CommandResult(
                    success=False,
                    message="Cannot RTL: drone disconnected",
                    error="Drone not connected"
                )
                
            # RTL can be executed from most states (flying, loitering, etc.)
            if initial_state in [DroneState.DISARMED, DroneState.CONNECTED]:
                return CommandResult(
                    success=True,
                    message="Drone already on ground - RTL not needed",
                    data={"already_on_ground": True}
                )
                
            start_time = asyncio.get_event_loop().time()
            
            # Execute RTL using native PX4 command
            logger.info("executing_rtl", drone_id=backend.drone_id)
            await backend.return_to_launch()
            await self.check_cancelled()
            
            # Wait for RTL completion
            success = await self._wait_for_rtl_completion(backend, timeout, wait_for_landing)
            
            duration = asyncio.get_event_loop().time() - start_time
            
            if success:
                logger.info("rtl_command_completed",
                           command_id=id(self),
                           duration=duration,
                           drone_id=backend.drone_id)
                           
                return CommandResult(
                    success=True,
                    message="RTL completed successfully",
                    duration=duration,
                    data={
                        "rtl_duration": duration,
                        "waited_for_landing": wait_for_landing
                    }
                )
            else:
                return CommandResult(
                    success=False,
                    message="RTL timed out or failed",
                    error="RTL timeout",
                    duration=duration,
                    data={
                        "rtl_duration": duration,
                        "timeout": timeout
                    }
                )
                
        except asyncio.CancelledError:
            logger.info("rtl_command_cancelled", 
                       command_id=id(self),
                       drone_id=backend.drone_id)
            return CommandResult(
                success=False,
                message="RTL command was cancelled",
                error="Cancelled"
            )
            
        except Exception as e:
            logger.error("rtl_command_failed",
                        command_id=id(self), 
                        error=str(e),
                        drone_id=backend.drone_id)
            return CommandResult(
                success=False,
                message=f"RTL failed: {str(e)}",
                error=str(e)
            )
            
    async def cancel(self) -> None:
        """Cancel RTL command."""
        await super().cancel()
        
    async def _wait_for_rtl_completion(
        self, 
        backend: AbstractBackend, 
        timeout: float = 120.0,
        wait_for_landing: bool = True
    ) -> bool:
        """Wait for RTL to complete."""
        
        logger.info("waiting_for_rtl_completion", 
                   timeout=timeout,
                   wait_for_landing=wait_for_landing,
                   drone_id=backend.drone_id)
        
        async def check_rtl_completed():
            """Check if RTL is completed."""
            max_checks = int(timeout / 0.5)
            rtl_started = False
            
            for check_num in range(max_checks):
                try:
                    await self.check_cancelled()
                    
                    # Get current state and flight mode
                    state = await backend.get_state()
                    flight_mode = await backend.get_flight_mode()
                    
                    # Log progress every 10 seconds
                    if check_num % 20 == 0:  # Every 10 seconds (20 * 0.5s)
                        logger.info("rtl_progress",
                                   state=state,
                                   flight_mode=flight_mode,
                                   elapsed_time=check_num * 0.5,
                                   wait_for_landing=wait_for_landing,
                                   drone_id=backend.drone_id)
                    
                    # Check if RTL mode is active
                    if "RTL" in str(flight_mode) or "RETURN" in str(flight_mode):
                        rtl_started = True
                        logger.info("rtl_mode_active", 
                                   flight_mode=flight_mode,
                                   drone_id=backend.drone_id)
                    
                    # If we don't need to wait for landing, RTL command success = RTL mode activated
                    if not wait_for_landing and rtl_started:
                        logger.info("rtl_command_accepted", 
                                   flight_mode=flight_mode,
                                   drone_id=backend.drone_id)
                        return True
                    
                    # If waiting for landing, check for landing completion
                    if wait_for_landing:
                        # Success: drone disarmed (RTL with landing completed)
                        if state in [DroneState.DISARMED, DroneState.CONNECTED]:
                            logger.info("rtl_landing_complete", 
                                       state=state,
                                       drone_id=backend.drone_id)
                            return True
                            
                        # Also check for explicit landing state
                        if state == DroneState.LANDING:
                            logger.info("rtl_landing_in_progress", 
                                       state=state,
                                       drone_id=backend.drone_id)
                    
                    # Failure: disconnected
                    if state == DroneState.DISCONNECTED:
                        logger.warning("rtl_disconnected", drone_id=backend.drone_id)
                        return False
                        
                except Exception as e:
                    logger.warning("rtl_check_failed", 
                                 error=str(e), 
                                 drone_id=backend.drone_id)
                    
                await asyncio.sleep(0.5)
                
            logger.warning("rtl_timeout", 
                          timeout=timeout,
                          wait_for_landing=wait_for_landing,
                          rtl_started=rtl_started,
                          drone_id=backend.drone_id)
            return False
            
        return await self.wait_for_cancel_or_condition(check_rtl_completed(), timeout)