"""Base command class for all drone commands.

Path: agent/commands/base.py
"""
import os
import sys
from abc import ABC, abstractmethod
from typing import Any, Dict

# Add parent directory to path for shared imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.models import CommandResult


class BaseCommand(ABC):
    """Abstract base class for all drone commands."""

    def __init__(self, name: str, params: Dict[str, Any]):
        """Initialize command with name and parameters.

        Args:
            name: Command identifier
            params: Command-specific parameters
        """
        self.name = name
        self.params = params
        self.validate_params()

    def validate_params(self) -> None:
        """Validate command parameters. Override in subclasses."""
        pass

    @abstractmethod
    async def execute(self, backend) -> CommandResult:
        """Execute the command using the provided backend.

        Args:
            backend: DroneBackend instance for communication

        Returns:
            CommandResult with execution status
        """
        pass
