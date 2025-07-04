"""Circle command implementation."""

import asyncio
from ..backends.base import AbstractBackend
from ..core.models import CommandResult, DroneState  
from ..core.logging import get_logger
from ..base import BaseCommand

logger = get_logger(__name__)


class CircleCommand(BaseCommand):
    """Command to fly in a circle pattern."""
    
    async def run(self, backend: AbstractBackend, **params) -> CommandResult:
        """Execute circle command."""
        radius = params.get("radius", 10.0)
        speed = params.get("speed", 2.0)
        turns = params.get("turns", 1.0)
        
        logger.info("circle_command_started",
                   command_id=id(self),
                   radius=radius,
                   speed=speed,
                   turns=turns,
                   drone_id=backend.drone_id)
        
        # Implementation would go here
        # For now, simulate the command
        duration = (2 * 3.14159 * radius * turns) / speed  # Estimated time
        await asyncio.sleep(min(duration, 5.0))  # Cap simulation at 5s
        
        return CommandResult(
            success=True,
            message=f"Completed {turns} circle(s) with radius {radius}m",
            duration=duration,
            data={
                "radius": radius,
                "turns_completed": turns,
                "estimated_distance": 2 * 3.14159 * radius * turns
            }
        )
