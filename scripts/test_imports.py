#!/usr/bin/env python3
"""Test basic imports work."""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("Testing imports...")

try:
    # Test shared imports first
    print("1. Testing shared domain imports...")
    from src.shared.domain.value_object import ValueObject
    print("   ✅ ValueObject imported")
    
    from src.shared.domain.entity import Entity
    print("   ✅ Entity imported")
    
    from src.shared.domain.event import DomainEvent
    print("   ✅ DomainEvent imported")
    
    # Test value objects (without circular imports)
    print("\n2. Testing value object imports...")
    from src.core.domain.value_objects.position import Position
    print("   ✅ Position imported")
    
    # Test events
    print("\n3. Testing event imports...")
    from src.core.domain.events.drone_events import DroneConnectedEvent
    print("   ✅ DroneEvents imported")
    
    # Test entities
    print("\n4. Testing entity imports...")
    from src.core.domain.entities.drone import Drone, DroneState
    print("   ✅ Drone entity imported")
    
    # Test commands last (they depend on position)
    print("\n5. Testing command imports...")
    from src.core.domain.value_objects.command import TakeoffCommand
    print("   ✅ Commands imported")
    
    print("\n🎉 All imports successful!")
    
except ImportError as e:
    print(f"\n❌ Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
