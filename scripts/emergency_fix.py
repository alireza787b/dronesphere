#!/usr/bin/env python3
"""Emergency fix script to diagnose and fix import issues."""

import os
import sys
from pathlib import Path

# Colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

def check_file_exists(filepath):
    """Check if file exists and report."""
    if os.path.exists(filepath):
        print(f"{GREEN}✅ {filepath}{RESET}")
        return True
    else:
        print(f"{RED}❌ {filepath} - MISSING!{RESET}")
        return False

def main():
    """Run emergency diagnostics."""
    print(f"\n{YELLOW}🚨 Emergency Domain Model Diagnostic{RESET}")
    print("=" * 50)
    
    # Check Python version
    print(f"\nPython version: {sys.version}")
    
    # Check current directory
    print(f"\nCurrent directory: {os.getcwd()}")
    
    # Check if we're in the right place
    if not os.path.exists("pyproject.toml"):
        print(f"{RED}❌ Not in project root! Run from dronesphere/ directory{RESET}")
        return 1
    
    # Required files
    print(f"\n{YELLOW}Checking required files:{RESET}")
    
    required_files = [
        # Shared domain
        "src/__init__.py",
        "src/shared/__init__.py",
        "src/shared/domain/__init__.py",
        "src/shared/domain/value_object.py",
        "src/shared/domain/entity.py",
        "src/shared/domain/event.py",
        
        # Core domain
        "src/core/__init__.py",
        "src/core/domain/__init__.py",
        
        # Entities
        "src/core/domain/entities/__init__.py",
        "src/core/domain/entities/drone.py",
        
        # Value objects
        "src/core/domain/value_objects/__init__.py",
        "src/core/domain/value_objects/position.py",
        "src/core/domain/value_objects/command.py",
        
        # Events
        "src/core/domain/events/__init__.py",
        "src/core/domain/events/drone_events.py",
    ]
    
    missing_files = []
    for filepath in required_files:
        if not check_file_exists(filepath):
            missing_files.append(filepath)
    
    if missing_files:
        print(f"\n{RED}Missing {len(missing_files)} files!{RESET}")
        print(f"\n{YELLOW}Creating missing __init__.py files...{RESET}")
        
        # Create missing __init__.py files
        for filepath in missing_files:
            if filepath.endswith("__init__.py"):
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                Path(filepath).touch()
                print(f"{GREEN}Created: {filepath}{RESET}")
    
    # Test imports
    print(f"\n{YELLOW}Testing imports...{RESET}")
    
    # Add to Python path
    sys.path.insert(0, os.getcwd())
    
    try:
        # Test shared imports
        from src.shared.domain.value_object import ValueObject
        print(f"{GREEN}✅ ValueObject imported{RESET}")
    except ImportError as e:
        print(f"{RED}❌ Failed to import ValueObject: {e}{RESET}")
        print("\nYou need to create src/shared/domain/value_object.py")
        print("Copy the content from the artifact 'base-value-object'")
        return 1
    
    print(f"\n{GREEN}🎉 Basic structure looks good!{RESET}")
    print("\nNext steps:")
    print("1. Ensure all .py files have the correct content from artifacts")
    print("2. Update command.py with the fixed version (no circular import)")
    print("3. Run: python scripts/test_domain_models.py")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())