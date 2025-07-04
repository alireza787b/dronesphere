"""Server main entry point."""

import asyncio
import signal
import sys

import uvicorn

from ..agent.main import get_agent
from ..core.config import get_settings
from ..core.logging import get_logger, setup_logging

logger = get_logger(__name__)


async def start_server_with_agent():
    """Start server with embedded agent."""
    # Setup logging
    settings = get_settings()
    setup_logging(level=settings.logging.level, log_format=settings.logging.format)
    
    logger.info("server_starting_with_agent",
               host=settings.server.host,
               port=settings.server.port)
    
    # Start agent
    agent = get_agent()
    
    try:
        # Start agent in background
        await agent.start()
        
        # Give agent time to initialize
        await asyncio.sleep(2.0)
        
        # Start server
        config = uvicorn.Config(
            "dronesphere.server.api:app",
            host=settings.server.host,
            port=settings.server.port,
            log_level=settings.logging.level.lower(),
            reload=settings.debug,
            access_log=False,  # We handle our own logging
        )
        
        server = uvicorn.Server(config)
        
        # Setup graceful shutdown
        def signal_handler(sig, frame):
            logger.info("shutdown_signal_received", signal=sig)
            agent.signal_shutdown()
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Run server
        await server.serve()
        
    except Exception as e:
        logger.error("server_failed", error=str(e))
        raise
    finally:
        # Shutdown agent
        await agent.shutdown()


def main():
    """Main entry point for the server."""
    try:
        asyncio.run(start_server_with_agent())
    except KeyboardInterrupt:
        logger.info("server_interrupted")
    except Exception as e:
        logger.error("server_main_failed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
