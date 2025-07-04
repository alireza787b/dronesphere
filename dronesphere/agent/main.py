"""Agent main entry point."""

import asyncio
import signal
import sys
from typing import Dict

from ..commands.registry import load_command_library
from ..core.config import get_settings
from ..core.logging import get_logger, setup_logging
from .connection import DroneConnection
from .runner import CommandRunner

logger = get_logger(__name__)


class Agent:
    """Main agent class managing drone connections and command execution."""
    
    def __init__(self):
        self.connections: Dict[int, DroneConnection] = {}
        self.runners: Dict[int, CommandRunner] = {}
        self._shutdown_event = asyncio.Event()
        
    async def start(self) -> None:
        """Start the agent."""
        logger.info("agent_starting")
        
        # Load command library
        load_command_library()
        
        # For MVP, we only support drone ID 1
        drone_id = 1
        
        try:
            # Create and connect drone
            connection = DroneConnection(drone_id)
            await connection.connect()
            self.connections[drone_id] = connection
            
            # Create and start command runner
            runner = CommandRunner(connection)
            await runner.start()
            self.runners[drone_id] = runner
            
            logger.info("agent_started", supported_drones=[drone_id])
            
        except Exception as e:
            logger.error("agent_start_failed", error=str(e))
            await self.shutdown()
            raise
            
    async def shutdown(self) -> None:
        """Shutdown the agent."""
        logger.info("agent_shutting_down")
        
        try:
            # Stop all runners
            for drone_id, runner in self.runners.items():
                logger.info("stopping_runner", drone_id=drone_id)
                await runner.stop()
                
            # Disconnect all drones
            for drone_id, connection in self.connections.items():
                logger.info("disconnecting_drone", drone_id=drone_id)
                await connection.disconnect()
                
            self.runners.clear()
            self.connections.clear()
            
            logger.info("agent_shutdown_complete")
            
        except Exception as e:
            logger.error("agent_shutdown_failed", error=str(e))
            
    def get_connection(self, drone_id: int) -> DroneConnection:
        """Get drone connection by ID."""
        if drone_id not in self.connections:
            raise ValueError(f"Drone {drone_id} not connected")
        return self.connections[drone_id]
        
    def get_runner(self, drone_id: int) -> CommandRunner:
        """Get command runner by drone ID."""
        if drone_id not in self.runners:
            raise ValueError(f"Runner for drone {drone_id} not available")
        return self.runners[drone_id]
        
    async def wait_for_shutdown(self) -> None:
        """Wait for shutdown signal."""
        await self._shutdown_event.wait()
        
    def signal_shutdown(self) -> None:
        """Signal shutdown."""
        self._shutdown_event.set()


# Global agent instance
_agent: Agent = None


def get_agent() -> Agent:
    """Get the global agent instance."""
    global _agent
    if _agent is None:
        _agent = Agent()
    return _agent


def main() -> None:
    """Main entry point for the agent."""
    # Setup logging
    settings = get_settings()
    setup_logging(level=settings.logging.level, log_format=settings.logging.format)
    
    logger.info("agent_main_starting", 
               config={
                   "backend": settings.backend.default_backend,
                   "telemetry": settings.backend.telemetry_backend,
                   "connection": settings.agent.drone_connection_string,
               })
    
    agent = get_agent()
    
    # Setup signal handlers
    def signal_handler(sig, frame):
        logger.info("shutdown_signal_received", signal=sig)
        agent.signal_shutdown()
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    async def run_agent():
        try:
            # Start agent
            await agent.start()
            
            # Wait for shutdown signal
            await agent.wait_for_shutdown()
            
        except KeyboardInterrupt:
            logger.info("keyboard_interrupt_received")
        except Exception as e:
            logger.error("agent_main_failed", error=str(e))
            sys.exit(1)
        finally:
            # Shutdown
            await agent.shutdown()
            
        logger.info("agent_main_completed")
    
    # Run the async main function
    asyncio.run(run_agent())


if __name__ == "__main__":
    main()
