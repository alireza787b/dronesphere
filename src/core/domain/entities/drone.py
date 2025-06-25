"""Drone entity - the main aggregate root."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from src.core.domain.events.drone_events import (
    DroneArmedEvent,
    DroneConnectedEvent,
    DroneDisarmedEvent,
    DroneDisconnectedEvent,
    DroneLandedEvent,
    DroneMovedEvent,
    DroneStateChangedEvent,
    DroneTookOffEvent,
)
from src.core.domain.value_objects.position import Position
from src.shared.domain.entity import Entity


class DroneState(str, Enum):
    """Drone operational states."""
    
    DISCONNECTED = "DISCONNECTED"
    CONNECTED = "CONNECTED"
    ARMED = "ARMED"
    TAKING_OFF = "TAKING_OFF"
    HOVERING = "HOVERING"
    FLYING = "FLYING"
    LANDING = "LANDING"
    LANDED = "LANDED"
    EMERGENCY = "EMERGENCY"
    
    def can_transition_to(self, new_state: "DroneState") -> bool:
        """Check if transition to new state is valid."""
        valid_transitions = {
            DroneState.DISCONNECTED: [DroneState.CONNECTED],
            DroneState.CONNECTED: [DroneState.ARMED, DroneState.DISCONNECTED],
            DroneState.ARMED: [DroneState.TAKING_OFF, DroneState.CONNECTED],
            DroneState.TAKING_OFF: [DroneState.HOVERING, DroneState.EMERGENCY],
            DroneState.HOVERING: [DroneState.FLYING, DroneState.LANDING, DroneState.EMERGENCY],
            DroneState.FLYING: [DroneState.HOVERING, DroneState.LANDING, DroneState.EMERGENCY],
            DroneState.LANDING: [DroneState.LANDED, DroneState.EMERGENCY],
            DroneState.LANDED: [DroneState.CONNECTED],
            DroneState.EMERGENCY: [DroneState.LANDED, DroneState.DISCONNECTED],
        }
        return new_state in valid_transitions.get(self, [])


class Drone(Entity):
    """
    Drone aggregate root.
    
    Represents a single drone with its state, position, and capabilities.
    Enforces business rules and raises domain events.
    """
    
    def __init__(
        self,
        id: Optional[UUID] = None,
        name: str = "Drone",
        model: str = "Generic",
        firmware_version: str = "1.0.0",
    ) -> None:
        """Initialize drone in disconnected state."""
        super().__init__(id)
        self._name = name
        self._model = model
        self._firmware_version = firmware_version
        self._state = DroneState.DISCONNECTED
        self._position: Optional[Position] = None
        self._home_position: Optional[Position] = None
        self._battery_percent: float = 100.0
        self._is_armed = False
        self._last_heartbeat: Optional[datetime] = None
        self._flight_time_seconds: int = 0
        self._total_distance_meters: float = 0.0
    
    # Properties
    @property
    def name(self) -> str:
        """Get drone name."""
        return self._name
    
    @property
    def model(self) -> str:
        """Get drone model."""
        return self._model
    
    @property
    def state(self) -> DroneState:
        """Get current drone state."""
        return self._state
    
    @property
    def position(self) -> Optional[Position]:
        """Get current position."""
        return self._position
    
    @property
    def home_position(self) -> Optional[Position]:
        """Get home position."""
        return self._home_position
    
    @property
    def battery_percent(self) -> float:
        """Get battery percentage."""
        return self._battery_percent
    
    @property
    def is_armed(self) -> bool:
        """Check if drone is armed."""
        return self._is_armed
    
    @property
    def is_connected(self) -> bool:
        """Check if drone is connected."""
        return self._state != DroneState.DISCONNECTED
    
    @property
    def is_flying(self) -> bool:
        """Check if drone is in flight."""
        return self._state in [
            DroneState.TAKING_OFF,
            DroneState.HOVERING,
            DroneState.FLYING,
            DroneState.LANDING,
        ]
    
    # State transitions
    def connect(self, initial_position: Position) -> None:
        """Connect to drone."""
        if self._state != DroneState.DISCONNECTED:
            raise ValueError(f"Cannot connect: drone is {self._state}")
        
        self._state = DroneState.CONNECTED
        self._position = initial_position
        self._last_heartbeat = datetime.utcnow()
        self.mark_updated()
        
        self.add_event(
            DroneConnectedEvent(
                position=initial_position,
                aggregate_id=self.id,
            )
        )
    
    def disconnect(self) -> None:
        """Disconnect from drone."""
        if self.is_flying:
            raise ValueError("Cannot disconnect while flying")
        
        old_state = self._state
        self._state = DroneState.DISCONNECTED
        self._last_heartbeat = None
        self.mark_updated()
        
        self.add_event(
            DroneDisconnectedEvent(
                last_state=str(old_state),
                aggregate_id=self.id,
            )
        )
    
    def arm(self) -> None:
        """Arm the drone for flight."""
        if self._state != DroneState.CONNECTED:
            raise ValueError(f"Cannot arm: drone is {self._state}")
        
        if self._battery_percent < 20:
            raise ValueError("Cannot arm: battery too low")
        
        self._state = DroneState.ARMED
        self._is_armed = True
        self._home_position = self._position
        self.mark_updated()
        
        self.add_event(
            DroneArmedEvent(
                home_position=self._home_position,
                aggregate_id=self.id,
            )
        )
    
    def disarm(self) -> None:
        """Disarm the drone."""
        if not self._is_armed:
            return
        
        if self.is_flying:
            raise ValueError("Cannot disarm while flying")
        
        self._state = DroneState.CONNECTED
        self._is_armed = False
        self.mark_updated()
        
        self.add_event(DroneDisarmedEvent(aggregate_id=self.id))
    
    def takeoff(self, target_altitude: float) -> None:
        """Initiate takeoff."""
        if self._state != DroneState.ARMED:
            raise ValueError(f"Cannot takeoff: drone is {self._state}")
        
        if target_altitude < 1 or target_altitude > 120:
            raise ValueError(f"Invalid takeoff altitude: {target_altitude}")
        
        self._state = DroneState.TAKING_OFF
        self.mark_updated()
        
        self.add_event(
            DroneTookOffEvent(
                target_altitude=target_altitude,
                aggregate_id=self.id,
            )
        )
    
    def land(self) -> None:
        """Initiate landing."""
        if not self.is_flying:
            raise ValueError(f"Cannot land: drone is {self._state}")
        
        self._state = DroneState.LANDING
        self.mark_updated()
        
        self.add_event(DroneLandedEvent(aggregate_id=self.id))
    
    def update_position(self, new_position: Position) -> None:
        """Update drone position."""
        if not self.is_connected:
            raise ValueError("Cannot update position: drone disconnected")
        
        old_position = self._position
        self._position = new_position
        
        # Update state based on movement
        if self._state == DroneState.TAKING_OFF and new_position.altitude > 1:
            self._state = DroneState.HOVERING
            self.add_event(
                DroneStateChangedEvent(
                    old_state=str(DroneState.TAKING_OFF),
                    new_state=str(DroneState.HOVERING),
                    aggregate_id=self.id,
                )
            )
        elif self._state == DroneState.LANDING and new_position.altitude < 0.5:
            self._state = DroneState.LANDED
            self._is_armed = False
            self.add_event(
                DroneStateChangedEvent(
                old_state=str(DroneState.LANDING),
                new_state=str(DroneState.LANDED),
                aggregate_id=self.id,
            )
            )
        
        # Calculate distance traveled
        if old_position:
            distance = old_position.distance_to(new_position)
            self._total_distance_meters += distance
        
        self._last_heartbeat = datetime.utcnow()
        self.mark_updated()
        
        self.add_event(
            DroneMovedEvent(
                aggregate_id=self.id,
                old_position=old_position,
                new_position=new_position,
            )
        )
    
    def update_battery(self, battery_percent: float) -> None:
        """Update battery level."""
        if not 0 <= battery_percent <= 100:
            raise ValueError(f"Invalid battery percent: {battery_percent}")
        
        self._battery_percent = battery_percent
        self._last_heartbeat = datetime.utcnow()
        self.mark_updated()
        
        # Check for low battery
        if battery_percent < 15 and self.is_flying:
            self.emergency_land()
    
    def emergency_land(self) -> None:
        """Initiate emergency landing."""
        if not self.is_flying:
            return
        
        old_state = self._state
        self._state = DroneState.EMERGENCY
        self.mark_updated()
        
        self.add_event(
            DroneStateChangedEvent(
                old_state=str(old_state),
                new_state=str(DroneState.EMERGENCY),
                aggregate_id=self.id,
            )
        )
    
    def update_heartbeat(self) -> None:
        """Update last heartbeat timestamp."""
        self._last_heartbeat = datetime.utcnow()
    
    def is_connection_lost(self, timeout_seconds: int = 5) -> bool:
        """Check if connection is lost based on heartbeat."""
        if not self._last_heartbeat:
            return True
        
        time_since_heartbeat = (datetime.utcnow() - self._last_heartbeat).total_seconds()
        return time_since_heartbeat > timeout_seconds
