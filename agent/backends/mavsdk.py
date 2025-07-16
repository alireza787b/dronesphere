"""MAVSDK backend implementation for drone communication.

Path: agent/backends/mavsdk.py
"""
import asyncio
import time
from typing import Dict, Any
from mavsdk import System
from .base import DroneBackend


class MAVSDKBackend(DroneBackend):
    """MAVSDK implementation for drone communication."""
    
    def __init__(self, connection_string: str = "udp://172.17.0.1:14540"):
        """Initialize MAVSDK backend.
        
        Args:
            connection_string: Connection string for drone (docker bridge network)
        """
        self.drone = System()
        self.connection_string = connection_string
        self._connected = False
        self._connection_timeout = 15.0
        
    async def connect(self) -> None:
        """Connect to drone via MAVSDK."""
        try:
            print(f"Connecting to drone at {self.connection_string}...")
            await self.drone.connect(system_address=self.connection_string)
            
            # Wait for connection with timeout
            print("Waiting for drone connection...")
            start_time = time.time()
            
            async for state in self.drone.core.connection_state():
                if state.is_connected:
                    self._connected = True
                    print(f"✅ Connected to drone in {time.time() - start_time:.1f}s")
                    break
                    
                if time.time() - start_time > self._connection_timeout:
                    raise TimeoutError(f"Connection timeout after {self._connection_timeout}s")
                    
        except Exception as e:
            self._connected = False
            print(f"❌ Failed to connect to drone: {e}")
            raise
            
    async def disconnect(self) -> None:
        """Disconnect from drone."""
        try:
            if self._connected:
                # MAVSDK doesn't have explicit disconnect, just stop using it
                self._connected = False
                print("🔌 Disconnected from drone")
        except Exception as e:
            print(f"Warning: Disconnect error: {e}")
            
    async def get_telemetry(self) -> Dict[str, Any]:
        """Get current telemetry data from drone."""
        if not self._connected:
            raise RuntimeError("Not connected to drone")
            
        try:
            # Get latest telemetry data with timeout
            position_task = asyncio.create_task(self._get_position())
            attitude_task = asyncio.create_task(self._get_attitude()) 
            battery_task = asyncio.create_task(self._get_battery())
            flight_mode_task = asyncio.create_task(self._get_flight_mode())
            armed_task = asyncio.create_task(self._get_armed_state())
            
            # Wait for all with timeout
            position, attitude, battery, flight_mode, armed = await asyncio.wait_for(
                asyncio.gather(position_task, attitude_task, battery_task, flight_mode_task, armed_task),
                timeout=2.0
            )
            
            return {
                "timestamp": time.time(),
                "position": position,
                "attitude": attitude,
                "battery": battery,
                "flight_mode": flight_mode,
                "armed": armed,
                "connected": self._connected
            }
            
        except asyncio.TimeoutError:
            raise RuntimeError("Telemetry timeout - drone may be unresponsive")
        except Exception as e:
            raise RuntimeError(f"Telemetry error: {e}")
    
    @property
    def connected(self) -> bool:
        """Check if backend is connected to drone."""
        return self._connected
        
    async def _get_position(self) -> Dict[str, float]:
        """Get position data."""
        async for position in self.drone.telemetry.position():
            return {
                "latitude": position.latitude_deg,
                "longitude": position.longitude_deg,
                "altitude": position.absolute_altitude_m,
                "relative_altitude": position.relative_altitude_m
            }
            
    async def _get_attitude(self) -> Dict[str, float]:
        """Get attitude data."""
        async for attitude in self.drone.telemetry.attitude_euler():
            return {
                "roll": attitude.roll_deg,
                "pitch": attitude.pitch_deg,
                "yaw": attitude.yaw_deg
            }
            
    async def _get_battery(self) -> Dict[str, float]:
        """Get battery data."""
        async for battery in self.drone.telemetry.battery():
            return {
                "voltage": battery.voltage_v,
                "remaining_percent": battery.remaining_percent if battery.remaining_percent else 0.0
            }
            
    async def _get_flight_mode(self) -> str:
        """Get current flight mode."""
        async for flight_mode in self.drone.telemetry.flight_mode():
            return str(flight_mode)
            
    async def _get_armed_state(self) -> bool:
        """Get armed state."""
        async for armed in self.drone.telemetry.armed():
            return armed
