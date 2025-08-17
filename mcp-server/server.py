#!/usr/bin/env python3
"""DroneSphere MCP Server - Main Entry Point.

Path: mcp-server/server.py

Handles server initialization, lifecycle, and transport configuration.
All tools are defined in tools.py for better organization.
"""

import logging
import os
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import yaml
from dotenv import load_dotenv
from mcp.server.fastmcp import Context, FastMCP

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import our modules
from core.drone_api import DroneAPI
from core.llm_handler import LLMHandler
from tools import register_all_tools

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO if os.getenv("DEBUG_MODE") == "true" else logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


@dataclass
class AppContext:
    """Application context with shared dependencies."""

    drone_api: DroneAPI
    llm_handler: LLMHandler
    config: Dict[str, Any]
    active_commands: Dict[str, str]  # command_id -> description


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage application lifecycle and dependencies.

    Args:
        server: FastMCP server instance

    Yields:
        AppContext with initialized dependencies
    """
    logger.info("Initializing DroneSphere MCP Server...")

    # Load configuration
    config_path = Path(__file__).parent / "prompts" / "config.yaml"
    if config_path.exists():
        with open(config_path) as f:
            config = yaml.safe_load(f)
    else:
        config = {"safety": {}, "custom_rules": []}

    # Initialize services
    server_url = os.getenv("DRONESPHERE_SERVER_URL", "http://localhost:8002")
    drone_api = DroneAPI(server_url)
    llm_handler = LLMHandler()

    logger.info(f"Connected to DroneSphere backend: {server_url}")
    logger.info("Ready for natural language drone control")

    try:
        yield AppContext(
            drone_api=drone_api, llm_handler=llm_handler, config=config, active_commands={}
        )
    finally:
        await drone_api.close()
        logger.info("Server cleanup complete")


# Initialize FastMCP server
mcp = FastMCP(
    name="DroneSphere Control",
    instructions="""Natural language drone control system with coordinate transformations.

Features:
- Natural language commands in multiple languages
- Coordinate transformations (Body ↔ NED ↔ Global)
- Asynchronous command execution
- Real-time telemetry with GPS status

Available tools:
- execute_drone_command: Natural language control
- get_drone_status: Full telemetry including GPS
- check_command_status: Monitor executing commands
- transform_body_to_ned: Body frame to world coordinates
- transform_ned_to_body: World to body frame
- transform_ned_to_global: NED to GPS coordinates
- transform_global_to_ned: GPS to NED coordinates

Examples:
- 'takeoff to 10m then fly forward 5m'
- 'move 10 meters north and 5 meters east'
- 'go to GPS 47.398, 8.546 at 50m altitude'
""",
    lifespan=app_lifespan,
)


def get_app_context_from_mcp_context(ctx: Context) -> AppContext:
    """Extract AppContext from MCP Context.

    Args:
        ctx: MCP Context from tool

    Returns:
        AppContext instance
    """
    return ctx.request_context.lifespan_context


# Register all tools from tools.py
register_all_tools(mcp, get_app_context_from_mcp_context)


def main():
    """Main entry point with transport selection."""
    import sys

    # Parse command line arguments
    transport = "sse"  # Default for n8n
    if len(sys.argv) > 1:
        transport = sys.argv[1].lower()

    # Configure server
    port = int(os.getenv("MCP_PORT", 8003))
    host = "0.0.0.0"

    # Clean up any existing process on the port
    os.system(f"lsof -ti:{port} | xargs -r kill -TERM 2>/dev/null || true")

    if transport == "stdio":
        # STDIO mode for Claude Desktop
        logger.info("Starting STDIO transport for Claude Desktop")
        mcp.run(transport="stdio")

    elif transport == "sse":
        # SSE mode for n8n - use uvicorn
        logger.info(f"Starting SSE transport on {host}:{port}")
        logger.info(f"n8n URL: http://172.17.0.1:{port}/sse")

        import uvicorn

        # Get ASGI app from FastMCP
        app = mcp.sse_app()

        # Run with uvicorn
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="info" if os.getenv("DEBUG_MODE") == "true" else "warning",
        )

    else:
        print(f"Unknown transport: {transport}")
        print("Usage: python server.py [stdio|sse]")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)
