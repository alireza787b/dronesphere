"""Command execution runner for agent.

This module provides the CommandRunner class that handles command execution
and queue management for drone operations.
"""

import asyncio
from datetime import datetime
from typing import Dict, Optional

from dronesphere.commands.base import BaseCommand
from dronesphere.commands.registry import get_command_registry
from dronesphere.core.errors import CommandExecutionError, CommandValidationError
from dronesphere.core.logging import get_logger
from dronesphere.core.models import (
    CommandResult,
    CommandEnvelope, CommandExecution, CommandResult, CommandStatus, DroneState, CommandRequest
)
from .connection import DroneConnection

logger = get_logger(__name__)


class CommandRunner:
    """Handles command execution and queue management."""
    
    def __init__(self, connection: DroneConnection):
        self.connection = connection
        self.execution_queue: asyncio.Queue = asyncio.Queue()
        self.execution_history: Dict[str, CommandExecution] = {}
        self.current_execution: Optional[CommandExecution] = None
        self._runner_task: Optional[asyncio.Task] = None
        self._running = False
        
    async def start(self) -> None:
        """Start the command runner."""
        if self._running:
            return
            
        self._running = True
        self._runner_task = asyncio.create_task(self._execution_loop())
        logger.info("command_runner_started")
        
    async def stop(self) -> None:
        """Stop the command runner."""
        self._running = False
        
        if self._runner_task:
            self._runner_task.cancel()
            try:
                await self._runner_task
            except asyncio.CancelledError:
                pass
            self._runner_task = None
            
        logger.info("command_runner_stopped")
        
    async def enqueue_command(self, envelope: CommandEnvelope) -> str:
        """Enqueue a command for execution."""
        # FIX: Use correct fields and status
        command_id = f"cmd_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        # Create CommandRequest from first command in sequence
        if not envelope.sequence:
            raise CommandValidationError("Empty command sequence")
            
        first_command = envelope.sequence[0]
        command_request = CommandRequest(
            name=first_command.name,
            params=first_command.params or {}
        )
        
        execution = CommandExecution(
            id=command_id,
            command=command_request,  # FIX: Use CommandRequest object
            status=CommandStatus.PENDING,  # FIX: Use PENDING instead of QUEUED
            started_at=datetime.now()
            # FIX: Remove drone_id (not in model)
        )
        
        self.execution_history[execution.id] = execution
        await self.execution_queue.put(envelope)
        
        logger.info("command_enqueued", command_id=execution.id)
        return execution.id
        
    async def _execution_loop(self) -> None:
        """Main execution loop."""
        while self._running:
            try:
                # Get next command from queue
                envelope = await asyncio.wait_for(
                    self.execution_queue.get(), 
                    timeout=1.0
                )
                
                # Execute command sequence
                await self._execute_sequence(envelope)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error("execution_loop_error", error=str(e))
                
    async def _execute_sequence(self, envelope: CommandEnvelope) -> None:
        """Execute a command sequence with robust error handling and failsafe logic."""
        sequence_failed = False
        
        for cmd_index, command in enumerate(envelope.sequence):
            try:
                # Get command implementation and spec
                registry = get_command_registry()
                command_spec = registry.get_spec(command.name)
                
                # Extract criticality from metadata
                metadata = command_spec.spec.get("metadata", {})
                is_critical = metadata.get("critical", False)
                failsafe_action = metadata.get("failsafe", None)
                max_retries = metadata.get("max_retries", 0)
                timeout_behavior = metadata.get("timeout_behavior", "continue")
                
                logger.info("executing_command", 
                           command=command.name, 
                           params=command.params,
                           critical=is_critical,
                           cmd_index=cmd_index + 1,
                           total_commands=len(envelope.sequence))
                
                # Execute command with retry logic
                result = None
                last_error = None
                
                for attempt in range(max_retries + 1):
                    try:
                        # Create fresh command instance for each retry
                        command_impl = registry.create_command(command.name, command.params or {})
                        
                        if attempt > 0:
                            logger.warning("command_retry", 
                                         command=command.name, 
                                         attempt=attempt + 1,
                                         max_retries=max_retries + 1)
                        
                        result = await command_impl.run(self.connection.backend, **command_impl.parameters)
                        
                        if result.success:
                            break  # Success, exit retry loop
                        else:
                            last_error = result.error
                            
                    except Exception as e:
                        last_error = str(e)
                        logger.error("command_execution_exception", 
                                   command=command.name, 
                                   attempt=attempt + 1,
                                   error=str(e))
                
                # Handle command result
                if result and result.success:
                    logger.info("command_completed", 
                               command=command.name, 
                               success=True,
                               duration=getattr(result, 'duration', 0))
                else:
                    # Command failed after all retries
                    logger.error("command_failed", 
                               command=command.name, 
                               error=last_error,
                               critical=is_critical,
                               retries_exhausted=max_retries)
                    
                    if is_critical:
                        # Critical command failed - execute failsafe
                        logger.error("critical_command_failed", 
                                   command=command.name,
                                   triggering_failsafe=failsafe_action)
                        
                        if failsafe_action:
                            await self._execute_failsafe(failsafe_action)
                        
                        sequence_failed = True
                        break  # Stop sequence execution
                    else:
                        # Non-critical command failed - continue with next command
                        logger.warning("noncritical_command_failed_continuing", 
                                     command=command.name,
                                     error=last_error)
                        continue
                    
            except Exception as e:
                logger.error("command_execution_error", 
                           command=command.name, 
                           error=str(e))
                
                # For unexpected errors, treat as critical failure
                logger.error("unexpected_error_triggering_failsafe", error=str(e))
                await self._execute_failsafe("land")
                sequence_failed = True
                break
        
        # Log sequence completion
        if sequence_failed:
            logger.error("command_sequence_failed", 
                       envelope_id=getattr(envelope, 'id', 'unknown'))
        else:
            logger.info("command_sequence_completed", 
                       envelope_id=getattr(envelope, 'id', 'unknown'),
                       commands_executed=len(envelope.sequence))
    
    async def _execute_failsafe(self, failsafe_action: str) -> None:
        """Execute failsafe action."""
        try:
            logger.warning("executing_failsafe", action=failsafe_action)
            
            if failsafe_action == "land":
                # Emergency land
                registry = get_command_registry()
                land_command = registry.create_command("land", {})
                result = await land_command.run(self.connection.backend, **land_command.parameters)
                
                if result.success:
                    logger.info("failsafe_land_completed")
                else:
                    logger.error("failsafe_land_failed", error=result.error)
                    
            elif failsafe_action == "rtl":
                # Return to launch
                registry = get_command_registry()
                rtl_command = registry.create_command("rtl", {})
                result = await rtl_command.run(self.connection.backend, **rtl_command.parameters)
                
                if result.success:
                    logger.info("failsafe_rtl_completed")
                else:
                    logger.error("failsafe_rtl_failed", error=result.error)
                    
            elif failsafe_action == "emergency_stop":
                # Emergency stop
                await self.connection.emergency_stop()
                logger.info("failsafe_emergency_stop_completed")
                
        except Exception as e:
            logger.error("failsafe_execution_failed", 
                       action=failsafe_action, 
                       error=str(e))
    def get_current_execution(self) -> Optional[CommandExecution]:
        """Get currently executing command."""
        return self.current_execution
        
    def get_queue_size(self) -> int:
        """Get number of queued commands."""
        return self.execution_queue.qsize()
