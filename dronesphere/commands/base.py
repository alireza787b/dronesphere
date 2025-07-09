# dronesphere/commands/base.py
# =====================================

"""Base command implementation."""

import abc
import asyncio
from typing import Any

from ..backends.base import AbstractBackend
from ..core.logging import get_logger
from ..core.models import CommandResult

logger = get_logger(__name__)


class BaseCommand(abc.ABC):
    """Base class for all drone commands."""

    def __init__(self, name: str, parameters: dict[str, Any] | None = None):
        self.name = name
        self.parameters = parameters or {}
        self._cancelled = False
        self._cancel_event = asyncio.Event()

    @abc.abstractmethod
    async def run(self, backend: AbstractBackend, **params) -> CommandResult:
        """Execute the command.

        Args:
            backend: Drone backend to use for execution
            **params: Command parameters

        Returns:
            CommandResult with success status and details
        """
        pass

    async def cancel(self) -> None:
        """Cancel the command execution.

        Default implementation sets cancel flag and event.
        Commands should override if they need custom cancellation logic.
        """
        logger.info("command_cancelled", command=self.name)
        self._cancelled = True
        self._cancel_event.set()

    @property
    def cancelled(self) -> bool:
        """Check if command has been cancelled."""
        return self._cancelled

    async def check_cancelled(self) -> None:
        """Check if cancelled and raise if so."""
        if self._cancelled:
            raise asyncio.CancelledError(f"Command {self.name} was cancelled")

    async def wait_for_cancel_or_condition(
        self, condition_coro, timeout: float | None = None
    ):
        """Wait for either cancellation or a condition to be met.

        Args:
            condition_coro: Coroutine that returns True when condition is met
            timeout: Optional timeout in seconds

        Returns:
            True if condition met, False if cancelled or timeout
        """
        try:
            cancel_task = asyncio.create_task(self._cancel_event.wait())
            condition_task = asyncio.create_task(condition_coro)

            if timeout:
                done, pending = await asyncio.wait(
                    [cancel_task, condition_task],
                    timeout=timeout,
                    return_when=asyncio.FIRST_COMPLETED,
                )
            else:
                done, pending = await asyncio.wait(
                    [cancel_task, condition_task], return_when=asyncio.FIRST_COMPLETED
                )

            # Cancel pending tasks
            for task in pending:
                task.cancel()

            # Check results
            if cancel_task in done:
                return False  # Cancelled
            elif condition_task in done:
                return True  # Condition met
            else:
                return False  # Timeout

        except Exception as e:
            logger.error("wait_condition_failed", command=self.name, error=str(e))
            return False


class MockCommand(BaseCommand):
    """Mock command for testing."""

    def __init__(self, name: str, duration: float = 1.0, should_fail: bool = False):
        super().__init__(name)
        self.duration = duration
        self.should_fail = should_fail

    async def run(self, backend: AbstractBackend, **params) -> CommandResult:
        """Mock command execution."""
        logger.info("mock_command_started", command=self.name, duration=self.duration)

        try:
            # Simulate work
            for i in range(int(self.duration * 10)):  # 0.1s increments
                await self.check_cancelled()
                await asyncio.sleep(0.1)

            if self.should_fail:
                return CommandResult(
                    success=False,
                    message=f"Mock command {self.name} failed as requested",
                    error="Simulated failure",
                )

            return CommandResult(
                success=True,
                message=f"Mock command {self.name} completed",
                duration=self.duration,
            )

        except asyncio.CancelledError:
            return CommandResult(
                success=False,
                message=f"Mock command {self.name} was cancelled",
                error="Cancelled",
            )
