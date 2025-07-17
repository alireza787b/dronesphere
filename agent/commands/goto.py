"""goto command implementation with GPS and NED coordinate support.

Path: agent/commands/goto.py

COORDINATE SYSTEMS:
- GPS (lat/lon/alt): Altitude is ABSOLUTE MSL (Mean Sea Level) in meters
- NED (north/east/down): Coordinates are RELATIVE to PX4 origin ground level

USAGE:
- GPS: {"latitude": 47.398, "longitude": 8.546, "altitude": 502.0}  # 502m MSL
- NED: {"north": 50, "east": 30, "down": -15}  # 15m above origin ground level

ROBUSTNESS: Only operates when drone is armed and airborne.
"""
import asyncio
import math
import time
from typing import Any, Dict, Optional, Tuple

from shared.models import CommandResult

from .base import BaseCommand

try:
    import pymap3d as pm
except ImportError:
    pm = None
    print("⚠️  pymap3d not available - NED coordinate conversion disabled")


class GotoCommand(BaseCommand):
    """Navigate to specified GPS or NED coordinates.

    Coordinate Systems:
    1. GPS: {"latitude": float, "longitude": float, "altitude": float}
       - latitude/longitude: Decimal degrees
       - altitude: ABSOLUTE MSL altitude in meters

    2. NED: {"north": float, "east": float, "down": float}
       - Coordinates RELATIVE to PX4 origin ground level
       - north/east: Horizontal displacement in meters
       - down: Vertical displacement (negative = up from origin)

    Optional Parameters:
        - speed: Flight speed in m/s (default: 5.0, max: 20.0)
        - acceptance_radius: Arrival tolerance in meters (default: 2.0, max: 50.0)

    Robustness: Requires drone to be armed and airborne.
    """

    def validate_params(self) -> None:
        """Validate command parameters for GPS or NED coordinates."""
        params = self.params

        # Check coordinate system
        has_gps = all(key in params for key in ["latitude", "longitude", "altitude"])
        has_ned = all(key in params for key in ["north", "east", "down"])

        if not has_gps and not has_ned:
            raise ValueError(
                "goto requires either GPS coordinates (latitude, longitude, altitude) "
                "or NED coordinates (north, east, down)"
            )

        if has_gps and has_ned:
            raise ValueError("goto cannot accept both GPS and NED coordinates simultaneously")

        if has_gps:
            self._validate_gps_params()
        elif has_ned:
            self._validate_ned_params()

        # Validate optional parameters
        if "speed" in params:
            speed = params["speed"]
            if not isinstance(speed, (int, float)) or speed <= 0 or speed > 20:
                raise ValueError("speed must be a positive number ≤ 20 m/s")

        if "acceptance_radius" in params:
            radius = params["acceptance_radius"]
            if not isinstance(radius, (int, float)) or radius <= 0 or radius > 50:
                raise ValueError("acceptance_radius must be positive and ≤ 50 meters")

    def _validate_gps_params(self) -> None:
        """Validate GPS coordinate parameters."""
        lat = self.params["latitude"]
        lon = self.params["longitude"]
        alt = self.params["altitude"]

        if not isinstance(lat, (int, float)) or not (-90 <= lat <= 90):
            raise ValueError("latitude must be a number between -90 and 90 degrees")

        if not isinstance(lon, (int, float)) or not (-180 <= lon <= 180):
            raise ValueError("longitude must be a number between -180 and 180 degrees")

        if not isinstance(alt, (int, float)) or alt < -500 or alt > 10000:
            raise ValueError("altitude must be between -500 and 10000 meters MSL")

    def _validate_ned_params(self) -> None:
        """Validate NED coordinate parameters."""
        if pm is None:
            raise ValueError("NED coordinates require pymap3d library (uv pip install pymap3d)")

        north = self.params["north"]
        east = self.params["east"]
        down = self.params["down"]

        if not isinstance(north, (int, float)) or abs(north) > 10000:
            raise ValueError("north must be a number with absolute value ≤ 10000 meters")

        if not isinstance(east, (int, float)) or abs(east) > 10000:
            raise ValueError("east must be a number with absolute value ≤ 10000 meters")

        if not isinstance(down, (int, float)) or down < -1000 or down > 100:
            raise ValueError("down must be between -1000 and 100 meters (negative = up)")

    async def _check_flight_state(self, backend) -> None:
        """Check if drone is in appropriate state for goto command.

        Raises:
            RuntimeError: If drone is not armed or not airborne
        """
        drone = backend.drone

        # Check if armed
        async for is_armed in drone.telemetry.armed():
            if not is_armed:
                raise RuntimeError("goto command requires drone to be armed. Use takeoff first.")
            break

        # Check if airborne (relative altitude > 0.5m)
        async for position in drone.telemetry.position():
            if position.relative_altitude_m < 0.5:
                raise RuntimeError("goto command requires drone to be airborne. Use takeoff first.")
            break

    async def _get_px4_origin_dynamic(self, backend) -> Tuple[float, float, float]:
        """Get PX4 origin GPS coordinates dynamically from telemetry.

        Returns:
            tuple: (latitude, longitude, altitude) of PX4 origin
        """
        try:
            origin = await backend.drone.telemetry.get_gps_global_origin()
            return (origin.latitude_deg, origin.longitude_deg, origin.altitude_m)
        except Exception as e:
            print(f"⚠️  Could not get GPS origin from PX4: {e}")
            print("🔧 Using SITL default origin (Zurich)")
            return (47.3977508, 8.5456074, 488.0)

    async def _convert_ned_to_gps(
        self, backend, north: float, east: float, down: float
    ) -> Tuple[float, float, float]:
        """Convert NED coordinates to GPS using dynamic PX4 origin.

        NED coordinates are RELATIVE to origin ground level.

        Args:
            north: North displacement in meters from origin
            east: East displacement in meters from origin
            down: Down displacement in meters (negative = up from origin ground level)

        Returns:
            tuple: (latitude, longitude, altitude_msl) in GPS coordinates
        """
        if pm is None:
            raise RuntimeError("pymap3d library required for NED conversion")

        # Get dynamic PX4 origin coordinates
        origin_lat, origin_lon, origin_alt_msl = await self._get_px4_origin_dynamic(backend)

        print(f"📍 Using PX4 origin: {origin_lat:.6f}, {origin_lon:.6f}, {origin_alt_msl:.1f}m MSL")

        # Convert NED to GPS using pymap3d
        # Note: pymap3d converts relative to the origin altitude
        target_lat, target_lon, target_alt_msl = pm.ned2geodetic(
            north, east, down, origin_lat, origin_lon, origin_alt_msl
        )

        return (target_lat, target_lon, target_alt_msl)

    async def execute(self, backend) -> CommandResult:
        """Execute goto command using MAVSDK backend."""
        start_time = time.time()

        try:
            if not backend.connected:
                return CommandResult(
                    success=False,
                    message="Backend not connected to drone",
                    error="backend_disconnected",
                )

            # Check flight state - must be armed and airborne
            await self._check_flight_state(backend)

            drone = backend.drone

            # Get target coordinates based on coordinate system
            if "latitude" in self.params:
                # GPS coordinates - altitude is ABSOLUTE MSL
                target_lat = self.params["latitude"]
                target_lon = self.params["longitude"]
                target_alt_msl = self.params["altitude"]  # Already MSL
                coord_type = "GPS"

                print(f"🔧 Executing goto to {coord_type} coordinates...")
                print(f"   📍 Target: {target_lat:.6f}, {target_lon:.6f}")
                print(f"   🏔️  Altitude: {target_alt_msl:.1f}m MSL (absolute)")

            else:
                # NED coordinates - relative to origin ground level
                target_lat, target_lon, target_alt_msl = await self._convert_ned_to_gps(
                    backend, self.params["north"], self.params["east"], self.params["down"]
                )
                coord_type = "NED"

                print(f"🔧 Executing goto to {coord_type} coordinates...")
                print(f"   📍 Target: {target_lat:.6f}, {target_lon:.6f}")
                print(f"   🏔️  Altitude: {target_alt_msl:.1f}m MSL (from NED conversion)")
                print(
                    f"   📊 NED: N={self.params['north']}m, E={self.params['east']}m, D={self.params['down']}m"
                )

            # Get optional parameters
            speed = self.params.get("speed", 5.0)
            acceptance_radius = self.params.get("acceptance_radius", 2.0)

            print(f"   ⚡ Speed: {speed}m/s, Acceptance: {acceptance_radius}m")

            # Execute goto using MAVSDK action.goto_location with MSL altitude
            await drone.action.goto_location(
                target_lat, target_lon, target_alt_msl, float("nan")  # Maintain current yaw
            )

            print(f"🚁 Navigate command sent, monitoring arrival...")

            # Monitor arrival with timeout
            timeout = 60.0
            check_interval = 0.5
            elapsed = 0.0

            while elapsed < timeout:
                async for position in drone.telemetry.position():
                    current_lat = position.latitude_deg
                    current_lon = position.longitude_deg
                    current_alt = position.absolute_altitude_m

                    # Calculate 3D distance to target
                    distance = self._calculate_distance(
                        current_lat,
                        current_lon,
                        current_alt,
                        target_lat,
                        target_lon,
                        target_alt_msl,
                    )

                    if distance <= acceptance_radius:
                        duration = time.time() - start_time
                        return CommandResult(
                            success=True,
                            message=f"goto to {coord_type} coordinates completed successfully (distance: {distance:.1f}m)",
                            duration=duration,
                        )

                    # Log progress every 5 seconds
                    if elapsed % 5.0 < check_interval:
                        print(f"   📊 Distance to target: {distance:.1f}m")
                    break

                await asyncio.sleep(check_interval)
                elapsed += check_interval

            # Timeout reached
            duration = time.time() - start_time
            return CommandResult(
                success=False,
                message=f"goto to {coord_type} coordinates timed out after {timeout}s",
                error="timeout",
                duration=duration,
            )

        except Exception as e:
            duration = time.time() - start_time
            return CommandResult(
                success=False, message=f"goto failed: {str(e)}", error=str(e), duration=duration
            )

    def _calculate_distance(
        self, lat1: float, lon1: float, alt1: float, lat2: float, lon2: float, alt2: float
    ) -> float:
        """Calculate 3D distance between two GPS coordinates.

        Returns:
            float: Distance in meters
        """
        # Convert to radians
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)

        # Haversine formula for horizontal distance
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.asin(math.sqrt(a))

        # Earth radius in meters
        earth_radius = 6371000
        horizontal_distance = earth_radius * c

        # Vertical distance
        vertical_distance = abs(alt2 - alt1)

        # 3D distance
        return math.sqrt(horizontal_distance**2 + vertical_distance**2)
