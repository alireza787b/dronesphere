# Copy content from "Complete Clean agent/runner.py" artifact above
# dronesphere/agent/runner.py
# ===================================

"""Command execution runner."""

import asyncio
from datetime import datetime
from typing import Dict, Optional

from ..commands.base import BaseCommand
from ..commands.registry import get_command_registry
from ..core.errors import CommandExecutionError, CommandValidationError
from ..core.logging import get_logger
from ..core.models import (
    CommandEnvelope, CommandExecution, CommandResult, CommandStatus, DroneState
)
from .connection import DroneConnection

logger = get_logger(__name__)


class CommandRunner:
    """Manages command execution for a single drone."""
    
    def __init__(self, drone_connection: DroneConnection):
        self.drone_connection = drone_connection
        self.drone_id = drone_connection.drone_id
        self.command_queue: asyncio.Queue = asyncio.Queue()
        self.current_execution: Optional[CommandExecution] = None
        self.execution_history: Dict[str, CommandExecution] = {}
        self._runner_task: Optional[asyncio.Task] = None
        self._running = False
        
    async def start(self) -> None:
        """Start the command runner."""
        if self._running:
            return
            
        self._running = True
        self._runner_task = asyncio.create_task(self._execution_loop())
        logger.info("command_runner_started", drone_id=self.drone_id)
        
    async def stop(self) -> None:
        """Stop the command runner."""
        self._running = False
        
        # Cancel current execution
        if self.current_execution:
            await self._cancel_current_execution()
            
        # Cancel runner task
        if self._runner_task:
            self._runner_task.cancel()
            try:
                await self._runner_task
            except asyncio.CancelledError:
                pass
            self._runner_task = None
            
        logger.info("command_runner_stopped", drone_id=self.drone_id)
        
    async def enqueue_command(self, envelope: CommandEnvelope) -> str:
        """Enqueue a command envelope for execution."""
        try:
            # Validate all commands in sequence
            registry = get_command_registry()
            for cmd_request in envelope.sequence:
                registry.validate_parameters(cmd_request.name, cmd_request.params)
                
            # Cancel current execution if running
            if self.current_execution and self.current_execution.status == CommandStatus.EXECUTING:
                logger.info("cancelling_current_command_for_new", 
                           drone_id=self.drone_id,
                           current_id=self.current_execution.id,
                           new_id=envelope.id)
                await self._cancel_current_execution()
                
            # Clear queue and add new command
            while not self.command_queue.empty():
                try:
                    self.command_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
                    
            await self.command_queue.put(envelope)
            
            logger.info("command_enqueued", 
                       drone_id=self.drone_id,
                       command_id=envelope.id,
                       sequence_length=len(envelope.sequence))
            
            return envelope.id
            
        except Exception as e:
            logger.error("command_enqueue_failed", 
                        drone_id=self.drone_id,
                        error=str(e))
            raise CommandValidationError(f"Failed to enqueue command: {e}")
            
    def get_queue_size(self) -> int:
        """Get current queue size."""
        return self.command_queue.qsize()
        
    def get_current_execution(self) -> Optional[CommandExecution]:
        """Get current command execution."""
        return self.current_execution
        
    def get_execution_history(self, command_id: str) -> Optional[CommandExecution]:
        """Get execution from history."""
        return self.execution_history.get(command_id)
        
    async def _execution_loop(self) -> None:
        """Main execution loop."""
        logger.info("execution_loop_started", drone_id=self.drone_id)
        
        try:
            while self._running:
                try:
                    # Wait for command envelope
                    envelope = await asyncio.wait_for(
                        self.command_queue.get(), timeout=1.0
                    )
                    
                    # Execute command sequence
                    await self._execute_sequence(envelope)
                    
                except asyncio.TimeoutError:
                    # No commands in queue, continue loop
                    continue
                except Exception as e:
                    logger.error("execution_loop_error", 
                               drone_id=self.drone_id, 
                               error=str(e))
                    await asyncio.sleep(1.0)  # Brief pause before retry
                    
        except asyncio.CancelledError:
            logger.info("execution_loop_cancelled", drone_id=self.drone_id)
        except Exception as e:
            logger.error("execution_loop_failed", 
                        drone_id=self.drone_id, 
                        error=str(e))
        finally:
            logger.info("execution_loop_stopped", drone_id=self.drone_id)
            
    async def _execute_sequence(self, envelope: CommandEnvelope) -> None:
        """Execute a command sequence with soft failure support."""
        logger.info("sequence_execution_started", 
                   drone_id=self.drone_id,
                   sequence_id=envelope.id,
                   commands=len(envelope.sequence))
        
        registry = get_command_registry()
        sequence_results = []
        
        for i, cmd_request in enumerate(envelope.sequence):
            if not self._running:
                break
                
            try:
                # Create command execution record
                execution = CommandExecution(
                    id=f"{envelope.id}-{i}",
                    command=cmd_request,
                    status=CommandStatus.EXECUTING,
                    started_at=datetime.utcnow()
                )
                
                self.current_execution = execution
                self.execution_history[execution.id] = execution
                
                logger.info("command_execution_started",
                           drone_id=self.drone_id,
                           execution_id=execution.id,
                           command=cmd_request.name)
                
                # Create command instance
                command = registry.create_command(cmd_request.name, cmd_request.params)
                
                # Check drone state before execution
                if not await self._check_drone_ready(command):
                    result = CommandResult(
                        success=False,
                        message="Drone not ready for command execution",
                        error="Drone not connected or in invalid state"
                    )
                else:
                    # Execute command
                    result = await self._execute_command(command)
                
                # Update execution record
                execution.completed_at = datetime.utcnow()
                execution.result = result
                execution.status = CommandStatus.COMPLETED if result.success else CommandStatus.FAILED
                sequence_results.append(result)
                
                logger.info("command_execution_completed",
                           drone_id=self.drone_id,
                           execution_id=execution.id,
                           success=result.success,
                           duration=result.duration)
                
                # Enhanced failure handling
                if not result.success:
                    failure_behavior = self._get_failure_behavior(cmd_request.name, result)
                    
                    if failure_behavior == "stop":
                        logger.error("sequence_stopped_on_critical_failure",
                                   drone_id=self.drone_id,
                                   failed_command=cmd_request.name,
                                   error=result.error)
                        break
                    elif failure_behavior == "warn":
                        logger.warning("sequence_continuing_after_soft_failure",
                                     drone_id=self.drone_id,
                                     failed_command=cmd_request.name,
                                     error=result.error,
                                     remaining_commands=len(envelope.sequence) - i - 1)
                        # Continue to next command
                else:
                    # Check for partial success warnings
                    if (result.data and 
                        (result.data.get("partial_success") or result.data.get("tolerance_met"))):
                        logger.info("command_partial_success",
                                   drone_id=self.drone_id,
                                   command=cmd_request.name,
                                   details=result.data)
                    
            except Exception as e:
                logger.error("command_execution_error",
                           drone_id=self.drone_id,
                           command=cmd_request.name,
                           error=str(e))
                
                if self.current_execution:
                    self.current_execution.status = CommandStatus.FAILED
                    self.current_execution.completed_at = datetime.utcnow()
                    error_result = CommandResult(
                        success=False,
                        message=f"Command execution failed: {str(e)}",
                        error=str(e)
                    )
                    self.current_execution.result = error_result
                    sequence_results.append(error_result)
                
                # Stop on unexpected errors
                break
                
        self.current_execution = None
        
        # Log sequence summary
        total_commands = len(envelope.sequence)
        successful_commands = sum(1 for r in sequence_results if r.success)
        failed_commands = total_commands - successful_commands
        
        logger.info("sequence_execution_completed", 
                   drone_id=self.drone_id,
                   sequence_id=envelope.id,
                   total_commands=total_commands,
                   successful=successful_commands,
                   failed=failed_commands)
    
    def _get_failure_behavior(self, command_name: str, result: CommandResult) -> str:
        """Determine how to handle command failure.
        
        Returns:
            "stop" - Stop sequence on this failure
            "warn" - Log warning and continue 
        """
        # Commands that should stop sequence on failure
        critical_commands = {
            "land": "stop",        # Landing failure is critical
            "emergency": "stop",   # Emergency commands must succeed
            "arm": "stop",         # Arming failure stops flight
        }
        
        # Commands that can fail without stopping sequence
        soft_failure_commands = {
            "wait": "warn",        # Wait can be skipped
            "takeoff": "warn",     # Takeoff can partially succeed
            "goto": "warn",        # Navigation can be approximated
            "circle": "warn",      # Patterns can be skipped
        }
        
        # Check for partial success indicators
        if (result.data and 
            (result.data.get("partial_success") or 
             result.data.get("already_flying") or 
             result.data.get("tolerance_met"))):
            return "warn"  # Treat partial success as warning
        
        # Use command-specific behavior
        return critical_commands.get(command_name, 
                                   soft_failure_commands.get(command_name, "stop"))
        
    async def _execute_command(self, command: BaseCommand) -> CommandResult:
        """Execute a single command."""
        if not self.drone_connection.backend:
            raise CommandExecutionError("No backend available")
            
        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                command.run(self.drone_connection.backend, **command.parameters),
                timeout=60.0  # Default timeout, could be configurable per command
            )
            return result
            
        except asyncio.TimeoutError:
            await command.cancel()
            return CommandResult(
                success=False,
                message=f"Command {command.name} timed out",
                error="Timeout"
            )
        except asyncio.CancelledError:
            return CommandResult(
                success=False,
                message=f"Command {command.name} was cancelled",
                error="Cancelled"
            )
            
    async def _check_drone_ready(self, command: BaseCommand) -> bool:
        """Check if drone is ready for command execution."""
        if not self.drone_connection.connected:
            return False
            
        state = await self.drone_connection.get_state()
        
        # Allow most commands when connected, but be more restrictive for flight commands
        if state == DroneState.DISCONNECTED:
            return False
            
        # For takeoff, require disarmed or connected state
        if command.name == "takeoff" and state not in [
            DroneState.DISARMED, DroneState.CONNECTED
        ]:
            return False
            
        # For land, require flying state
        if command.name == "land" and state not in [
            DroneState.FLYING, DroneState.TAKEOFF, DroneState.LANDING
        ]:
            return False
            
        return True
        
    def _is_non_critical_command(self, command_name: str) -> bool:
        """Check if command is non-critical (sequence continues on failure)."""
        non_critical = ["wait"]  # Wait command failure shouldn't stop sequence
        return command_name in non_critical
        
    async def _cancel_current_execution(self) -> None:
        """Cancel currently executing command."""
        if not self.current_execution:
            return
            
        try:
            execution = self.current_execution
            logger.info("cancelling_current_execution",
                       drone_id=self.drone_id,
                       execution_id=execution.id)
            
            # Mark as cancelled
            execution.status = CommandStatus.CANCELLED
            execution.completed_at = datetime.utcnow()
            
            # Try to emergency stop the drone
            await self.drone_connection.emergency_stop()
            
            logger.info("current_execution_cancelled",
                       drone_id=self.drone_id,
                       execution_id=execution.id)
            
        except Exception as e:
            logger.error("cancel_execution_failed",
                        drone_id=self.drone_id,
                        error=str(e))