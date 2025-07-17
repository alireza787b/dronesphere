"""wait command implementation for timing delays in command sequences.

Path: agent/commands/wait.py
Provides precise timing control for drone mission sequences.
"""
import asyncio
import time

from shared.models import CommandResult

from .base import BaseCommand


class WaitCommand(BaseCommand):
    """Wait for specified duration in command sequences.

    Useful for:
    - Mission timing coordination
    - Sensor stabilization delays
    - Formation flight synchronization
    - Data collection intervals

    Parameters:
        - duration: Wait time in seconds (float, 0.1 to 300.0)
        - message: Optional status message to display during wait
    """

    def validate_params(self) -> None:
        """Validate wait command parameters."""
        if "duration" not in self.params:
            raise ValueError("wait command requires 'duration' parameter")

        duration = self.params["duration"]

        if not isinstance(duration, (int, float)):
            raise ValueError("duration must be a number")

        if duration < 0.1:
            raise ValueError("duration must be at least 0.1 seconds")

        if duration > 300.0:
            raise ValueError("duration must not exceed 300 seconds (5 minutes)")

        # Validate optional message parameter
        if "message" in self.params:
            message = self.params["message"]
            if not isinstance(message, str):
                raise ValueError("message must be a string")
            if len(message) > 100:
                raise ValueError("message must not exceed 100 characters")

    async def execute(self, backend) -> CommandResult:
        """Execute wait command with precise timing."""
        start_time = time.time()

        try:
            duration = self.params["duration"]
            custom_message = self.params.get("message", "")

            if custom_message:
                print(f"⏱️  Waiting {duration}s: {custom_message}")
            else:
                print(f"⏱️  Waiting {duration} seconds...")

            # Perform the wait using asyncio.sleep for precise timing
            await asyncio.sleep(duration)

            actual_duration = time.time() - start_time
            timing_accuracy = abs(actual_duration - duration)

            # Consider timing accurate if within 10ms or 1% of target
            timing_threshold = max(0.01, duration * 0.01)
            timing_ok = timing_accuracy <= timing_threshold

            if timing_ok:
                message = f"wait completed successfully ({actual_duration:.2f}s)"
            else:
                message = f"wait completed with timing drift ({actual_duration:.2f}s vs {duration:.2f}s target)"

            return CommandResult(success=True, message=message, duration=actual_duration)

        except Exception as e:
            actual_duration = time.time() - start_time
            return CommandResult(
                success=False,
                message=f"wait failed: {str(e)}",
                error=str(e),
                duration=actual_duration,
            )
