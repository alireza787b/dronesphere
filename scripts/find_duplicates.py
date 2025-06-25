#!/usr/bin/env python3
"""Find duplicate DomainEvent definitions and other issues."""

import os
from pathlib import Path
from collections import defaultdict

def find_files(pattern):
    """Find all files matching pattern."""
    files = []
    for root, dirs, filenames in os.walk("src"):
        for filename in filenames:
            if filename == pattern or filename.endswith(pattern):
                files.append(os.path.join(root, filename))
    return files

def main():
    print("🔍 Searching for duplicate files and import issues...\n")
    
    # Find all event.py files
    event_files = find_files("event.py")
    print(f"Found {len(event_files)} event.py files:")
    for f in event_files:
        print(f"  - {f}")
    
    # Find all files that might import DomainEvent
    print("\n📝 Files importing DomainEvent:")
    for root, dirs, files in os.walk("src"):
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r') as f:
                        content = f.read()
                        if "DomainEvent" in content and "import" in content:
                            # Find the actual import line
                            for line in content.split('\n'):
                                if "import" in line and "DomainEvent" in line:
                                    print(f"  {filepath}: {line.strip()}")
                                    break
                except:
                    pass
    
    # Check for other duplicates
    print("\n🔍 Checking for other duplicate files:")
    file_map = defaultdict(list)
    for root, dirs, files in os.walk("src"):
        for file in files:
            if file.endswith(".py") and not file.startswith("__"):
                file_map[file].append(os.path.join(root, file))
    
    for filename, paths in file_map.items():
        if len(paths) > 1:
            print(f"\n  Duplicate: {filename}")
            for p in paths:
                print(f"    - {p}")

if __name__ == "__main__":
    main()