"""Command execution engine for DroneSphere agents.

Path: agent/executor.py
Handles command sequence execution with dynamic command loading.
"""
import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from shared.models import Command, CommandMode, CommandResult

from .command_registry import CommandRegistry
from .commands.rtl import RTLCommand  # Keep for emergency RTL

logger = logging.getLogger(__name__)


class CommandExecutor:
    """Executes command sequences with dynamic command loading."""

    def __init__(self, backend):
        """Initialize executor with backend connection.

        Args:
            backend: MAVSDK backend instance for drone communication
        """
        self.backend = backend
        self.registry = CommandRegistry()
        self.current_sequence = []
        self.executing = False

        # Discover and register commands
        self._initialize_commands()

    def _initialize_commands(self):
        """Initialize dynamic command registry."""
        try:
            self.registry.discover_and_register()
            logger.info(f"🚀 Loaded {len(self.registry.commands)} commands dynamically")

            # Verify critical commands are loaded
            critical_commands = ["takeoff", "land", "rtl", "goto", "wait"]
            for cmd in critical_commands:
                if cmd not in self.registry.commands:
                    logger.warning(f"⚠️ Critical command '{cmd}' not loaded!")

        except Exception as e:
            logger.error(f"Failed to initialize command registry: {e}")
            # Fall back to empty registry (will fail gracefully on command execution)

    async def execute_sequence(self, commands: List[Command]) -> List[CommandResult]:
        """Execute a sequence of commands with proper error handling.

        Args:
            commands: List of Command objects to execute

        Returns:
            List[CommandResult]: Results for each command executed
        """
        if self.executing:
            raise RuntimeError("Executor is already running a command sequence")

        self.executing = True
        self.current_sequence = commands.copy()
        results = []

        try:
            print(f"🚀 Starting command sequence with {len(commands)} commands")

            for i, cmd in enumerate(commands):
                print(f"\n📋 [{i+1}/{len(commands)}] Executing: {cmd.name}")

                # Validate command exists
                command_class = self.registry.get_command_class(cmd.name)
                if not command_class:
                    result = CommandResult(
                        success=False,
                        message=f"Unknown command: {cmd.name}",
                        error="unknown_command",
                    )
                    results.append(result)

                    if cmd.mode == CommandMode.CRITICAL:
                        print("💥 Critical command failed - triggering emergency RTL")
                        await self._emergency_rtl()
                        break
                    elif cmd.mode == CommandMode.ABORT_ON_FAIL:
                        print("🛑 Command sequence aborted due to failure")
                        break
                    else:
                        print("⚠️  Continuing sequence despite command failure")
                        continue

                # Validate parameters
                validation_errors = self.registry.validate_params(cmd.name, cmd.params)
                if validation_errors:
                    result = CommandResult(
                        success=False,
                        message=f"Invalid parameters: {'; '.join(validation_errors)}",
                        error="invalid_parameters",
                    )
                    results.append(result)

                    if cmd.mode == CommandMode.CRITICAL:
                        print("💥 Critical command validation failed - triggering emergency RTL")
                        await self._emergency_rtl()
                        break
                    else:
                        print("⚠️  Continuing despite validation failure")
                        continue

                # Execute command
                try:
                    command_instance = command_class(cmd.name, cmd.params)
                    result = await command_instance.execute(self.backend)
                    results.append(result)

                    # Handle failure based on command mode
                    if not result.success:
                        print(f"⚠️  Command {cmd.name} failed: {result.message}")

                        if cmd.mode == CommandMode.CRITICAL:
                            print("💥 Critical command failed - triggering emergency RTL")
                            await self._emergency_rtl()
                            break
                        elif cmd.mode == CommandMode.ABORT_ON_FAIL:
                            print("🛑 Command sequence aborted due to failure")
                            break
                        else:
                            print("⚠️  Continuing sequence despite command failure")
                    else:
                        print(f"✅ Command {cmd.name} completed successfully")

                except Exception as e:
                    print(f"💥 Command {cmd.name} threw exception: {str(e)}")
                    result = CommandResult(
                        success=False, message=f"Command execution error: {str(e)}", error=str(e)
                    )
                    results.append(result)

                    if cmd.mode == CommandMode.CRITICAL:
                        print("💥 Critical command exception - triggering emergency RTL")
                        await self._emergency_rtl()
                        break
                    elif cmd.mode == CommandMode.ABORT_ON_FAIL:
                        print("🛑 Command sequence aborted due to exception")
                        break
                    else:
                        print("⚠️  Continuing sequence despite exception")

            print(f"\n🏁 Command sequence completed. {len(results)} commands processed.")

        finally:
            self.executing = False
            self.current_sequence = []

        return results

    async def _emergency_rtl(self):
        """Execute emergency return-to-launch."""
        try:
            print("🚨 Emergency RTL triggered")
            rtl_command = RTLCommand("rtl", {})
            await rtl_command.execute(self.backend)
        except Exception as e:
            print(f"💥 Emergency RTL failed: {str(e)}")

    def get_available_commands(self) -> List[str]:
        """Get list of available command names.

        Returns:
            List[str]: Available command names
        """
        return self.registry.list_commands()

    def is_executing(self) -> bool:
        """Check if executor is currently running commands.

        Returns:
            bool: True if executing, False otherwise
        """
        return self.executing

    def get_current_sequence(self) -> List[Command]:
        """Get copy of current command sequence.

        Returns:
            List[Command]: Current sequence (empty if not executing)
        """
        return self.current_sequence.copy()

    async def abort_sequence(self) -> bool:
        """Abort current command sequence if running.

        Returns:
            bool: True if sequence was aborted, False if not executing
        """
        if not self.executing:
            return False

        print("🛑 Aborting command sequence...")
        self.executing = False
        self.current_sequence = []

        # Trigger emergency RTL for safety
        await self._emergency_rtl()
        return True

    def get_command_info(self) -> List[Dict[str, Any]]:
        """Get information about all available commands.

        Returns:
            List of command information dictionaries
        """
        return self.registry.get_command_info()
