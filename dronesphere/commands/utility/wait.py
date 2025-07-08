"""Wait command implementation with FIXED parameter handling."""
import asyncio
from dronesphere.backends.base import AbstractBackend
from dronesphere.core.models import CommandResult
from dronesphere.core.logging import get_logger
from dronesphere.commands.base import BaseCommand

logger = get_logger(__name__)


class WaitCommand(BaseCommand):
    """Command to wait for specified duration with robust parameter handling."""
    
    async def run(self, backend: AbstractBackend, **params) -> CommandResult:
        """Execute wait command with proper parameter isolation."""
        
        # FIX: Extract duration parameter correctly and don't overwrite it
        requested_duration = params.get("duration", params.get("seconds", 1.0))
        
        logger.info("wait_command_started", 
                   command_id=id(self),
                   requested_duration=requested_duration,
                   received_params=params,
                   drone_id=backend.drone_id)
        
        try:
            start_time = asyncio.get_event_loop().time()
            
            # Wait in small increments to allow for cancellation
            elapsed = 0.0
            while elapsed < requested_duration:
                await self.check_cancelled()
                
                # Wait for 0.1s or remaining time, whichever is smaller
                wait_time = min(0.1, requested_duration - elapsed)
                await asyncio.sleep(wait_time)
                elapsed += wait_time
                
                # Log progress every second for long waits
                if requested_duration > 2.0 and int(elapsed) != int(elapsed - wait_time):
                    logger.info("wait_progress",
                               elapsed=elapsed,
                               remaining=requested_duration - elapsed,
                               drone_id=backend.drone_id)
            
            # FIX: Calculate actual duration without overwriting requested_duration
            actual_duration = asyncio.get_event_loop().time() - start_time
            
            logger.info("wait_command_completed",
                       command_id=id(self),
                       requested_duration=requested_duration,
                       actual_duration=actual_duration,
                       accuracy=abs(actual_duration - requested_duration),
                       drone_id=backend.drone_id)
                       
            return CommandResult(
                success=True,
                message=f"Wait completed ({requested_duration}s requested, {actual_duration:.2f}s actual)",
                duration=actual_duration,
                data={
                    "requested_duration": requested_duration,
                    "actual_duration": actual_duration,
                    "accuracy": abs(actual_duration - requested_duration)
                }
            )
            
        except asyncio.CancelledError:
            elapsed_time = asyncio.get_event_loop().time() - start_time
            logger.info("wait_command_cancelled", 
                       command_id=id(self),
                       elapsed=elapsed_time,
                       requested=requested_duration,
                       drone_id=backend.drone_id)
            return CommandResult(
                success=False,
                message=f"Wait cancelled after {elapsed_time:.1f}s of {requested_duration}s",
                error="Cancelled",
                duration=elapsed_time
            )
            
        except Exception as e:
            elapsed_time = asyncio.get_event_loop().time() - start_time
            logger.error("wait_command_failed",
                        command_id=id(self), 
                        error=str(e),
                        elapsed=elapsed_time,
                        requested=requested_duration,
                        drone_id=backend.drone_id)
            return CommandResult(
                success=False,
                message=f"Wait failed: {str(e)}",
                error=str(e),
                duration=elapsed_time
            )
            
    async def cancel(self) -> None:
        """Cancel wait command with proper cleanup."""
        logger.info("wait_command_cancel_requested", command_id=id(self))
        await super().cancel()