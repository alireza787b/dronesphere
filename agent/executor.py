"""Command execution engine with sequence support.

Path: agent/executor.py
"""
import asyncio
import time
from typing import List
import sys
import os

# Add parent directory to path for shared imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.models import Command, CommandResult, CommandMode
from .commands.takeoff import TakeoffCommand
from .commands.land import LandCommand
from .commands.rtl import RTLCommand


class CommandExecutor:
    """Executes command sequences with proper error handling."""
    
    def __init__(self, backend):
        """Initialize executor with drone backend.
        
        Args:
            backend: DroneBackend instance for drone communication
        """
        self.backend = backend
        self.command_map = {
            "takeoff": TakeoffCommand,
            "land": LandCommand, 
            "rtl": RTLCommand
        }
        self.current_sequence = []
        self.executing = False
    
    async def execute_sequence(self, commands: List[Command]) -> List[CommandResult]:
        """Execute a sequence of commands with proper error handling.
        
        Args:
            commands: List of Command objects to execute
            
        Returns:
            List of CommandResult objects for each command
        """
        if self.executing:
            return [CommandResult(
                success=False,
                message="Executor is already running a sequence",
                error="executor_busy"
            )]
        
        self.executing = True
        self.current_sequence = commands
        results = []
        
        try:
            print(f"🎯 Starting command sequence with {len(commands)} commands")
            
            for i, cmd in enumerate(commands):
                print(f"📝 Command {i+1}/{len(commands)}: {cmd.name}")
                
                try:
                    # Validate command exists
                    if cmd.name not in self.command_map:
                        result = CommandResult(
                            success=False,
                            message=f"Unknown command: {cmd.name}",
                            error="unknown_command"
                        )
                        results.append(result)
                        
                        if cmd.mode == CommandMode.CRITICAL:
                            print("💥 Critical command failed - triggering emergency RTL")
                            await self._emergency_rtl()
                            break
                        continue
                    
                    # Create and execute command
                    command_class = self.command_map[cmd.name]
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
                        elif cmd.mode == CommandMode.SKIP:
                            print("⏭️  Skipping to next command")
                            continue
                        # CONTINUE mode continues regardless
                        
                    else:
                        print(f"✅ Command {cmd.name} completed successfully")
                
                except Exception as e:
                    print(f"💥 Unexpected error in command {cmd.name}: {e}")
                    result = CommandResult(
                        success=False,
                        message=f"Command execution error: {str(e)}",
                        error=str(e)
                    )
                    results.append(result)
                    
                    if cmd.mode == CommandMode.CRITICAL:
                        print("💥 Critical command error - triggering emergency RTL")
                        await self._emergency_rtl()
                        break
            
            print(f"🎯 Sequence completed: {sum(1 for r in results if r.success)}/{len(results)} successful")
            return results
            
        finally:
            self.executing = False
            self.current_sequence = []
    
    async def _emergency_rtl(self):
        """Execute emergency return to launch."""
        try:
            print("🚨 Emergency RTL initiated")
            rtl_cmd = RTLCommand("rtl", {})
            result = await rtl_cmd.execute(self.backend)
            
            if result.success:
                print("🚨 Emergency RTL completed")
            else:
                print(f"🚨 Emergency RTL failed: {result.message}")
                
        except Exception as e:
            print(f"🚨 Emergency RTL critical failure: {e}")
