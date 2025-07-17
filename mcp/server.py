"""DroneSphere MCP Server - Pure MCP Protocol Implementation

This is a standards-compliant MCP server that can connect to:
- Claude Desktop (direct MCP connection)
- n8n (when they add MCP support)
- Any other MCP-compatible tool

Path: mcp/server.py

ARCHITECTURE:
Claude Desktop → MCP Server → DroneSphere
n8n → MCP Server → DroneSphere
Web Bridge → MCP Server → DroneSphere
"""

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional, Sequence

import httpx
import yaml
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import EmbeddedResource, Resource, TextContent, Tool

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("dronesphere-mcp")


class DroneCommand(BaseModel):
    """Structured drone command matching DroneSphere universal protocol."""

    name: str = Field(description="Command name (takeoff, land, rtl, goto, wait)")
    params: Dict[str, Any] = Field(description="Command-specific parameters")
    mode: str = Field(default="continue", description="Execution mode: continue, critical, skip")


class ConfigManager:
    """Professional configuration management with environment overrides."""

    def __init__(self, config_path: str = "config.yaml"):
        """Load configuration with environment variable overrides."""
        self.config = self._load_config(config_path)
        self._apply_env_overrides()

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(config_path, "r") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Config file {config_path} not found, using defaults")
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "llm": {
                "provider": "openrouter",
                "openrouter": {
                    "base_url": "https://openrouter.ai/api/v1",
                    "model": "anthropic/claude-3-sonnet",
                    "temperature": 0.1,
                    "max_tokens": 1000,
                    "timeout": 30,
                },
            },
            "dronesphere": {
                "server_url": "http://localhost:8002",
                "timeout": 60.0,
                "default_drone_id": 1,
            },
            "safety": {"hard_limits": {"max_altitude": 120, "max_speed": 25, "min_battery": 15}},
        }

    def _apply_env_overrides(self):
        """Apply environment variable overrides."""
        # API Keys
        if os.getenv("OPENROUTER_API_KEY"):
            self.api_key = os.getenv("OPENROUTER_API_KEY")
        elif os.getenv("OPENAI_API_KEY"):
            self.api_key = os.getenv("OPENAI_API_KEY")
        else:
            self.api_key = None

        # Model overrides
        if os.getenv("LLM_MODEL"):
            self.config["llm"]["openrouter"]["model"] = os.getenv("LLM_MODEL")
        if os.getenv("LLM_TEMPERATURE"):
            self.config["llm"]["openrouter"]["temperature"] = float(os.getenv("LLM_TEMPERATURE"))
        if os.getenv("LLM_BASE_URL"):
            self.config["llm"]["openrouter"]["base_url"] = os.getenv("LLM_BASE_URL")

        # DroneSphere overrides
        if os.getenv("DRONESPHERE_SERVER_URL"):
            self.config["dronesphere"]["server_url"] = os.getenv("DRONESPHERE_SERVER_URL")

    def get(self, path: str, default=None):
        """Get configuration value using dot notation (e.g., 'llm.openrouter.model')."""
        keys = path.split(".")
        value = self.config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value


class LLMClient:
    """LLM client supporting OpenRouter and OpenAI."""

    def __init__(self, config: ConfigManager):
        """Initialize LLM client with configuration."""
        self.config = config

        if not config.api_key:
            logger.error(
                "No API key found. Set OPENROUTER_API_KEY or OPENAI_API_KEY environment variable."
            )
            self.client = None
            return

        # Initialize OpenAI client (works with OpenRouter too)
        self.client = OpenAI(
            api_key=config.api_key,
            base_url=config.get("llm.openrouter.base_url", "https://openrouter.ai/api/v1"),
        )

        self.model = config.get("llm.openrouter.model", "anthropic/claude-3-sonnet")
        self.temperature = config.get("llm.openrouter.temperature", 0.1)
        self.max_tokens = config.get("llm.openrouter.max_tokens", 1000)

        logger.info(f"LLM Client initialized with model: {self.model}")

    async def process_command(
        self, user_input: str, drone_status: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Process natural language command using LLM."""

        if not self.client:
            raise Exception("LLM client not initialized - check API key")

        system_prompt = self._create_system_prompt(drone_status)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                extra_headers={
                    "HTTP-Referer": os.getenv("SITE_URL", ""),
                    "X-Title": os.getenv("SITE_NAME", "DroneSphere MCP"),
                },
            )

            content = response.choices[0].message.content
            return self._parse_llm_response(content)

        except Exception as e:
            logger.error(f"LLM API error: {e}")
            raise

    def _create_system_prompt(self, drone_status: Dict[str, Any]) -> str:
        """Create system prompt for LLM with drone command context."""
        return f"""You are a drone command interpreter. Convert natural language to JSON commands.

AVAILABLE COMMANDS:
1. takeoff: {{"name": "takeoff", "params": {{"altitude": 1-50}}}}
2. land: {{"name": "land", "params": {{}}}}
3. goto (GPS): {{"name": "goto", "params": {{"latitude": float, "longitude": float, "altitude": float}}}}
4. goto (NED): {{"name": "goto", "params": {{"north": float, "east": float, "down": float}}}}
5. wait: {{"name": "wait", "params": {{"duration": 0.1-300, "message": "optional"}}}}
6. rtl: {{"name": "rtl", "params": {{}}}}

CURRENT DRONE STATUS:
{json.dumps(drone_status, indent=2)}

COORDINATE SYSTEMS:
- GPS: Absolute coordinates (lat/lon/altitude_MSL)
  Example: Zurich at 15m height = lat: 47.398, lon: 8.546, alt: 503.0 (488m ground + 15m)
- NED: Relative to takeoff point (north/east/down from origin)
  Example: 50m north, 30m east, 15m up = north: 50, east: 30, down: -15

SAFETY RULES:
- Takeoff altitude: 1-50m
- GPS altitude is MSL (Mean Sea Level) - add ground elevation to desired height
- NED down: negative=up, positive=down from origin
- goto requires drone to be airborne (use takeoff first)
- Always prioritize safety

RESPONSE FORMAT:
Return ONLY a JSON array of commands, nothing else:
[{{"name": "command", "params": {{"param": value}}}}]

EXAMPLES:
User: "take off to 15 meters"
Response: [{{"name": "takeoff", "params": {{"altitude": 15}}}}]

User: "fly to coordinates 47.398, 8.546 at 15 meters above ground"
Response: [{{"name": "goto", "params": {{"latitude": 47.398, "longitude": 8.546, "altitude": 503.0}}}}]

User: "go 50 meters north and 30 meters east, then up 15 meters"
Response: [{{"name": "goto", "params": {{"north": 50, "east": 30, "down": -15}}}}]

User: "wait 5 seconds then land"
Response: [{{"name": "wait", "params": {{"duration": 5}}}}, {{"name": "land", "params": {{}}}}]
"""

    def _parse_llm_response(self, llm_response: str) -> List[Dict[str, Any]]:
        """Parse LLM response to extract command JSON."""
        try:
            # Clean response and extract JSON
            cleaned = llm_response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            # Parse JSON
            commands = json.loads(cleaned)

            # Ensure it's a list
            if isinstance(commands, dict):
                commands = [commands]

            return commands

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}")
            logger.error(f"Raw response: {llm_response}")
            return []


class DroneController:
    """Interface to DroneSphere system."""

    def __init__(self, config: ConfigManager):
        """Initialize drone controller."""
        self.config = config
        self.server_url = config.get("dronesphere.server_url")
        self.timeout = config.get("dronesphere.timeout", 60.0)

    async def execute_commands(
        self, commands: List[Dict[str, Any]], target_drone: int
    ) -> Dict[str, Any]:
        """Execute commands through DroneSphere server."""

        request_data = {
            "commands": commands,
            "target_drone": target_drone,
            "queue_mode": "override",
        }

        async with httpx.AsyncClient() as client:
            try:
                logger.info(f"Executing {len(commands)} commands on drone {target_drone}")
                response = await client.post(
                    f"{self.server_url}/fleet/commands", json=request_data, timeout=self.timeout
                )

                if response.status_code == 200:
                    result = response.json()
                    logger.info(
                        f"Commands executed successfully: {result.get('successful_commands', 0)}/{result.get('total_commands', 0)}"
                    )
                    return result
                else:
                    error_msg = f"Server error: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    return {"success": False, "error": error_msg}

            except httpx.TimeoutException:
                error_msg = f"Timeout after {self.timeout}s waiting for drone response"
                logger.error(error_msg)
                return {"success": False, "error": error_msg}
            except Exception as e:
                error_msg = f"Communication error: {str(e)}"
                logger.error(error_msg)
                return {"success": False, "error": error_msg}

    async def get_drone_status(self, target_drone: int) -> Dict[str, Any]:
        """Get drone status from DroneSphere server."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.server_url}/fleet/health", timeout=10.0)

                if response.status_code == 200:
                    fleet_health = response.json()
                    return fleet_health.get("drones", {}).get(str(target_drone), {})
                else:
                    return {"error": f"Status check failed: {response.status_code}"}

            except Exception as e:
                return {"error": f"Status check error: {str(e)}"}


class MCPDroneServer:
    """Pure MCP Server for DroneSphere integration."""

    def __init__(self, config_path: str = "config.yaml"):
        """Initialize MCP server."""
        self.config = ConfigManager(config_path)
        self.llm_client = LLMClient(self.config)
        self.drone_controller = DroneController(self.config)
        self.server = Server("dronesphere-mcp")
        self.setup_tools()

        logger.info("DroneSphere MCP Server initialized")
        logger.info(f"DroneSphere URL: {self.config.get('dronesphere.server_url')}")
        logger.info(f"LLM Model: {self.config.get('llm.openrouter.model')}")

    def setup_tools(self):
        """Register MCP tools for drone operations."""

        @self.server.call_tool()
        async def execute_drone_command(arguments: dict) -> Sequence[TextContent]:
            """Execute natural language drone commands.

            Convert natural language to structured drone commands and execute them.

            Args:
                user_request (str): Natural language command (e.g., "take off to 15 meters")
                target_drone (int, optional): Drone ID (default: 1)
                safety_mode (str, optional): Safety mode (default: "standard")

            Returns:
                Execution result with success status and details
            """
            try:
                user_request = arguments.get("user_request", "")
                target_drone = arguments.get(
                    "target_drone", self.config.get("dronesphere.default_drone_id", 1)
                )

                if not user_request:
                    return [TextContent(type="text", text="❌ Error: user_request is required")]

                # Get current drone status for context
                drone_status = await self.drone_controller.get_drone_status(target_drone)

                # Process natural language using LLM
                commands = await self.llm_client.process_command(user_request, drone_status)

                if not commands:
                    return [
                        TextContent(
                            type="text",
                            text="❌ Could not understand the command. Please try rephrasing or ask for help.",
                        )
                    ]

                # Execute commands through DroneSphere
                result = await self.drone_controller.execute_commands(commands, target_drone)

                # Format response
                response_text = self._format_execution_result(result, user_request, commands)

                return [TextContent(type="text", text=response_text)]

            except Exception as e:
                logger.error(f"Command execution error: {e}")
                return [TextContent(type="text", text=f"❌ Error executing drone command: {str(e)}")]

        @self.server.call_tool()
        async def get_drone_status(arguments: dict) -> Sequence[TextContent]:
            """Get current drone telemetry and status information.

            Args:
                target_drone (int, optional): Drone ID (default: 1)

            Returns:
                Current drone status including health, telemetry, and system info
            """
            try:
                target_drone = arguments.get(
                    "target_drone", self.config.get("dronesphere.default_drone_id", 1)
                )
                status = await self.drone_controller.get_drone_status(target_drone)

                response_text = self._format_status(status, target_drone)

                return [TextContent(type="text", text=response_text)]

            except Exception as e:
                logger.error(f"Status check error: {e}")
                return [TextContent(type="text", text=f"❌ Error getting drone status: {str(e)}")]

        @self.server.call_tool()
        async def list_available_commands(arguments: dict) -> Sequence[TextContent]:
            """List all available drone commands with descriptions and examples.

            Returns:
                Comprehensive list of available commands with usage examples
            """
            try:
                commands_help = """🚁 **Available Drone Commands**

**Basic Commands:**
• **takeoff** - Launch drone to specified altitude
  Example: "take off to 15 meters"

• **land** - Land drone at current location
  Example: "land the drone"

• **rtl** - Return to launch point automatically
  Example: "return home" or "return to launch"

**Navigation Commands:**
• **goto (GPS)** - Navigate to GPS coordinates
  Example: "fly to coordinates 47.398, 8.546"
  Note: GPS altitude is MSL (sea level), add ground elevation

• **goto (NED)** - Navigate relative to takeoff point
  Example: "go 50 meters north and 30 meters east"
  Note: Negative down = up (e.g., down: -15 = 15m above origin)

**Utility Commands:**
• **wait** - Pause for specified duration
  Example: "wait 5 seconds" or "wait 3 seconds then land"

**Coordinate Systems:**
• **GPS**: Absolute position (latitude, longitude, altitude MSL)
• **NED**: Relative position (north, east, down from takeoff point)

**Safety Notes:**
• Takeoff altitude: 1-50 meters
• goto requires drone to be airborne (takeoff first)
• Maximum altitude: 120 meters (legal limit)
• Always maintain visual line of sight

**Example Sequences:**
• "Take off to 15 meters, wait 3 seconds, then land"
• "Launch drone to 20m, fly to coordinates 47.398, 8.546, then return home"
• "Take off to 10m, go 50m north, wait 5 seconds, then land"
"""

                return [TextContent(type="text", text=commands_help)]

            except Exception as e:
                logger.error(f"Help generation error: {e}")
                return [TextContent(type="text", text="❌ Error generating help information")]

    def _format_execution_result(
        self, result: Dict[str, Any], user_request: str, commands: List[Dict]
    ) -> str:
        """Format execution result for user-friendly display."""
        if result.get("success", False):
            results = result.get("results", [])
            successful = sum(1 for r in results if r.get("success", False))
            total = len(results)

            total_duration = sum(r.get("duration", 0) for r in results if r.get("duration"))

            response = f"✅ **Command Executed Successfully**\n\n"
            response += f"**Request**: {user_request}\n"
            response += f"**Commands**: {successful}/{total} successful\n"
            response += f"**Duration**: {total_duration:.1f} seconds\n\n"

            # Add command details
            response += "**Details**:\n"
            for i, (cmd, cmd_result) in enumerate(zip(commands, results), 1):
                status = "✅" if cmd_result.get("success") else "❌"
                cmd_name = cmd.get("name", "unknown")
                message = cmd_result.get("message", "No details")
                duration = cmd_result.get("duration", 0)
                response += f"{i}. {status} **{cmd_name}**: {message} ({duration:.1f}s)\n"

            return response
        else:
            error = result.get("error", "Unknown error")
            return f"❌ **Command Failed**\n\n**Request**: {user_request}\n**Error**: {error}"

    def _format_status(self, status: Dict[str, Any], target_drone: int) -> str:
        """Format drone status for user-friendly display."""
        if "error" in status:
            return f"❌ **Drone {target_drone} Status Error**: {status['error']}"

        drone_status = status.get("status", "unknown")

        response = f"📊 **Drone {target_drone} Status Report**\n\n"
        response += f"**Overall Status**: {drone_status}\n"

        # Add detailed status if available
        if "backend_connected" in status:
            backend = "✅ Connected" if status["backend_connected"] else "❌ Disconnected"
            response += f"**Backend**: {backend}\n"

        if "executor_ready" in status:
            executor = "✅ Ready" if status["executor_ready"] else "❌ Not Ready"
            response += f"**Executor**: {executor}\n"

        if "uptime" in status:
            response += f"**Uptime**: {status['uptime']} seconds\n"

        return response

    async def run(self):
        """Run the MCP server using stdio (standard MCP protocol)."""
        logger.info("Starting DroneSphere MCP Server on stdio...")
        logger.info("Ready for Claude Desktop, n8n, and other MCP clients!")

        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream, write_stream, self.server.create_initialization_options()
            )


async def main():
    """Main entry point for MCP server."""
    server = MCPDroneServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
