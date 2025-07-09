"""Combined main entry point for agent + server."""

import asyncio
import signal
import sys
from concurrent.futures import ThreadPoolExecutor

import uvicorn

from .agent.main import get_agent
from .core.config import get_settings
from .core.logging import setup_logging, get_logger

logger = get_logger(__name__)


async def start_combined_system():
    """Start both agent and server in the same process."""
    settings = get_settings()
    
    # Setup logging
    setup_logging(level=settings.logging.level, log_format=settings.logging.format)
    
    logger.info("combined_system_starting")
    
    # Start agent
    agent = get_agent()
    
    try:
        # Start agent in background
        await agent.start()
        
        logger.info("agent_started_successfully")
        
        # Give agent a moment to stabilize
        await asyncio.sleep(2.0)
        
        # Configure uvicorn
        config = uvicorn.Config(
            "dronesphere.server.api:app",
            host=settings.server.host,
            port=settings.server.port,
            log_level=settings.logging.level.lower(),
            reload=False,  # Don't reload when running combined
            access_log=False,
        )
        
        server = uvicorn.Server(config)
        
        logger.info("starting_server", port=settings.server.port)
        
        # Setup graceful shutdown
        def signal_handler(sig, frame):
            logger.info("shutdown_signal_received", signal=sig)
            agent.signal_shutdown()
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Run server
        await server.serve()
        
    except Exception as e:
        logger.error("combined_system_failed", error=str(e))
        raise
    finally:
        # Shutdown agent
        await agent.shutdown()


def main():
    """Main entry point."""
    try:
        asyncio.run(start_combined_system())
    except KeyboardInterrupt:
        logger.info("system_interrupted")
    except Exception as e:
        logger.error("main_failed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
