"""DroneSphere Agent - Entry point for drone control agent.

Runs the FastAPI application on port 8001 for drone command and control.
This service runs on individual drones or Raspberry Pi units.

Path: agent/main.py
"""
import os
import sys
from pathlib import Path

import uvicorn

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agent.api import app


def main():
    """Start the DroneSphere agent server."""
    print("🚁 Starting DroneSphere Agent v2.0.0")
    print("📡 Server will be available at: http://localhost:8001")
    print("�� Health check: http://localhost:8001/health")
    print("📊 Detailed health: http://localhost:8001/health/detailed")
    print("-" * 50)

    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info", access_log=True)


if __name__ == "__main__":
    main()
