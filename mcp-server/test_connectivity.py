#!/usr/bin/env python3
"""Test MCP server connectivity in different modes."""

import asyncio
import json
import sys

import httpx


async def test_http():
    """Test HTTP endpoint."""
    print("Testing HTTP endpoint...")

    urls = [
        "http://localhost:8003/health",
        "http://localhost:8003/mcp",
        "http://172.18.0.1:8003/mcp",  # Docker bridge
        "http://62.60.206.251:8003/mcp",  # Public IP
    ]

    async with httpx.AsyncClient(timeout=5.0) as client:
        for url in urls:
            try:
                response = await client.get(url)
                print(f"  {url}: {response.status_code}")
            except Exception as e:
                print(f"  {url}: Failed - {e}")


async def test_stdio():
    """Test STDIO mode readiness."""
    print("\nTesting STDIO readiness...")
    try:
        import server

        print("  ✅ Server module imports OK")
        print("  ✅ Ready for Claude Desktop")
    except Exception as e:
        print(f"  ❌ Import failed: {e}")


if __name__ == "__main__":
    print("MCP Server Connectivity Test")
    print("=" * 40)

    if len(sys.argv) > 1 and sys.argv[1] == "http":
        asyncio.run(test_http())
    else:
        asyncio.run(test_stdio())
        print("\nTo test HTTP: python test_connectivity.py http")
