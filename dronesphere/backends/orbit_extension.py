"""Orbit utility functions for MAVSDK backend.

This module provides utility functions for orbit operations without
mixing concerns with the main backend class. Clean separation of concerns.
"""

import math
from typing import Tuple

try:
    from mavsdk.action import OrbitYawBehavior
    HAS_ORBIT_SUPPORT = True
except ImportError:
    HAS_ORBIT_SUPPORT = False
    # Create mock enum for testing
    class OrbitYawBehavior:
        HOLD_FRONT_TO_CIRCLE_CENTER = "HOLD_FRONT_TO_CIRCLE_CENTER"
        HOLD_INITIAL_HEADING = "HOLD_INITIAL_HEADING"
        UNCONTROLLED = "UNCONTROLLED"
        HOLD_FRONT_TANGENT_TO_CIRCLE = "HOLD_FRONT_TANGENT_TO_CIRCLE"
        RC_CONTROLLED = "RC_CONTROLLED"

try:
    import pymap3d as pm3d
    HAS_PYMAP3D = True
except ImportError:
    HAS_PYMAP3D = False

from ..core.logging import get_logger

logger = get_logger(__name__)


def get_orbit_yaw_behavior(behavior_str: str):
    """Convert string yaw behavior to MAVSDK OrbitYawBehavior enum.
    
    Args:
        behavior_str: String representation of yaw behavior
        
    Returns:
        OrbitYawBehavior enum value
        
    Raises:
        ValueError: If behavior string is invalid
    """
    behavior_map = {
        "face_center": OrbitYawBehavior.HOLD_FRONT_TO_CIRCLE_CENTER,
        "hold_heading": OrbitYawBehavior.HOLD_INITIAL_HEADING,
        "uncontrolled": OrbitYawBehavior.UNCONTROLLED,
        "face_tangent": OrbitYawBehavior.HOLD_FRONT_TANGENT_TO_CIRCLE,
        "rc_controlled": OrbitYawBehavior.RC_CONTROLLED,
    }
    
    if behavior_str not in behavior_map:
        valid_options = ", ".join(behavior_map.keys())
        raise ValueError(f"Invalid yaw behavior '{behavior_str}'. Valid options: {valid_options}")
        
    return behavior_map[behavior_str]


def convert_ned_to_global(
    north: float, 
    east: float, 
    altitude_relative: float,
    ref_lat: float, 
    ref_lon: float, 
    ref_alt_msl: float,
    drone_id: int = 1
) -> Tuple[float, float, float]:
    """Convert NED coordinates to global GPS coordinates.
    
    Args:
        north: North coordinate in meters (NED)
        east: East coordinate in meters (NED)
        altitude_relative: Relative altitude in meters
        ref_lat: Reference latitude in degrees
        ref_lon: Reference longitude in degrees  
        ref_alt_msl: Reference altitude MSL in meters
        drone_id: Drone ID for logging
        
    Returns:
        Tuple of (latitude, longitude, altitude_msl)
    """
    if HAS_PYMAP3D:
        # Use pymap3d for accurate conversion
        lat, lon, alt_msl = pm3d.ned2geodetic(
            north, east, -altitude_relative,  # NED down is negative altitude
            ref_lat, ref_lon, ref_alt_msl
        )
        
        logger.info(
            "accurate_ned_to_global_conversion",
            drone_id=drone_id,
            method="pymap3d",
            ned_input={"north": north, "east": east, "alt_rel": altitude_relative},
            global_output={"lat": lat, "lon": lon, "alt_msl": alt_msl},
        )
        
        return lat, lon, alt_msl
    else:
        # Simple approximation (less accurate, but works without pymap3d)
        lat_deg_per_m = 1.0 / 111320.0  # approximate
        lon_deg_per_m = 1.0 / (111320.0 * math.cos(math.radians(ref_lat)))
        
        lat = ref_lat + (north * lat_deg_per_m)
        lon = ref_lon + (east * lon_deg_per_m) 
        alt_msl = ref_alt_msl + altitude_relative
        
        logger.warning(
            "approximate_coordinate_conversion",
            drone_id=drone_id,
            method="simple_approximation",
            note="Install pymap3d for accurate conversion",
            ned_input={"north": north, "east": east, "alt_rel": altitude_relative},
            global_output={"lat": lat, "lon": lon, "alt_msl": alt_msl}
        )
        
        return lat, lon, alt_msl


def validate_orbit_parameters(radius: float, velocity: float) -> None:
    """Validate orbit parameters for safety.
    
    Args:
        radius: Orbit radius in meters
        velocity: Orbit velocity in m/s
        
    Raises:
        ValueError: If parameters are invalid
    """
    if radius <= 0:
        raise ValueError("Orbit radius must be positive")
    if radius > 1000:
        raise ValueError("Orbit radius too large (max 1000m for safety)")
    if abs(velocity) < 0.1:
        raise ValueError("Orbit velocity must be at least 0.1 m/s")
    if abs(velocity) > 20:
        raise ValueError("Orbit velocity too fast (max 20 m/s for safety)")


def calculate_orbit_duration(radius: float, velocity: float, loops: float) -> float:
    """Calculate expected orbit duration for given parameters.
    
    Args:
        radius: Orbit radius in meters
        velocity: Orbit velocity in m/s
        loops: Number of complete loops
        
    Returns:
        Expected duration in seconds
    """
    circumference = 2 * math.pi * radius
    time_per_loop = circumference / abs(velocity)
    return loops * time_per_loop
