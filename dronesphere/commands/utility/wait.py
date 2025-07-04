"""Wait command implementation with corrected imports."""

import asyncio

from dronesphere.backends.base import AbstractBackend
from dronesphere.core.models import CommandResult
from dronesphere.core.logging import get_logger
from dronesphere.commands.base import BaseCommand

logger = get_logger(__name__)


class WaitCommand(BaseCommand):
    """Command to wait for specified duration."""
    
    async def run(self, backend: AbstractBackend, **params) -> CommandResult:
        """Execute wait command."""
        seconds = params.get("seconds", 1.0)
        
        logger.info("wait_command_started", 
                   command_id=id(self),
                   duration=seconds,
                   drone_id=backend.drone_id)
        
        try:
            start_time = asyncio.get_event_loop().time()
            
            # Wait in small increments to allow for cancellation
            elapsed = 0.0
            while elapsed < seconds:
                await self.check_cancelled()
                
                # Wait for 0.1 seconds or remaining time, whichever is smaller
                wait_time = min(0.1, seconds - elapsed)
                await asyncio.sleep(wait_time)
                elapsed += wait_time
                
                # Log progress every second for long waits
                if seconds > 2.0 and int(elapsed) != int(elapsed - wait_time):
                    logger.info("wait_progress",
                               elapsed=elapsed,
                               remaining=seconds - elapsed,
                               drone_id=backend.drone_id)
            
            duration = asyncio.get_event_loop().time() - start_time
            
            logger.info("wait_command_completed",
                       command_id=id(self),
                       requested_duration=seconds,
                       actual_duration=duration,
                       drone_id=backend.drone_id)
                       
            return CommandResult(
                success=True,
                message=f"Wait completed ({seconds}s)",
                duration=duration,
                data={"wait_duration": seconds}
            )
            
        except asyncio.CancelledError:
            elapsed_time = asyncio.get_event_loop().time() - start_time
            logger.info("wait_command_cancelled", 
                       command_id=id(self),
                       elapsed=elapsed_time,
                       requested=seconds,
                       drone_id=backend.drone_id)
            return CommandResult(
                success=False,
                message=f"Wait cancelled after {elapsed_time:.1f}s of {seconds}s",
                error="Cancelled",
                duration=elapsed_time
            )
            
        except Exception as e:
            logger.error("wait_command_failed",
                        command_id=id(self), 
                        error=str(e),
                        drone_id=backend.drone_id)
            return CommandResult(
                success=False,
                message=f"Wait failed: {str(e)}",
                error=str(e)
            )
            
    async def cancel(self) -> None:
        """Cancel wait command."""
        await super().cancel()