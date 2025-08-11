#!/usr/bin/env python3
"""
DroneSphere MCP Server Startup Script
====================================
Simple script to start the MCP server with proper configuration.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the parent directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.config import ConfigManager
from mcp.server import MCPServer


async def main():
    """Main startup function."""
    try:
        print("🚁 Starting DroneSphere MCP Server...")

        # Initialize configuration
        config_manager = ConfigManager()

        # Create and start server
        server = MCPServer(config_manager)
        await server.run()

    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
