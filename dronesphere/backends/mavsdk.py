"""MAVSDK backend implementation with correct NED position telemetry.

KEY FIX: MAVSDK Python does NOT have telemetry.position_ned() method!
Instead, we use telemetry.position_velocity_ned() which returns Odometry 
with position.north_m, position.east_m, position.down_m.

This is the ONLY working method to get local NED coordinates in MAVSDK Python.
"""

import asyncio
from typing import Optional

from mavsdk import System
from mavsdk.offboard import PositionNedYaw

from ..core.models import (
    Attitude, Battery, DroneState, FlightMode, GPS, Position, 
    Telemetry, Velocity
)
from ..core.errors import BackendError, DroneConnectionError
from ..core.logging import get_logger
from ..core.utils import run_with_timeout, safe_float
from .base import AbstractBackend, TelemetryProvider

logger = get_logger(__name__)


class MavsdkBackend(AbstractBackend):
    """MAVSDK implementation with WORKING local NED position telemetry."""
    
    def __init__(self, drone_id: int, connection_string: str):
        super().__init__(drone_id, connection_string)
        self.drone = System()
        self._takeoff_altitude = 0.0
        
    async def connect(self) -> None:
        """Connect to drone via MAVSDK."""
        try:
            logger.info("connecting_to_drone", drone_id=self.drone_id, 
                       connection=self.connection_string)
            
            await self.drone.connect(system_address=self.connection_string)
            
            # Wait for connection
            logger.info("waiting_for_connection", drone_id=self.drone_id)
            async for state in self.drone.core.connection_state():
                if state.is_connected:
                    logger.info("drone_connected", drone_id=self.drone_id)
                    self._connected = True
                    break
                await asyncio.sleep(0.1)
                
            # Wait for LOCAL position estimate (critical for NED coordinates)
            logger.info("waiting_for_local_position", drone_id=self.drone_id)
            async for health in self.drone.telemetry.health():
                if getattr(health, 'is_local_position_ok', False):
                    logger.info("local_position_ok", drone_id=self.drone_id)
                    break
                await asyncio.sleep(0.1)
                
            # Also wait for global position for GPS coordinates
            logger.info("waiting_for_global_position", drone_id=self.drone_id)
            async for health in self.drone.telemetry.health():
                if getattr(health, 'is_global_position_ok', False):
                    logger.info("global_position_ok", drone_id=self.drone_id)
                    break
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.error("connection_failed", drone_id=self.drone_id, error=str(e))
            raise DroneConnectionError(f"Failed to connect to drone {self.drone_id}: {e}")
            
    async def disconnect(self) -> None:
        """Disconnect from drone."""
        try:
            self._connected = False
            logger.info("drone_disconnected", drone_id=self.drone_id)
        except Exception as e:
            logger.error("disconnect_failed", drone_id=self.drone_id, error=str(e))
            
    async def arm(self) -> None:
        """Arm the drone."""
        try:
            logger.info("arming_drone", drone_id=self.drone_id)
            await run_with_timeout(
                self.drone.action.arm(),
                timeout=10.0,
                timeout_message="Arm operation timed out"
            )
            logger.info("drone_armed", drone_id=self.drone_id)
        except Exception as e:
            logger.error("arm_failed", drone_id=self.drone_id, error=str(e))
            raise BackendError(f"Failed to arm drone {self.drone_id}: {e}")

    async def hold(self) -> None:
        """Hold the drone."""
        try:
            logger.info("hold_drone", drone_id=self.drone_id)
            await run_with_timeout(
                self.drone.action.hold(),
                timeout=10.0,
                timeout_message="Hold operation timed out"
            )
            logger.info("drone_hold", drone_id=self.drone_id)
        except Exception as e:
            logger.error("hold_failed", drone_id=self.drone_id, error=str(e))
            raise BackendError(f"Failed to hold drone {self.drone_id}: {e}")
            
    async def disarm(self) -> None:
        """Disarm the drone."""
        try:
            logger.info("disarming_drone", drone_id=self.drone_id)
            await run_with_timeout(
                self.drone.action.disarm(),
                timeout=10.0,
                timeout_message="Disarm operation timed out"
            )
            logger.info("drone_disarmed", drone_id=self.drone_id)
        except Exception as e:
            logger.error("disarm_failed", drone_id=self.drone_id, error=str(e))
            raise BackendError(f"Failed to disarm drone {self.drone_id}: {e}")
            
    async def takeoff(self, altitude: float) -> None:
        """Take off to specified altitude."""
        try:
            logger.info("taking_off", drone_id=self.drone_id, altitude=altitude)
            
            # Set takeoff altitude
            await self.drone.action.set_takeoff_altitude(altitude)
            self._takeoff_altitude = altitude
            
            # Execute takeoff
            await run_with_timeout(
                self.drone.action.takeoff(),
                timeout=30.0,
                timeout_message="Takeoff operation timed out"
            )
            
            # # Wait for takeoff completion (mavsdk doesnt need it)
            # await self._wait_for_altitude(altitude * 0.9)  # 90% of target altitude
            
            logger.info("takeoff_completed", drone_id=self.drone_id, altitude=altitude)
            
        except Exception as e:
            logger.error("takeoff_failed", drone_id=self.drone_id, error=str(e))
            raise BackendError(f"Failed to takeoff drone {self.drone_id}: {e}")
            
    async def land(self) -> None:
        """Land the drone."""
        try:
            logger.info("landing_drone", drone_id=self.drone_id)
            
            await run_with_timeout(
                self.drone.action.land(),
                timeout=60.0,
                timeout_message="Land operation timed out"
            )
            
            # Wait for landing completion
            await self._wait_for_disarmed()
            
            logger.info("landing_completed", drone_id=self.drone_id)
            
        except Exception as e:
            logger.error("land_failed", drone_id=self.drone_id, error=str(e))
            raise BackendError(f"Failed to land drone {self.drone_id}: {e}")
            
    async def return_to_launch(self) -> None:
        """Return to launch position."""
        try:
            logger.info("returning_to_launch", drone_id=self.drone_id)
            await run_with_timeout(
                self.drone.action.return_to_launch(),
                timeout=120.0,
                timeout_message="RTL operation timed out"
            )
            logger.info("rtl_completed", drone_id=self.drone_id)
        except Exception as e:
            logger.error("rtl_failed", drone_id=self.drone_id, error=str(e))
            raise BackendError(f"Failed RTL for drone {self.drone_id}: {e}")
            
    async def hold_position(self) -> None:
        """Hold current position."""
        try:
            logger.info("holding_position", drone_id=self.drone_id)
            await run_with_timeout(
                self.drone.action.hold(),
                timeout=10.0,
                timeout_message="Hold operation timed out"
            )
            logger.info("hold_activated", drone_id=self.drone_id)
        except Exception as e:
            logger.error("hold_failed", drone_id=self.drone_id, error=str(e))
            raise BackendError(f"Failed to hold position for drone {self.drone_id}: {e}")
            
    async def set_flight_mode(self, mode: FlightMode) -> None:
        """Set flight mode - limited implementation for MVP."""
        logger.warning("set_flight_mode_not_implemented", mode=mode, drone_id=self.drone_id)
        
    async def get_state(self) -> DroneState:
        """Get current drone state."""
        try:
            # Get flight mode and armed status
            flight_mode = None
            async for mode in self.drone.telemetry.flight_mode():
                flight_mode = mode
                break
                
            armed = await self.is_armed()
            
            # Map MAVSDK flight mode to our state
            if not self._connected:
                return DroneState.DISCONNECTED
            elif not armed:
                return DroneState.DISARMED
            elif flight_mode and "TAKEOFF" in str(flight_mode):
                return DroneState.TAKEOFF
            elif flight_mode and "LAND" in str(flight_mode):
                return DroneState.LANDING
            elif armed:
                return DroneState.FLYING
            else:
                return DroneState.CONNECTED
                
        except Exception as e:
            logger.error("get_state_failed", drone_id=self.drone_id, error=str(e))
            return DroneState.DISCONNECTED
            
    async def is_armed(self) -> bool:
        """Check if drone is armed."""
        try:
            async for armed in self.drone.telemetry.armed():
                return armed
        except Exception:
            return False
            
    async def get_flight_mode(self) -> FlightMode:
        """Get current flight mode."""
        try:
            async for mode in self.drone.telemetry.flight_mode():
                # Map MAVSDK flight mode to our enum
                mode_str = str(mode).lower()
                if "manual" in mode_str:
                    return FlightMode.MANUAL
                elif "hold" in mode_str or "loiter" in mode_str:
                    return FlightMode.AUTO_LOITER
                elif "rtl" in mode_str:
                    return FlightMode.AUTO_RTL
                elif "takeoff" in mode_str:
                    return FlightMode.AUTO_TAKEOFF
                elif "land" in mode_str:
                    return FlightMode.AUTO_LAND
                elif "offboard" in mode_str:
                    return FlightMode.OFFBOARD
                else:
                    return FlightMode.POSCTL
        except Exception:
            return FlightMode.POSCTL
            
    async def goto_position(self, position: Position, yaw: Optional[float] = None, max_speed: float = 2.0) -> None:
        """Go to specified position using offboard mode with velocity control."""
        try:
            logger.info("goto_position", drone_id=self.drone_id, position=position.dict(), max_speed=max_speed)
            
            if position.north is None or position.east is None or position.down is None:
                raise BackendError("NED coordinates required for goto_position")
            
            # Set initial target position
            target = PositionNedYaw(
                north_m=position.north,
                east_m=position.east, 
                down_m=position.down,
                yaw_deg=yaw or 0.0
            )
            
            # Start offboard mode with position control
            await self.drone.offboard.set_position_ned(target)
            await self.drone.offboard.start()
            
            logger.info("goto_position_started", drone_id=self.drone_id)
            
        except Exception as e:
            logger.error("goto_position_failed", drone_id=self.drone_id, error=str(e))
            raise BackendError(f"Failed goto position for drone {self.drone_id}: {e}")
    
    async def get_telemetry(self) -> Telemetry:
        """Get comprehensive telemetry using WORKING MAVSDK methods."""
        try:
            # Initialize telemetry components
            position_data = None
            attitude_data = None
            velocity_data = None
            battery_data = None
            gps_data = None
            health_data = None
            armed = False
            
            # Get GPS position from MAVSDK
            try:
                async for pos in self.drone.telemetry.position():
                    position_data = Position(
                        latitude=safe_float(pos.latitude_deg),
                        longitude=safe_float(pos.longitude_deg),
                        altitude_msl=safe_float(pos.absolute_altitude_m),
                        altitude_relative=safe_float(pos.relative_altitude_m)
                    )
                    break
            except Exception as e:
                logger.debug("gps_position_failed", error=str(e), drone_id=self.drone_id)
            
            # CRITICAL FIX: Get NED position using position_velocity_ned()
            # This is the ONLY working method in MAVSDK Python for local NED coordinates
            try:
                async for odom in self.drone.telemetry.position_velocity_ned():
                    # Extract position from odometry data
                    ned_pos = odom.position
                    ned_vel = odom.velocity
                    
                    if position_data:
                        # Add NED coordinates to existing GPS position data
                        position_data.north = safe_float(ned_pos.north_m)
                        position_data.east = safe_float(ned_pos.east_m)
                        position_data.down = safe_float(ned_pos.down_m)
                    else:
                        # Create position data with just NED coordinates
                        position_data = Position(
                            north=safe_float(ned_pos.north_m),
                            east=safe_float(ned_pos.east_m),
                            down=safe_float(ned_pos.down_m)
                        )
                    
                    # Also get velocity from the same odometry data
                    velocity_data = Velocity(
                        north=safe_float(ned_vel.north_m_s),
                        east=safe_float(ned_vel.east_m_s),
                        down=safe_float(ned_vel.down_m_s)
                    )
                    
                    logger.debug("ned_position_received", 
                               north=ned_pos.north_m, 
                               east=ned_pos.east_m, 
                               down=ned_pos.down_m, 
                               drone_id=self.drone_id)
                    break
                    
            except Exception as e:
                logger.warning("position_velocity_ned_failed", error=str(e), drone_id=self.drone_id)
                logger.warning("ned_coordinates_unavailable", 
                             note="position_velocity_ned() is the only way to get NED coordinates in MAVSDK Python", 
                             drone_id=self.drone_id)
            
            # Get attitude from MAVSDK
            try:
                async for att in self.drone.telemetry.attitude_euler():
                    attitude_data = Attitude(
                        roll=safe_float(att.roll_deg * 3.14159 / 180),
                        pitch=safe_float(att.pitch_deg * 3.14159 / 180),
                        yaw=safe_float(att.yaw_deg * 3.14159 / 180)
                    )
                    break
            except Exception as e:
                logger.debug("attitude_failed", error=str(e), drone_id=self.drone_id)
                
            # Skip velocity_ned() since we already got it from position_velocity_ned()
            # Note: velocity_data is already set above
                
            # Get battery from MAVSDK
            try:
                async for bat in self.drone.telemetry.battery():
                    battery_data = Battery(
                        voltage=safe_float(bat.voltage_v),
                        remaining_percent=safe_float(bat.remaining_percent * 100)
                    )
                    break
            except Exception as e:
                logger.debug("battery_failed", error=str(e), drone_id=self.drone_id)
                
            # Get GPS info from MAVSDK
            try:
                async for gps in self.drone.telemetry.gps_info():
                    gps_data = GPS(
                        fix_type=gps.fix_type,
                        satellites_visible=gps.num_satellites
                    )
                    break
            except Exception as e:
                logger.debug("gps_info_failed", error=str(e), drone_id=self.drone_id)
                
            # Get health from MAVSDK
            try:
                async for health in self.drone.telemetry.health():
                    health_data = health
                    break
            except Exception as e:
                logger.debug("health_failed", error=str(e), drone_id=self.drone_id)
                
            # Get armed status from MAVSDK
            try:
                async for armed_status in self.drone.telemetry.armed():
                    armed = armed_status
                    break
            except Exception as e:
                logger.debug("armed_status_failed", error=str(e), drone_id=self.drone_id)
                
            # Get current state
            state = await self.get_state()
                
            # Extract health information safely
            health_all_ok = True
            calibration_ok = True
            if health_data:
                health_all_ok = getattr(health_data, 'is_all_ok', True)
                calibration_ok = getattr(health_data, 'is_calibration_ok', True)
                
            return Telemetry(
                drone_id=self.drone_id,
                state=state,
                armed=armed,
                position=position_data,
                attitude=attitude_data,
                velocity=velocity_data,
                battery=battery_data,
                gps=gps_data,
                health_all_ok=health_all_ok,
                calibration_ok=calibration_ok,
                connection_ok=self._connected
            )
            
        except Exception as e:
            logger.error("backend_get_telemetry_failed", drone_id=self.drone_id, error=str(e))
            
            # Return minimal telemetry on error
            return Telemetry(
                drone_id=self.drone_id,
                state=DroneState.DISCONNECTED,
                armed=False,
                health_all_ok=False,
                connection_ok=False
            )

    async def _wait_for_altitude(self, target_altitude: float, timeout: float = 30.0) -> None:
        """Wait for drone to reach target altitude."""
        start_time = asyncio.get_event_loop().time()
        
        async for position in self.drone.telemetry.position():
            current_altitude = abs(position.relative_altitude_m)
            
            if current_altitude >= target_altitude:
                logger.info("altitude_reached", 
                           drone_id=self.drone_id,
                           target=target_altitude, 
                           current=current_altitude)
                break
                
            if asyncio.get_event_loop().time() - start_time > timeout:
                raise BackendError(f"Timeout waiting for altitude {target_altitude}m")
                
            await asyncio.sleep(0.5)
            
    async def _wait_for_disarmed(self, timeout: float = 60.0) -> None:
        """Wait for drone to disarm (landing complete)."""
        start_time = asyncio.get_event_loop().time()
        
        async for armed in self.drone.telemetry.armed():
            if not armed:
                logger.info("drone_disarmed", drone_id=self.drone_id)
                break
                
            if asyncio.get_event_loop().time() - start_time > timeout:
                raise BackendError("Timeout waiting for disarm")
                
            await asyncio.sleep(0.5)


class MavsdkTelemetryProvider(TelemetryProvider):
    """MAVSDK telemetry provider with working NED support."""
    
    def __init__(self, drone_id: int, connection_string: str):
        super().__init__(drone_id, connection_string)
        self.drone = System()
        
    async def connect(self) -> None:
        """Connect to drone for telemetry."""
        try:
            await self.drone.connect(system_address=self.connection_string)
            
            async for state in self.drone.core.connection_state():
                if state.is_connected:
                    self._connected = True
                    break
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.error("telemetry_connection_failed", drone_id=self.drone_id, error=str(e))
            raise DroneConnectionError(f"Failed to connect telemetry: {e}")
            
    async def disconnect(self) -> None:
        """Disconnect telemetry."""
        self._connected = False
        
    async def get_telemetry(self) -> Telemetry:
        """Get current telemetry data using working MAVSDK methods."""
        # Reuse the main backend implementation
        backend = MavsdkBackend(self.drone_id, "")
        backend.drone = self.drone
        backend._connected = self._connected
        return await backend.get_telemetry()