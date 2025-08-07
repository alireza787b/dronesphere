#!/usr/bin/env python3
"""DroneSphere MCP Server - FastMCP Implementation.

Path: mcp-server/server.py

This server provides natural language drone control through MCP protocol.
Supports both STDIO (Claude Desktop) and HTTP (n8n) transports.

Usage:
    python server.py          # HTTP mode for n8n (port 8003)
    python server.py stdio    # STDIO mode for Claude Desktop
    mcp dev server.py         # Development with inspector
"""

import asyncio
import logging
import os
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import yaml
from dotenv import load_dotenv

from mcp.server.fastmcp import Context, FastMCP

# Add core module to path
sys.path.insert(0, str(Path(__file__).parent))

from core.drone_api import DroneAPI
from core.llm_handler import LLMHandler

# Load environment variables
load_dotenv()

# Configure logging (CRITICAL: stderr only for STDIO mode)
logging.basicConfig(
    level=logging.INFO if os.getenv("DEBUG_MODE") == "true" else logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr,  # Never stdout!
)
logger = logging.getLogger(__name__)


@dataclass
class AppContext:
    """Application context with dependencies."""

    drone_api: DroneAPI
    llm_handler: LLMHandler
    config: Dict[str, Any]


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage application lifecycle with proper initialization."""
    # Load prompt configuration
    config_path = Path(__file__).parent / "prompts" / "config.yaml"
    if config_path.exists():
        with open(config_path) as f:
            config = yaml.safe_load(f)
    else:
        config = {"safety": {}, "custom_rules": []}

    # Initialize API clients
    server_url = os.getenv("DRONESPHERE_SERVER_URL", "http://62.60.206.251:8002")
    drone_api = DroneAPI(server_url)
    llm_handler = LLMHandler()

    logger.info(f"Initialized with server: {server_url}")

    try:
        yield AppContext(drone_api=drone_api, llm_handler=llm_handler, config=config)
    finally:
        # Cleanup
        await drone_api.close()
        logger.info("Cleanup complete")


# Initialize MCP server with lifespan
mcp = FastMCP(
    name="DroneSphere Control",
    instructions="""Natural language drone control system.
    Supports commands in any language.
    Commands: takeoff, land, goto, wait, rtl.
    Example: 'takeoff to 10m then go north 5m then land'""",
    lifespan=app_lifespan,
)


def get_safety_rules(config: Dict[str, Any]) -> str:
    """Get current safety rules based on mode.

    Args:
        config: Configuration dictionary

    Returns:
        Formatted safety rules string
    """
    sitl_mode = os.getenv("SITL_MODE", "false").lower() == "true"

    if sitl_mode:
        rules = config.get("safety", {}).get("sitl_mode", [])
    else:
        rules = config.get("safety", {}).get("production_mode", [])

    # Add custom rules
    custom = config.get("custom_rules", [])
    if custom:
        rules.extend(custom)

    return "\n".join(f"- {rule}" for rule in rules)


@mcp.tool()
async def execute_drone_command(
    command: str, drone_id: int = 1, ctx: Context = None
) -> Dict[str, Any]:
    """Execute natural language drone command.

    Path: mcp-server/server.py::execute_drone_command

    Understands any language and handles command sequences.
    Examples:
    - 'takeoff to 10 meters'
    - 'بلند شو به ۱۵ متر' (Persian)
    - 'go north 5m then wait 3 seconds then land'

    Args:
        command: Natural language command
        drone_id: Target drone ID (default: 1)
        ctx: MCP context with lifespan dependencies

    Returns:
        Execution result with status and details
    """
    try:
        # Get dependencies from context
        app_ctx = ctx.request_context.lifespan_context
        drone_api = app_ctx.drone_api
        llm_handler = app_ctx.llm_handler
        config = app_ctx.config

        # Get current telemetry for context
        telemetry = await drone_api.get_telemetry(drone_id)

        # Get safety rules
        safety_rules = get_safety_rules(config)

        # Parse with LLM
        commands = await llm_handler.parse_command(command, telemetry, safety_rules)

        if not commands:
            return {
                "success": False,
                "error": "Could not understand command",
                "suggestion": "Try simpler commands like 'takeoff to 10m' or 'land'",
            }

        # Log if debug mode
        if os.getenv("DEBUG_MODE") == "true":
            logger.info(f"Parsed commands: {commands}")

        # Execute command sequence
        result = await drone_api.send_commands(commands, drone_id)

        return {
            "success": result.get("success", False),
            "executed_commands": commands,
            "command_count": len(commands),
            "response": result.get("message", "Commands sent"),
            "original_request": command,
        }

    except Exception as e:
        logger.error(f"Command execution failed: {e}")
        return {"success": False, "error": str(e), "original_request": command}


@mcp.tool()
async def get_drone_status(drone_id: int = 1, ctx: Context = None) -> Dict[str, Any]:
    """Get current drone telemetry and status.

    Path: mcp-server/server.py::get_drone_status

    Args:
        drone_id: Target drone ID (default: 1)
        ctx: MCP context with lifespan dependencies

    Returns:
        Current telemetry including position, battery, mode
    """
    try:
        # Get drone API from context
        app_ctx = ctx.request_context.lifespan_context
        drone_api = app_ctx.drone_api

        telemetry = await drone_api.get_telemetry(drone_id)

        # Format for readability
        return {
            "drone_id": drone_id,
            "connected": telemetry.get("connected", False),
            "armed": telemetry.get("armed", False),
            "mode": telemetry.get("flight_mode", "UNKNOWN"),
            "position": {
                "altitude": telemetry.get("position", {}).get("relative_altitude", 0.0),
                "latitude": telemetry.get("position", {}).get("latitude", 0.0),
                "longitude": telemetry.get("position", {}).get("longitude", 0.0),
            },
            "battery": {
                "percent": telemetry.get("battery", {}).get("remaining_percent", 0.0),
                "voltage": telemetry.get("battery", {}).get("voltage", 0.0),
            },
        }
    except Exception as e:
        logger.error(f"Status fetch failed: {e}")
        return {"error": str(e), "drone_id": drone_id}


@mcp.tool()
async def emergency_stop(drone_id: int = 1, ctx: Context = None) -> Dict[str, Any]:
    """Emergency land the drone immediately.

    Path: mcp-server/server.py::emergency_stop

    Args:
        drone_id: Target drone ID (default: 1)
        ctx: MCP context with lifespan dependencies

    Returns:
        Confirmation of emergency landing
    """
    try:
        # Get drone API from context
        app_ctx = ctx.request_context.lifespan_context
        drone_api = app_ctx.drone_api

        # Send immediate land command
        commands = [{"name": "land", "params": {}}]
        result = await drone_api.send_commands(commands, drone_id, queue_mode="override")

        return {
            "success": result.get("success", False),
            "action": "emergency_land",
            "drone_id": drone_id,
            "message": "Emergency landing initiated",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def health_check(ctx: Context = None) -> Dict[str, Any]:
    """Check MCP server health and connectivity.

    Path: mcp-server/server.py::health_check

    Returns:
        Health status of all components
    """
    health = {"mcp_server": "healthy", "timestamp": os.popen('date').read().strip()}

    # Check DroneSphere server
    try:
        app_ctx = ctx.request_context.lifespan_context
        drone_api = app_ctx.drone_api

        # Try to get telemetry
        telemetry = await drone_api.get_telemetry(1)
        health["dronesphere_server"] = "connected"
        health["telemetry_available"] = "error" not in telemetry
    except Exception as e:
        health["dronesphere_server"] = f"error: {str(e)}"
        health["telemetry_available"] = False

    # Check LLM
    try:
        llm_handler = app_ctx.llm_handler
        health["llm_configured"] = bool(llm_handler.api_key)
        health["llm_model"] = llm_handler.model
    except Exception as e:
        health["llm_configured"] = False
        health["llm_error"] = str(e)

    # Check environment
    health["sitl_mode"] = os.getenv("SITL_MODE", "false")
    health["debug_mode"] = os.getenv("DEBUG_MODE", "false")

    return health


@mcp.prompt()
def flight_safety_check(altitude: int = 10, ctx: Context = None) -> str:
    """Generate safety check prompt for flight operations.

    Path: mcp-server/server.py::flight_safety_check

    Args:
        altitude: Planned altitude in meters
        ctx: MCP context with lifespan dependencies

    Returns:
        Safety checklist prompt
    """
    sitl_mode = os.getenv("SITL_MODE", "false").lower() == "true"
    mode = "SIMULATION" if sitl_mode else "PRODUCTION"

    # Get config from context if available
    config = {}
    if ctx and hasattr(ctx, 'request_context'):
        app_ctx = ctx.request_context.lifespan_context
        config = app_ctx.config

    rules = get_safety_rules(config) if config else "Standard safety rules apply"

    return f"""
    Perform pre-flight safety check for {mode} mode:

    1. Check battery level (minimum 20% for production)
    2. Verify GPS lock and connection status
    3. Confirm altitude limit ({altitude}m requested, max 120m)
    4. Check weather conditions
    5. Verify clear airspace

    Current safety rules:
    {rules}

    Confirm all checks before proceeding with flight.
    """


def main():
    """Main entry point with transport selection.

    Path: mcp-server/server.py::main
    """
    # Check if running in STDIO mode for Claude Desktop
    if len(sys.argv) > 1 and sys.argv[1] == "stdio":
        logger.info("Starting in STDIO mode for Claude Desktop")
        mcp.run(transport="stdio")
    else:
        # HTTP mode for n8n and web clients
        port = int(os.getenv("MCP_PORT", 8003))
        logger.info(f"Starting HTTP server on port {port}")
        mcp.run(transport="streamable-http", host="0.0.0.0", port=port)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
