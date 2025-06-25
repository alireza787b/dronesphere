#!/usr/bin/env python3
"""Main entry point for drone controller on Raspberry Pi."""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def main():
    """Main drone controller loop."""
    print("🚁 DroneSphere Drone Controller Starting...")
    
    # TODO: Initialize MAVSDK connection
    # TODO: Connect to server WebSocket
    # TODO: Start telemetry loop
    # TODO: Start command receiver
    
    print("✅ Drone controller ready")
    
    try:
        # Keep running
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        print("\n👋 Shutting down drone controller")

if __name__ == "__main__":
    asyncio.run(main())
