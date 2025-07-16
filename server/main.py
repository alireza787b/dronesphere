"""DroneSphere Server - Entry point for fleet management.

Runs the FastAPI application on port 8002 for fleet command routing.
This service routes commands to individual drone agents.

Path: server/main.py
"""
import uvicorn
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from server.api import app


def main():
    """Start the DroneSphere server."""
    print("🖥️  Starting DroneSphere Server v2.0.0")
    print("📡 Server will be available at: http://localhost:8002")
    print("🔧 Fleet health: http://localhost:8002/fleet/health")
    print("🎯 Fleet commands: http://localhost:8002/fleet/commands")
    print("-" * 50)
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8002,
        log_level="info",
        access_log=True
    )


if __name__ == "__main__":
    main()
