#!/usr/bin/env python3
# agent/run_agent.py
"""
Run script for DroneSphere Agent that properly sets up the Python path.
"""

import sys
from pathlib import Path

# Add src directory to Python path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

# Now import and run main
from agent.main import main

if __name__ == "__main__":
    main()
