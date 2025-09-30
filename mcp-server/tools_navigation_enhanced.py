"""Enhanced Navigation Tool - Smart coordinate handling for natural language.

Path: mcp-server/tools_navigation_enhanced.py

This module provides a unified smart_navigate tool that intelligently handles
ALL coordinate input types, making it easy for LLMs to translate natural language
into drone commands without needing to chain multiple tools.

Design Philosophy:
- ONE tool call for ANY navigation command
- Automatic coordinate detection and transformation
- Reference frame support (current, home, origin)
- Body frame support (forward/right/up)
- LLM doesn't need to understand coordinate math
"""

import logging
import math
from typing import Any, Dict, Optional

import pymap3d as pm
from mcp.server.fastmcp import Context

logger = logging.getLogger(__name__)


async def smart_navigate(
    # ===== ABSOLUTE GPS COORDINATES =====
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    altitude_msl: Optional[float] = None,
    # ===== NED FROM PX4 ORIGIN =====
    north: Optional[float] = None,
    east: Optional[float] = None,
    down: Optional[float] = None,
    # ===== OFFSET FROM REFERENCE POINT =====
    offset_north: Optional[float] = None,
    offset_east: Optional[float] = None,
    offset_up: Optional[float] = None,  # Positive = UP (intuitive)
    reference: str = "current",  # "current", "home", "origin"
    # ===== BODY FRAME (RELATIVE TO DRONE HEADING) =====
    forward: Optional[float] = None,
    right: Optional[float] = None,
    up_body: Optional[float] = None,  # Positive = UP in body frame
    # ===== COMMON OPTIONS =====
    speed: float = 5.0,
    yaw: Optional[float] = None,
    maintain_altitude: bool = False,
    drone_id: int = 1,
    ctx: Context = None,
    app_ctx=None,  # Injected by registration
) -> Dict[str, Any]:
    """Smart navigation tool that handles ALL coordinate types automatically.

    This tool intelligently detects the coordinate type and performs all necessary
    transformations internally. The LLM only needs to understand user intent.

    COORDINATE MODES (Auto-detected by priority):

    1. ABSOLUTE GPS:
       latitude=47.398, longitude=8.546, altitude_msl=500
       → "Go to this exact GPS location"

    2. NED FROM ORIGIN:
       north=50, east=30, down=-15
       → "Go 50m north and 30m east from PX4 origin, at 15m altitude"

    3. OFFSET FROM REFERENCE:
       offset_north=10, offset_up=5, reference="current"
       → "Go 10m north and 5m up from current position"

       offset_north=20, reference="home"
       → "Go 20m north from home/origin position"

    4. BODY FRAME (RELATIVE TO DRONE HEADING):
       forward=10, right=5, up_body=3
       → "Go 10m forward, 5m right, 3m up relative to where drone is facing"

    REFERENCE FRAMES:
    - "current": Relative to drone's current position
    - "home": Relative to PX4 origin (takeoff/first GPS fix location)
    - "origin": Same as "home"

    EXAMPLES FOR LLM:

    User: "go to GPS coordinates 47.398, 8.546 at 500m altitude"
    → smart_navigate(latitude=47.398, longitude=8.546, altitude_msl=500)

    User: "fly 10 meters forward"
    → smart_navigate(forward=10, maintain_altitude=True)

    User: "go 5 meters north"
    → smart_navigate(offset_north=5, reference="current", maintain_altitude=True)

    User: "go 20 meters north from home"
    → smart_navigate(offset_north=20, reference="home")

    User: "move 10m forward and 5m right"
    → smart_navigate(forward=10, right=5, maintain_altitude=True)

    User: "go up 5 meters"
    → smart_navigate(offset_up=5, reference="current")

    Args:
        latitude: Target latitude in decimal degrees (-90 to 90)
        longitude: Target longitude in decimal degrees (-180 to 180)
        altitude_msl: Target altitude MSL in meters
        north: North offset from PX4 origin in meters
        east: East offset from PX4 origin in meters
        down: Down offset from PX4 origin in meters (negative = up)
        offset_north: North offset from reference in meters
        offset_east: East offset from reference in meters
        offset_up: Up offset from reference in meters (positive = up, intuitive)
        reference: Reference frame ("current", "home", "origin")
        forward: Forward distance in meters (body frame)
        right: Right distance in meters (body frame)
        up_body: Up distance in meters (body frame, positive = up)
        speed: Flight speed in m/s (default 5.0, max 20.0)
        yaw: Target yaw/heading in degrees (0=North, 90=East, optional)
        maintain_altitude: Keep current altitude if not specified
        drone_id: Target drone ID
        ctx: MCP context
        app_ctx: Application context (injected)

    Returns:
        Success/failure with details of command sent
    """
    try:
        # Get current telemetry for transformations
        telemetry = await app_ctx.drone_api.get_telemetry(drone_id, use_cache=True)

        position = telemetry.get("position", {})
        attitude = telemetry.get("attitude", {})
        px4_origin = telemetry.get("px4_origin", {})

        current_lat = position.get("latitude", 47.3977505)
        current_lon = position.get("longitude", 8.5456072)
        current_alt_msl = position.get("altitude", 488.0)
        current_alt_rel = position.get("relative_altitude", 0.0)
        current_yaw = attitude.get("yaw", 0.0)

        origin_lat = px4_origin.get("latitude", 47.3977505)
        origin_lon = px4_origin.get("longitude", 8.5456072)
        origin_alt = px4_origin.get("altitude", 488.0)

        # ===== COORDINATE DETECTION & TRANSFORMATION =====

        # MODE 1: Absolute GPS (highest priority)
        if latitude is not None and longitude is not None:
            target_lat = latitude
            target_lon = longitude
            target_alt = altitude_msl if altitude_msl is not None else current_alt_msl
            mode = "GPS (Absolute)"

        # MODE 2: NED from origin
        elif north is not None or east is not None or down is not None:
            n = north or 0.0
            e = east or 0.0
            d = down if down is not None else -current_alt_rel  # Maintain altitude if not specified

            # Convert NED to GPS
            target_lat, target_lon, target_alt = pm.ned2geodetic(
                n, e, d, origin_lat, origin_lon, origin_alt
            )
            mode = f"NED from Origin (N={n}, E={e}, D={d})"

        # MODE 3: Body frame (forward/right/up)
        elif forward is not None or right is not None or up_body is not None:
            fwd = forward or 0.0
            rgt = right or 0.0
            up_val = up_body or 0.0

            # Transform body to NED using current yaw
            yaw_rad = math.radians(current_yaw)
            cos_yaw = math.cos(yaw_rad)
            sin_yaw = math.sin(yaw_rad)

            # Rotation: body to NED
            ned_north = fwd * cos_yaw - rgt * sin_yaw
            ned_east = fwd * sin_yaw + rgt * cos_yaw
            ned_down = -up_val  # Body up is negative NED down

            # Get current position in NED from origin
            current_n, current_e, current_d = pm.geodetic2ned(
                current_lat, current_lon, current_alt_msl, origin_lat, origin_lon, origin_alt
            )

            # Add offset to current NED position
            target_n = current_n + ned_north
            target_e = current_e + ned_east
            target_d = current_d + ned_down

            # Convert back to GPS
            target_lat, target_lon, target_alt = pm.ned2geodetic(
                target_n, target_e, target_d, origin_lat, origin_lon, origin_alt
            )

            mode = f"Body Frame (fwd={fwd}m, right={rgt}m, up={up_val}m) from current yaw {current_yaw:.1f}°"

        # MODE 4: Offset from reference
        elif offset_north is not None or offset_east is not None or offset_up is not None:
            off_n = offset_north or 0.0
            off_e = offset_east or 0.0
            off_u = offset_up or 0.0

            # Determine reference position
            if reference == "current":
                ref_lat, ref_lon, ref_alt = current_lat, current_lon, current_alt_msl
                ref_desc = "current position"
            else:  # "home" or "origin"
                ref_lat, ref_lon, ref_alt = origin_lat, origin_lon, origin_alt
                ref_desc = "home/origin"

            # Get reference in NED
            ref_n, ref_e, ref_d = pm.geodetic2ned(
                ref_lat, ref_lon, ref_alt, origin_lat, origin_lon, origin_alt
            )

            # Apply offset (note: offset_up is positive = up, so negate for NED down)
            target_n = ref_n + off_n
            target_e = ref_e + off_e
            target_d = ref_d - off_u  # Subtract because NED down is opposite

            # Convert to GPS
            target_lat, target_lon, target_alt = pm.ned2geodetic(
                target_n, target_e, target_d, origin_lat, origin_lon, origin_alt
            )

            mode = f"Offset from {ref_desc} (N={off_n}, E={off_e}, Up={off_u})"

        # MODE 5: Maintain position (altitude change only, or error)
        else:
            if maintain_altitude:
                # Just maintain current position
                target_lat, target_lon, target_alt = current_lat, current_lon, current_alt_msl
                mode = "Maintain Position"
            else:
                return {
                    "success": False,
                    "error": "No coordinates specified",
                    "suggestion": "Specify one of: GPS (lat/lon), NED (north/east/down), offset (offset_north/east/up), or body frame (forward/right/up)",
                }

        # ===== PREPARE GOTO COMMAND =====

        # Determine yaw (heading)
        if yaw is not None:
            target_yaw = yaw
        else:
            target_yaw = float("nan")  # Maintain current yaw

        # Create command for agent
        goto_command = {
            "name": "goto",
            "params": {
                "latitude": target_lat,
                "longitude": target_lon,
                "altitude": target_alt,
                "speed": min(speed, 20.0),  # Cap at 20 m/s
            },
        }

        # Send command
        result = await app_ctx.drone_api.send_commands([goto_command], drone_id)

        return {
            "success": True,
            "mode": mode,
            "status": "✅ Navigation command sent",
            "target": {
                "latitude": round(target_lat, 7),
                "longitude": round(target_lon, 7),
                "altitude_msl": round(target_alt, 2),
                "altitude_relative": round(target_alt - origin_alt, 2),
            },
            "reference_used": {
                "current_position": f"{current_lat:.6f}, {current_lon:.6f}, {current_alt_msl:.1f}m",
                "px4_origin": f"{origin_lat:.6f}, {origin_lon:.6f}, {origin_alt:.1f}m",
                "current_yaw": f"{current_yaw:.1f}°",
            },
            "command_id": result.get("command_id"),
            "details": f"Drone will navigate using {mode}",
        }

    except Exception as e:
        logger.error(f"Smart navigate failed: {e}")
        return {"success": False, "error": str(e)}


def register_enhanced_navigation_tool(mcp, app_context_getter):
    """Register the smart_navigate tool with the MCP server.

    Args:
        mcp: FastMCP server instance
        app_context_getter: Function to extract AppContext from Context
    """

    @mcp.tool()
    async def smart_navigate_wrapper(
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        altitude_msl: Optional[float] = None,
        north: Optional[float] = None,
        east: Optional[float] = None,
        down: Optional[float] = None,
        offset_north: Optional[float] = None,
        offset_east: Optional[float] = None,
        offset_up: Optional[float] = None,
        reference: str = "current",
        forward: Optional[float] = None,
        right: Optional[float] = None,
        up_body: Optional[float] = None,
        speed: float = 5.0,
        yaw: Optional[float] = None,
        maintain_altitude: bool = False,
        drone_id: int = 1,
        ctx: Context = None,
    ) -> Dict[str, Any]:
        """Smart navigation - handles all coordinate types automatically.

        See smart_navigate() for detailed documentation.
        """
        app_ctx = app_context_getter(ctx)
        return await smart_navigate(
            latitude=latitude,
            longitude=longitude,
            altitude_msl=altitude_msl,
            north=north,
            east=east,
            down=down,
            offset_north=offset_north,
            offset_east=offset_east,
            offset_up=offset_up,
            reference=reference,
            forward=forward,
            right=right,
            up_body=up_body,
            speed=speed,
            yaw=yaw,
            maintain_altitude=maintain_altitude,
            drone_id=drone_id,
            ctx=ctx,
            app_ctx=app_ctx,
        )

    logger.info("Enhanced smart_navigate tool registered")
