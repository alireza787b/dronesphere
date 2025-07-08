"""Agent main module - handles single drone operations.

This module provides the main DroneAgent class that manages a single drone's
operations, including hardware connection, command execution, and server communication.
"""

import asyncio
import signal
from typing import Optional

import uvicorn

from dronesphere.core.config import get_settings
from dronesphere.core.logging import get_logger
from dronesphere.commands.registry import load_command_library
from .executor import CommandRunner, DroneConnection  
from .config import get_agent_settings
from .heartbeat import HeartbeatManager
from .instance import set_agent

logger = get_logger(__name__)

class DroneAgent:
    """Agent managing a single drone."""
    
    def __init__(self, drone_id: int = 1):
        self.drone_id = drone_id
        self.settings = get_agent_settings()
        self.connection: Optional[DroneConnection] = None
        self.runner: Optional[CommandRunner] = None
        self.heartbeat: Optional[HeartbeatManager] = None
        self._running = False
        self._shutdown_requested = False
        
    async def start(self) -> None:
        """Start the agent."""
        if self._running:
            return
            
        logger.info("agent_starting", drone_id=self.drone_id)
        
        try:
            # Load command library
            load_command_library()
            
            # Create drone connection
            self.connection = DroneConnection(
                drone_id=self.drone_id,
                connection_string=self.settings.drone_connection_string
            )
            
            # Connect to drone
            await self.connection.connect()
            
            # Create command runner
            self.runner = CommandRunner(self.connection)
            await self.runner.start()
            
            # Start heartbeat to server
            self.heartbeat = HeartbeatManager(
                agent_port=self.settings.port,
                server_host=self.settings.server_host,
                server_port=self.settings.server_port,
                interval=self.settings.heartbeat_interval
            )
            await self.heartbeat.start()
            
            self._running = True
            logger.info("agent_started", drone_id=self.drone_id)
            
        except Exception as e:
            logger.error("agent_start_failed", drone_id=self.drone_id, error=str(e))
            await self.stop()
            raise
            
    async def stop(self) -> None:
        """Stop the agent."""
        if not self._running:
            return
            
        logger.info("agent_stopping", drone_id=self.drone_id)
        
        self._running = False
        
        # Stop heartbeat
        if self.heartbeat:
            await self.heartbeat.stop()
            
        # Stop command runner
        if self.runner:
            await self.runner.stop()
            
        # Disconnect from drone
        if self.connection:
            await self.connection.disconnect()
            
        logger.info("agent_stopped", drone_id=self.drone_id)
        
    def request_shutdown(self) -> None:
        """Request shutdown (signal-safe)."""
        self._shutdown_requested = True

async def main():
    """Agent entry point with FastAPI server."""
    agent = DroneAgent()
    settings = get_agent_settings()
    
    # Set global agent instance for API
    set_agent(agent)
    
    # Setup signal handlers (FIX: Make them signal-safe)
    def signal_handler(signum, frame):
        logger.info("shutdown_signal_received", signal=signum)
        agent.request_shutdown()
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start agent hardware connection
        await agent.start()
        
        # Import API app after agent is set up
        from .api import app
        
        # Start FastAPI server
        logger.info("agent_api_starting", host=settings.host, port=settings.port)
        config = uvicorn.Config(
            app,
            host=settings.host,
            port=settings.port,
            log_level="info",
            access_log=True
        )
        
        server = uvicorn.Server(config)
        
        # Run server with shutdown monitoring
        server_task = asyncio.create_task(server.serve())
        
        # Monitor for shutdown requests
        while not agent._shutdown_requested and not server_task.done():
            await asyncio.sleep(0.1)
            
        # Shutdown sequence
        if not server_task.done():
            server.should_exit = True
            await server_task
        
    except KeyboardInterrupt:
        logger.info("keyboard_interrupt")
    except Exception as e:
        logger.error("agent_main_error", error=str(e))
    finally:
        await agent.stop()

if __name__ == "__main__":
    asyncio.run(main())
