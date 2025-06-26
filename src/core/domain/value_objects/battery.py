"""Battery-related value objects for drone domain.

This module defines battery status and monitoring value objects.
"""

from dataclasses import dataclass
from typing import Optional

from src.shared.domain.value_object import ValueObject


@dataclass(frozen=True)
class BatteryStatus(ValueObject):
    """Represents drone battery status.
    
    Immutable value object for battery information.
    """
    
    level: int  # Battery percentage (0-100)
    voltage: float  # Battery voltage in volts
    current: Optional[float] = None  # Current draw in amperes
    temperature: Optional[float] = None  # Temperature in Celsius
    remaining_flight_time_s: Optional[int] = None  # Estimated remaining flight time
    
    def __post_init__(self):
        """Validate battery status."""
        if not 0 <= self.level <= 100:
            raise ValueError(f"Battery level must be 0-100, got {self.level}")
        
        if self.voltage < 0:
            raise ValueError(f"Battery voltage cannot be negative, got {self.voltage}")
        
        if self.temperature is not None and self.temperature < -50:
            raise ValueError(f"Battery temperature unrealistic: {self.temperature}°C")
    
    @property
    def is_low(self) -> bool:
        """Check if battery is low (below 20%)."""
        return self.level < 20
    
    @property
    def is_critical(self) -> bool:
        """Check if battery is critical (below 10%)."""
        return self.level < 10
    
    @property
    def is_healthy(self) -> bool:
        """Check if battery is in healthy range."""
        # Voltage check for typical LiPo (3.7V nominal per cell)
        # Assuming 3S-6S batteries (11.1V - 22.2V nominal)
        voltage_ok = 10.0 <= self.voltage <= 26.0
        temp_ok = True
        
        if self.temperature is not None:
            temp_ok = -10 <= self.temperature <= 50
        
        return voltage_ok and temp_ok and self.level > 20
    
    def __str__(self) -> str:
        """String representation."""
        status = f"Battery: {self.level}% ({self.voltage:.1f}V)"
        if self.temperature:
            status += f" @ {self.temperature:.1f}°C"
        if self.is_critical:
            status += " [CRITICAL]"
        elif self.is_low:
            status += " [LOW]"
        return status


@dataclass(frozen=True)
class BatteryAlert(ValueObject):
    """Battery alert/warning value object."""
    
    severity: str  # "info", "warning", "critical"
    message: str
    battery_status: BatteryStatus
    action_required: Optional[str] = None
    
    def __post_init__(self):
        """Validate alert."""
        valid_severities = {"info", "warning", "critical"}
        if self.severity not in valid_severities:
            raise ValueError(f"Invalid severity: {self.severity}")