"""Position value object for drone location."""

from dataclasses import dataclass
from typing import Optional

from src.shared.domain.value_object import ValueObject


@dataclass(frozen=True)
class Position(ValueObject):
    """
    Represents a geographical position in 3D space.
    
    This is a value object - immutable and compared by value.
    Coordinates use WGS84 (GPS standard).
    """
    
    latitude: float  # Degrees (-90 to 90)
    longitude: float  # Degrees (-180 to 180)
    altitude: float  # Meters above sea level
    altitude_relative: Optional[float] = None  # Meters above takeoff point
    
    def __post_init__(self) -> None:
        """Validate position values."""
        if not -90 <= self.latitude <= 90:
            raise ValueError(f"Latitude must be between -90 and 90, got {self.latitude}")
        
        if not -180 <= self.longitude <= 180:
            raise ValueError(f"Longitude must be between -180 and 180, got {self.longitude}")
        
        if self.altitude < -1000:  # Dead Sea is ~430m below sea level
            raise ValueError(f"Altitude seems unrealistic: {self.altitude}")
    
    @property
    def coordinates_tuple(self) -> tuple[float, float, float]:
        """Get position as tuple (lat, lon, alt)."""
        return (self.latitude, self.longitude, self.altitude)
    
    def distance_to(self, other: "Position") -> float:
        """
        Calculate approximate distance to another position in meters.
        Uses simplified calculation suitable for small distances.
        """
        import math
        
        # Earth radius in meters
        R = 6371000
        
        # Convert to radians
        lat1 = math.radians(self.latitude)
        lat2 = math.radians(other.latitude)
        dlat = math.radians(other.latitude - self.latitude)
        dlon = math.radians(other.longitude - self.longitude)
        
        # Haversine formula
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        # Horizontal distance
        horizontal = R * c
        
        # Include altitude difference
        vertical = abs(other.altitude - self.altitude)
        
        return math.sqrt(horizontal ** 2 + vertical ** 2)
    
    def with_altitude(self, new_altitude: float) -> "Position":
        """Create new position with different altitude."""
        return Position(
            latitude=self.latitude,
            longitude=self.longitude,
            altitude=new_altitude,
            altitude_relative=self.altitude_relative,
        )
    
    def __str__(self) -> str:
        """Human-readable string representation."""
        return (
            f"Position(lat={self.latitude:.6f}, "
            f"lon={self.longitude:.6f}, "
            f"alt={self.altitude:.1f}m)"
        )
