#!/usr/bin/env python3
"""Fix all domain model issues including duplicate DomainEvent."""

import os
import shutil
from pathlib import Path

def fix_domain_event():
    """Ensure only one DomainEvent exists in the correct location."""
    print("🔧 Fixing DomainEvent issue...")
    
    # The canonical location
    canonical_path = Path("src/shared/domain/event.py")
    
    # Correct DomainEvent content with proper field ordering
    domain_event_content = '''"""Base domain event."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4


@dataclass
class DomainEvent:
    """
    Base class for domain events.
    
    Events represent something that has happened in the domain.
    They are immutable and carry the information about what occurred.
    All fields have defaults to avoid field ordering issues in subclasses.
    """
    
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=datetime.utcnow)
    aggregate_id: Optional[UUID] = None
    
    @property
    def event_name(self) -> str:
        """Get the event name (class name by default)."""
        return self.__class__.__name__
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        result = {
            "event_id": str(self.event_id),
            "event_name": self.event_name,
            "occurred_at": self.occurred_at.isoformat(),
        }
        
        if self.aggregate_id:
            result["aggregate_id"] = str(self.aggregate_id)
        
        # Add any additional fields from subclasses
        for key, value in self.__dict__.items():
            if key not in ["event_id", "occurred_at", "aggregate_id"]:
                result[key] = value
                
        return result
'''
    
    # Write the canonical version
    canonical_path.parent.mkdir(parents=True, exist_ok=True)
    canonical_path.write_text(domain_event_content)
    print(f"✅ Created canonical DomainEvent at {canonical_path}")
    
    # Remove any duplicates
    for root, dirs, files in os.walk("src"):
        for file in files:
            if file == "event.py":
                filepath = Path(root) / file
                if filepath != canonical_path:
                    print(f"❌ Removing duplicate: {filepath}")
                    os.remove(filepath)


def fix_drone_events():
    """Fix drone events to properly inherit from DomainEvent."""
    print("\n🔧 Fixing drone events...")
    
    drone_events_content = '''"""Domain events related to drone operations."""

from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID

from src.core.domain.value_objects.position import Position
from src.shared.domain.event import DomainEvent


@dataclass
class DroneConnectedEvent(DomainEvent):
    """Raised when drone connects."""
    
    position: Position = field(default=None)
    
    def __post_init__(self):
        """Ensure position is required."""
        if self.position is None:
            raise ValueError("Position is required for DroneConnectedEvent")


@dataclass
class DroneDisconnectedEvent(DomainEvent):
    """Raised when drone disconnects."""
    
    last_state: str = field(default="")
    
    def __post_init__(self):
        """Ensure last_state is required."""
        if not self.last_state:
            raise ValueError("last_state is required for DroneDisconnectedEvent")


@dataclass
class DroneArmedEvent(DomainEvent):
    """Raised when drone is armed."""
    
    home_position: Position = field(default=None)
    
    def __post_init__(self):
        """Ensure home_position is required."""
        if self.home_position is None:
            raise ValueError("home_position is required for DroneArmedEvent")


@dataclass
class DroneDisarmedEvent(DomainEvent):
    """Raised when drone is disarmed."""
    
    pass


@dataclass
class DroneTookOffEvent(DomainEvent):
    """Raised when drone takes off."""
    
    target_altitude: float = field(default=0.0)
    
    def __post_init__(self):
        """Validate altitude."""
        if self.target_altitude <= 0:
            raise ValueError("target_altitude must be positive")


@dataclass
class DroneLandedEvent(DomainEvent):
    """Raised when drone lands."""
    
    pass


@dataclass
class DroneMovedEvent(DomainEvent):
    """Raised when drone position changes."""
    
    old_position: Optional[Position] = None
    new_position: Position = field(default=None)
    
    def __post_init__(self):
        """Ensure new_position is required."""
        if self.new_position is None:
            raise ValueError("new_position is required for DroneMovedEvent")


@dataclass
class DroneStateChangedEvent(DomainEvent):
    """Raised when drone state changes."""
    
    old_state: str = field(default="")
    new_state: str = field(default="")
    
    def __post_init__(self):
        """Ensure states are required."""
        if not self.old_state or not self.new_state:
            raise ValueError("Both old_state and new_state are required")


@dataclass
class DroneBatteryLowEvent(DomainEvent):
    """Raised when battery is critically low."""
    
    battery_percent: float = field(default=0.0)
    
    def __post_init__(self):
        """Validate battery percent."""
        if not 0 <= self.battery_percent <= 100:
            raise ValueError("battery_percent must be between 0 and 100")


@dataclass
class DroneEmergencyEvent(DomainEvent):
    """Raised when emergency condition occurs."""
    
    reason: str = field(default="")
    severity: str = field(default="MEDIUM")  # LOW, MEDIUM, HIGH, CRITICAL
    
    def __post_init__(self):
        """Validate emergency event."""
        if not self.reason:
            raise ValueError("reason is required for DroneEmergencyEvent")
        if self.severity not in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]:
            raise ValueError(f"Invalid severity: {self.severity}")
'''
    
    events_path = Path("src/core/domain/events/drone_events.py")
    events_path.write_text(drone_events_content)
    print(f"✅ Fixed drone events at {events_path}")


def update_drone_entity():
    """Update drone entity to use events correctly."""
    print("\n🔧 Updating drone entity event creation...")
    
    # Read current drone.py
    drone_path = Path("src/core/domain/entities/drone.py")
    content = drone_path.read_text()
    
    # Fix event creation patterns
    replacements = [
        # Fix DroneConnectedEvent
        ('DroneConnectedEvent(\n                aggregate_id=self.id,\n                position=initial_position,\n            )',
         'DroneConnectedEvent(\n                position=initial_position,\n                aggregate_id=self.id,\n            )'),
        
        # Fix DroneDisconnectedEvent
        ('DroneDisconnectedEvent(\n                aggregate_id=self.id,\n                last_state=old_state,\n            )',
         'DroneDisconnectedEvent(\n                last_state=str(old_state),\n                aggregate_id=self.id,\n            )'),
        
        # Fix DroneArmedEvent
        ('DroneArmedEvent(\n                aggregate_id=self.id,\n                home_position=self._home_position,\n            )',
         'DroneArmedEvent(\n                home_position=self._home_position,\n                aggregate_id=self.id,\n            )'),
        
        # Fix DroneTookOffEvent
        ('DroneTookOffEvent(\n                aggregate_id=self.id,\n                target_altitude=target_altitude,\n            )',
         'DroneTookOffEvent(\n                target_altitude=target_altitude,\n                aggregate_id=self.id,\n            )'),
         
        # Fix DroneStateChangedEvent - multiple occurrences
        ('DroneStateChangedEvent(\n                    aggregate_id=self.id,\n                    old_state=DroneState.TAKING_OFF,\n                    new_state=DroneState.HOVERING,\n                )',
         'DroneStateChangedEvent(\n                    old_state=str(DroneState.TAKING_OFF),\n                    new_state=str(DroneState.HOVERING),\n                    aggregate_id=self.id,\n                )'),
    ]
    
    # Apply replacements
    for old, new in replacements:
        if old in content:
            content = content.replace(old, new)
    
    # General fix for any remaining DroneStateChangedEvent
    import re
    pattern = r'DroneStateChangedEvent\(\s*aggregate_id=self\.id,\s*old_state=([^,]+),\s*new_state=([^,]+),\s*\)'
    replacement = r'DroneStateChangedEvent(\n                old_state=str(\1),\n                new_state=str(\2),\n                aggregate_id=self.id,\n            )'
    content = re.sub(pattern, replacement, content)
    
    drone_path.write_text(content)
    print("✅ Updated drone entity event creation")


def verify_imports():
    """Verify all imports are correct."""
    print("\n🔍 Verifying imports...")
    
    issues = []
    
    # Check all Python files
    for root, dirs, files in os.walk("src"):
        for file in files:
            if file.endswith(".py"):
                filepath = Path(root) / file
                content = filepath.read_text()
                
                # Check for wrong event imports
                if "from event import" in content:
                    issues.append(f"{filepath}: Direct import from event.py")
                
                # Check for duplicate imports
                lines = content.split('\n')
                imports = [l for l in lines if l.strip().startswith('from') or l.strip().startswith('import')]
                seen = set()
                for imp in imports:
                    if imp in seen and imp.strip():
                        issues.append(f"{filepath}: Duplicate import: {imp}")
                    seen.add(imp)
    
    if issues:
        print("⚠️  Import issues found:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("✅ All imports look correct")


def main():
    """Run all fixes."""
    print("🚀 Fixing ALL domain model issues\n")
    
    fix_domain_event()
    fix_drone_events()
    update_drone_entity()
    verify_imports()
    
    print("\n✅ All fixes applied!")
    print("\nNext: Run 'python scripts/test_domain_models.py' to verify")


if __name__ == "__main__":
    main()