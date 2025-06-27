# agent/src/agent/main.py
"""
DroneSphere Agent Main Entry Point

This module starts the drone agent that connects to both the flight controller
(via MAVSDK) and the control server (via WebSocket).

Usage:
    python -m agent.main [--config CONFIG_FILE]
"""

import asyncio
import signal
import sys
from pathlib import Path

import click
import structlog
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import AgentSettings

from agent.connection import DroneConnection
from agent.executor import CommandExecutor
from agent.telemetry import TelemetryStreamer

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.dev.ConsoleRenderer(colors=True),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


class DroneAgent:
    """
    Main drone agent class that orchestrates all components.

    This class manages:
    - Connection to the flight controller (MAVSDK)
    - WebSocket connection to the control server
    - Command execution
    - Telemetry streaming
    """

    def __init__(self, settings: AgentSettings):
        """
        Initialize the drone agent.

        Args:
            settings: Agent configuration settings
        """
        self.settings = settings
        self.drone_connection: DroneConnection | None = None
        self.command_executor: CommandExecutor | None = None
        self.telemetry_streamer: TelemetryStreamer | None = None
        self._running = False

    async def start(self) -> None:
        """Start the drone agent and all its components."""
        logger.info("Starting DroneSphere Agent", version="0.1.0")

        try:
            # Initialize drone connection
            self.drone_connection = DroneConnection(
                system_address=self.settings.mavsdk_server_address,
                port=self.settings.mavsdk_server_port,
            )
            await self.drone_connection.connect()

            # Initialize command executor
            self.command_executor = CommandExecutor(
                drone_connection=self.drone_connection,
                server_url=self.settings.server_url,
            )

            # Initialize telemetry streamer
            self.telemetry_streamer = TelemetryStreamer(
                drone_connection=self.drone_connection,
                server_url=self.settings.server_url,
                stream_rate=self.settings.telemetry_rate,
            )

            # Start components
            self._running = True
            await asyncio.gather(
                self.command_executor.start(),
                self.telemetry_streamer.start(),
                self._monitor_connection(),
            )

        except Exception as e:
            logger.error("Failed to start agent", error=str(e))
            await self.stop()
            raise

    async def stop(self) -> None:
        """Stop the drone agent and cleanup resources."""
        logger.info("Stopping DroneSphere Agent")
        self._running = False

        # Stop components
        if self.telemetry_streamer:
            await self.telemetry_streamer.stop()
        if self.command_executor:
            await self.command_executor.stop()
        if self.drone_connection:
            await self.drone_connection.disconnect()

    async def _monitor_connection(self) -> None:
        """Monitor drone connection health."""
        while self._running:
            if self.drone_connection and not await self.drone_connection.is_connected():
                logger.warning("Drone connection lost, attempting reconnection")
                try:
                    await self.drone_connection.connect()
                    logger.info("Reconnection successful")
                except Exception as e:
                    logger.error("Reconnection failed", error=str(e))

            await asyncio.sleep(5)  # Check every 5 seconds


async def shutdown(agent: DroneAgent, loop: asyncio.AbstractEventLoop) -> None:
    """Gracefully shutdown the agent."""
    logger.info("Received shutdown signal")
    await agent.stop()

    # Cancel all running tasks
    tasks = [t for t in asyncio.all_tasks(loop) if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()

    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()


@click.command()
@click.option(
    "--config",
    default="config/agent.yaml",
    help="Path to configuration file",
    type=click.Path(exists=False),
)
@click.option(
    "--dev",
    is_flag=True,
    help="Run in development mode with debug logging",
)
def main(config: str, dev: bool) -> None:
    """
    DroneSphere Agent - Drone-side control software.

    This agent runs on the companion computer and manages communication
    between the flight controller and the control server.
    """
    # Load environment variables
    load_dotenv()

    # Load settings
    settings = (
        AgentSettings.from_file(config) if Path(config).exists() else AgentSettings()
    )

    if dev:
        settings.log_level = "DEBUG"
        logger.info("Running in development mode")

    # Create event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Create and start agent
    agent = DroneAgent(settings)

    # Setup signal handlers
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown(agent, loop)))

    try:
        loop.run_until_complete(agent.start())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error("Agent crashed", error=str(e), exc_info=True)
    finally:
        loop.close()
        logger.info("Agent stopped")


if __name__ == "__main__":
    main()
