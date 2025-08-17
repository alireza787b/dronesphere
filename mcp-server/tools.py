"""MCP Tools for DroneSphere - Organized by functional groups.

Path: mcp-server/tools.py

Groups:
1. Command Execution Tools
2. Status & Telemetry Tools
3. Coordinate Transformation Tools
"""

import asyncio
import logging
import math
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pymap3d as pm
from mcp.server.fastmcp import Context

logger = logging.getLogger(__name__)


def register_all_tools(mcp, app_context_getter):
    """Register all tool groups with the MCP server.

    Args:
        mcp: FastMCP server instance
        app_context_getter: Function to get AppContext from Context
    """
    # Register each tool group
    _register_command_tools(mcp, app_context_getter)
    _register_status_tools(mcp, app_context_getter)
    _register_coordinate_tools(mcp, app_context_getter)

    logger.info("All tools registered successfully")


# ============================================================================
# COMMAND EXECUTION TOOLS
# ============================================================================


def _register_command_tools(mcp, get_app_context):
    """Register command execution tools."""

    @mcp.tool()
    async def execute_drone_command(
        command: str, drone_id: int = 1, ctx: Context = None
    ) -> Dict[str, Any]:
        """Execute natural language drone command.

        Commands execute asynchronously in background.
        Returns immediately with acknowledgment.

        Examples:
            - 'takeoff to 10 meters'
            - 'go north 5m then wait 3 seconds then land'
            - 'fly forward 10 meters' (will use coordinate transformation)
            - 'بلند شو به ۱۵ متر' (Persian)

        Args:
            command: Natural language command in any language
            drone_id: Target drone ID (default: 1)
            ctx: MCP context

        Returns:
            Immediate acknowledgment with command ID for tracking
        """
        try:
            app_ctx = get_app_context(ctx)

            # Get telemetry for context
            telemetry = await app_ctx.drone_api.get_telemetry(drone_id, use_cache=True)

            # Parse command with LLM
            safety_rules = _get_safety_rules(app_ctx.config)
            commands = await app_ctx.llm_handler.parse_command(command, telemetry, safety_rules)

            if not commands:
                return {
                    "success": False,
                    "error": "Could not understand command",
                    "suggestion": "Try: 'takeoff to 10m' or 'fly forward 5 meters'",
                }

            # Send commands (non-blocking)
            result = await app_ctx.drone_api.send_commands(commands, drone_id)

            # Track command
            if result.get("success") and "command_id" in result:
                app_ctx.active_commands[result["command_id"]] = command

            return {
                "success": True,
                "status": "✅ Commands executing",
                "message": f"Drone executing: {command}",
                "details": f"{len(commands)} commands queued",
                "command_id": result.get("command_id"),
                "note": "Continue chatting while drone operates",
            }

        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": "Request timeout",
                "suggestion": "Try simpler commands",
            }
        except Exception as e:
            logger.error(f"Command failed: {e}")
            return {"success": False, "error": str(e)}


# ============================================================================
# STATUS & TELEMETRY TOOLS
# ============================================================================


def _register_status_tools(mcp, get_app_context):
    """Register status and telemetry tools."""

    @mcp.tool()
    async def get_drone_status(drone_id: int = 1, ctx: Context = None) -> Dict[str, Any]:
        """Get comprehensive drone telemetry and status.

        Includes position, attitude, battery, GPS info, and PX4 origin.

        Args:
            drone_id: Target drone ID
            ctx: MCP context

        Returns:
            Complete drone telemetry including:
            - Position (lat/lon/alt)
            - Attitude (roll/pitch/yaw)
            - Battery status
            - GPS info (satellites, fix type)
            - PX4 origin for coordinate transformations
        """
        try:
            app_ctx = get_app_context(ctx)

            # Get telemetry
            telemetry = await app_ctx.drone_api.get_telemetry(drone_id, use_cache=True)

            position = telemetry.get("position", {})
            attitude = telemetry.get("attitude", {})
            battery = telemetry.get("battery", {})
            gps_info = telemetry.get("gps_info", {})
            px4_origin = telemetry.get("px4_origin", {})

            return {
                "success": True,
                "drone_id": drone_id,
                "position": {
                    "latitude": position.get("latitude", 0),
                    "longitude": position.get("longitude", 0),
                    "altitude_msl": position.get("altitude", 0),
                    "altitude_relative": position.get("relative_altitude", 0),
                },
                "attitude": {
                    "roll_deg": attitude.get("roll", 0),
                    "pitch_deg": attitude.get("pitch", 0),
                    "yaw_deg": attitude.get("yaw", 0),
                },
                "battery": {
                    "percentage": battery.get("remaining_percent", 0),
                    "voltage": battery.get("voltage", 0),
                    "current": battery.get("current", 0),
                },
                "gps_info": {
                    "satellites": gps_info.get("num_satellites", 0),
                    "fix_type": gps_info.get("fix_type", "NO_FIX"),
                    "hdop": gps_info.get("hdop", 99.9),
                    "vdop": gps_info.get("vdop", 99.9),
                },
                "px4_origin": px4_origin,
                "flight_mode": telemetry.get("flight_mode", "UNKNOWN"),
                "armed": telemetry.get("armed", False),
                "connected": telemetry.get("connected", False),
                "summary": (
                    f"Alt: {position.get('relative_altitude', 0):.1f}m | "
                    f"Battery: {battery.get('remaining_percent', 0):.0f}% | "
                    f"GPS: {gps_info.get('num_satellites', 0)} sats"
                ),
            }

        except Exception as e:
            logger.error(f"Status failed: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def check_command_status(
        command_id: Optional[str] = None, ctx: Context = None
    ) -> Dict[str, Any]:
        """Check status of executing commands.

        Args:
            command_id: Specific command ID or None for all active
            ctx: MCP context

        Returns:
            Command execution status
        """
        try:
            app_ctx = get_app_context(ctx)

            if command_id:
                # Check specific command
                status = await app_ctx.drone_api.get_command_status(command_id)

                if "error" in status:
                    return {"success": False, "error": status["error"]}

                return {
                    "success": True,
                    "command_id": command_id,
                    "status": status.get("status", "unknown"),
                    "original": app_ctx.active_commands.get(command_id, "Unknown"),
                    "completed": status.get("completed", False),
                    "details": status,
                }
            else:
                # Show all active
                active = []
                for cmd_id, desc in app_ctx.active_commands.items():
                    status = await app_ctx.drone_api.get_command_status(cmd_id)
                    active.append(
                        {
                            "id": cmd_id,
                            "command": desc,
                            "status": status.get("status", "unknown"),
                            "completed": status.get("completed", False),
                        }
                    )

                return {"success": True, "active_commands": active, "total": len(active)}

        except Exception as e:
            logger.error(f"Status check failed: {e}")
            return {"success": False, "error": str(e)}


# ============================================================================
# COORDINATE TRANSFORMATION TOOLS
# ============================================================================


def _register_coordinate_tools(mcp, get_app_context):
    """Register coordinate transformation tools for drone navigation."""

    @mcp.tool()
    async def transform_body_to_ned(
        forward_m: float, right_m: float, down_m: float, drone_id: int = 1, ctx: Context = None
    ) -> Dict[str, Any]:
        """Transform body frame coordinates to NED frame.

        Body frame: X=forward, Y=right, Z=down (drone's perspective)
        NED frame: X=north, Y=east, Z=down (world coordinates)

        Useful for commands like 'fly forward 10m' or 'move right 5m'.

        Args:
            forward_m: Distance forward in meters (negative for backward)
            right_m: Distance right in meters (negative for left)
            down_m: Distance down in meters (negative for up)
            drone_id: Drone ID for getting current yaw
            ctx: MCP context

        Returns:
            NED coordinates relative to current position
        """
        try:
            app_ctx = get_app_context(ctx)

            # Get current yaw from telemetry
            telemetry = await app_ctx.drone_api.get_telemetry(drone_id, use_cache=True)
            yaw_deg = telemetry.get("attitude", {}).get("yaw", 0)
            yaw_rad = math.radians(yaw_deg)

            # Rotation matrix from body to NED
            cos_yaw = math.cos(yaw_rad)
            sin_yaw = math.sin(yaw_rad)

            # Transform body to NED
            north = forward_m * cos_yaw - right_m * sin_yaw
            east = forward_m * sin_yaw + right_m * cos_yaw
            down = down_m  # Down is same in both frames

            return {
                "success": True,
                "input_body": {"forward_m": forward_m, "right_m": right_m, "down_m": down_m},
                "output_ned": {
                    "north_m": round(north, 3),
                    "east_m": round(east, 3),
                    "down_m": round(down, 3),
                },
                "current_yaw_deg": round(yaw_deg, 1),
                "description": f"Body({forward_m:.1f}m forward, {right_m:.1f}m right) → NED({north:.1f}m N, {east:.1f}m E)",
            }

        except Exception as e:
            logger.error(f"Body to NED transform failed: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def transform_ned_to_body(
        north_m: float, east_m: float, down_m: float, drone_id: int = 1, ctx: Context = None
    ) -> Dict[str, Any]:
        """Transform NED frame coordinates to body frame.

        Inverse of body_to_ned transformation.

        Args:
            north_m: North distance in meters
            east_m: East distance in meters
            down_m: Down distance in meters
            drone_id: Drone ID for getting current yaw
            ctx: MCP context

        Returns:
            Body frame coordinates (forward, right, down)
        """
        try:
            app_ctx = get_app_context(ctx)

            # Get current yaw
            telemetry = await app_ctx.drone_api.get_telemetry(drone_id, use_cache=True)
            yaw_deg = telemetry.get("attitude", {}).get("yaw", 0)
            yaw_rad = math.radians(yaw_deg)

            # Rotation matrix from NED to body (inverse)
            cos_yaw = math.cos(yaw_rad)
            sin_yaw = math.sin(yaw_rad)

            # Transform NED to body
            forward = north_m * cos_yaw + east_m * sin_yaw
            right = -north_m * sin_yaw + east_m * cos_yaw
            down = down_m

            return {
                "success": True,
                "input_ned": {"north_m": north_m, "east_m": east_m, "down_m": down_m},
                "output_body": {
                    "forward_m": round(forward, 3),
                    "right_m": round(right, 3),
                    "down_m": round(down, 3),
                },
                "current_yaw_deg": round(yaw_deg, 1),
                "description": f"NED({north_m:.1f}m N, {east_m:.1f}m E) → Body({forward:.1f}m forward, {right:.1f}m right)",
            }

        except Exception as e:
            logger.error(f"NED to body transform failed: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def transform_ned_to_global(
        north_m: float, east_m: float, down_m: float, drone_id: int = 1, ctx: Context = None
    ) -> Dict[str, Any]:
        """Transform NED coordinates to global GPS coordinates.

        Uses PX4 origin (first GPS fix) as reference.

        Args:
            north_m: North offset from origin in meters
            east_m: East offset from origin in meters
            down_m: Down offset from origin in meters (negative for up)
            drone_id: Drone ID for getting PX4 origin
            ctx: MCP context

        Returns:
            Global GPS coordinates (latitude, longitude, altitude MSL)
        """
        try:
            app_ctx = get_app_context(ctx)

            # Get PX4 origin from telemetry
            telemetry = await app_ctx.drone_api.get_telemetry(drone_id, use_cache=True)
            origin = telemetry.get("px4_origin", {})

            if not origin:
                return {"success": False, "error": "PX4 origin not available. Ensure GPS has fix."}

            origin_lat = origin.get("latitude", 47.3977505)
            origin_lon = origin.get("longitude", 8.5456072)
            origin_alt = origin.get("altitude", 488.0)

            # Convert NED to GPS using pymap3d (WGS84 is default ellipsoid)
            lat, lon, alt = pm.ned2geodetic(
                north_m, east_m, down_m, origin_lat, origin_lon, origin_alt
            )

            return {
                "success": True,
                "input_ned": {"north_m": north_m, "east_m": east_m, "down_m": down_m},
                "output_global": {
                    "latitude": round(lat, 7),
                    "longitude": round(lon, 7),
                    "altitude_msl": round(alt, 2),
                },
                "px4_origin": {
                    "latitude": round(origin_lat, 7),
                    "longitude": round(origin_lon, 7),
                    "altitude_msl": round(origin_alt, 2),
                },
                "description": f"NED({north_m:.1f}m N, {east_m:.1f}m E) → GPS({lat:.6f}°, {lon:.6f}°, {alt:.1f}m)",
            }

        except Exception as e:
            logger.error(f"NED to global transform failed: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def transform_global_to_ned(
        latitude: float,
        longitude: float,
        altitude_msl: float,
        drone_id: int = 1,
        ctx: Context = None,
    ) -> Dict[str, Any]:
        """Transform global GPS coordinates to NED frame.

        Uses PX4 origin as reference point.

        Args:
            latitude: Target latitude in decimal degrees
            longitude: Target longitude in decimal degrees
            altitude_msl: Target altitude MSL in meters
            drone_id: Drone ID for getting PX4 origin
            ctx: MCP context

        Returns:
            NED coordinates relative to PX4 origin
        """
        try:
            app_ctx = get_app_context(ctx)

            # Get PX4 origin
            telemetry = await app_ctx.drone_api.get_telemetry(drone_id, use_cache=True)
            origin = telemetry.get("px4_origin", {})

            if not origin:
                return {"success": False, "error": "PX4 origin not available. Ensure GPS has fix."}

            origin_lat = origin.get("latitude", 47.3977505)
            origin_lon = origin.get("longitude", 8.5456072)
            origin_alt = origin.get("altitude", 488.0)

            # Convert GPS to NED using pymap3d (WGS84 is default ellipsoid)
            north, east, down = pm.geodetic2ned(
                latitude, longitude, altitude_msl, origin_lat, origin_lon, origin_alt
            )

            return {
                "success": True,
                "input_global": {
                    "latitude": latitude,
                    "longitude": longitude,
                    "altitude_msl": altitude_msl,
                },
                "output_ned": {
                    "north_m": round(north, 3),
                    "east_m": round(east, 3),
                    "down_m": round(down, 3),
                },
                "px4_origin": {
                    "latitude": round(origin_lat, 7),
                    "longitude": round(origin_lon, 7),
                    "altitude_msl": round(origin_alt, 2),
                },
                "description": f"GPS({latitude:.6f}°, {longitude:.6f}°) → NED({north:.1f}m N, {east:.1f}m E)",
            }

        except Exception as e:
            logger.error(f"Global to NED transform failed: {e}")
            return {"success": False, "error": str(e)}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def _get_safety_rules(config: Dict[str, Any]) -> str:
    """Get safety rules based on operating mode."""
    import os

    sitl_mode = os.getenv("SITL_MODE", "false").lower() == "true"

    rules = config.get("safety", {}).get("sitl_mode" if sitl_mode else "production_mode", [])

    # Add custom rules
    custom = config.get("custom_rules", [])
    if custom:
        rules.extend(custom)

    return "\n".join(f"- {rule}" for rule in rules)
