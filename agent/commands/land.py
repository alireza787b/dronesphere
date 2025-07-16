"""Land command implementation.

Path: agent/commands/land.py
"""
import asyncio
import time
from .base import BaseCommand
from shared.models import CommandResult


class LandCommand(BaseCommand):
    """Land the drone at current position."""
    
    def validate_params(self) -> None:
        """Land command has no parameters to validate."""
        pass
    
    async def execute(self, backend) -> CommandResult:
        """Execute landing using MAVSDK backend."""
        start_time = time.time()
        
        try:
            if not backend.connected:
                return CommandResult(
                    success=False,
                    message="Backend not connected to drone",
                    error="backend_disconnected"
                )
            
            print("🛬 Executing landing...")
            
            # Get MAVSDK drone instance
            drone = backend.drone
            
            # Execute landing
            await drone.action.land()
            
            # Wait for landing completion
            await asyncio.sleep(10)  # Give time for landing
            
            duration = time.time() - start_time
            
            print(f"✅ Landing completed in {duration:.1f}s")
            return CommandResult(
                success=True,
                message="Landing completed successfully",
                duration=duration
            )
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = str(e)
            print(f"❌ Landing failed: {error_msg}")
            
            return CommandResult(
                success=False,
                message=f"Landing failed: {error_msg}",
                error=error_msg,
                duration=duration
            )
