"""Takeoff command implementation.

Path: agent/commands/takeoff.py  
"""
import asyncio
import time
from .base import BaseCommand
from shared.models import CommandResult


class TakeoffCommand(BaseCommand):
    """Take off to specified altitude."""
    
    def validate_params(self) -> None:
        """Validate takeoff parameters."""
        altitude = self.params.get('altitude', 10.0)
        
        if not isinstance(altitude, (int, float)):
            raise ValueError("altitude must be a number")
            
        if not 1.0 <= altitude <= 50.0:
            raise ValueError(f"altitude must be between 1-50m, got {altitude}m")
    
    async def execute(self, backend) -> CommandResult:
        """Execute takeoff using MAVSDK backend."""
        start_time = time.time()
        
        try:
            altitude = float(self.params.get('altitude', 10.0))
            
            if not backend.connected:
                return CommandResult(
                    success=False,
                    message="Backend not connected to drone",
                    error="backend_disconnected"
                )
            
            print(f"🚁 Executing takeoff to {altitude}m...")
            
            # Get MAVSDK drone instance
            drone = backend.drone
            
            # Arm the drone
            print("🔧 Arming drone...")
            await drone.action.arm()
            
            # Set takeoff altitude
            await drone.action.set_takeoff_altitude(altitude)
            
            # Execute takeoff
            print(f"🚀 Taking off to {altitude}m...")
            await drone.action.takeoff()
            
            # Wait for takeoff completion (simple approach for MVP)
            await asyncio.sleep(8)  # Give time for takeoff
            
            duration = time.time() - start_time
            
            print(f"✅ Takeoff completed in {duration:.1f}s")
            return CommandResult(
                success=True,
                message=f"Takeoff to {altitude}m completed successfully",
                duration=duration
            )
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = str(e)
            print(f"❌ Takeoff failed: {error_msg}")
            
            return CommandResult(
                success=False,
                message=f"Takeoff failed: {error_msg}",
                error=error_msg,
                duration=duration
            )
