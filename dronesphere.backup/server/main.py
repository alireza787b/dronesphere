"""Server main module - multi-drone coordination.

This module provides the main server entry point for the DroneSphere coordination
service, handling fleet management, telemetry caching, and multi-drone operations.
"""

import asyncio
import signal

import uvicorn

from dronesphere.core.logging import get_logger
from dronesphere.commands.registry import load_command_library
from .api import app
from .config import get_server_settings

logger = get_logger(__name__)


async def main():
    """Server entry point."""
    settings = get_server_settings()
    
    logger.info("server_starting", port=settings.port)
    
    try:
        # Load command library for validation
        load_command_library()
        
        # Setup signal handlers
        def signal_handler():
            logger.info("shutdown_signal_received")
            
        signal.signal(signal.SIGINT, lambda s, f: signal_handler())
        signal.signal(signal.SIGTERM, lambda s, f: signal_handler())
        
        # Run server
        config = uvicorn.Config(
            app,
            host=settings.host,
            port=settings.port,
            log_level="info",
            access_log=True
        )
        
        server = uvicorn.Server(config)
        await server.serve()
        
    except KeyboardInterrupt:
        logger.info("keyboard_interrupt")
    except Exception as e:
        logger.error("server_main_error", error=str(e))

if __name__ == "__main__":
    asyncio.run(main())