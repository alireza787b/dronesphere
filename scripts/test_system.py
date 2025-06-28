#!/usr/bin/env python3
# scripts/test_system.py
"""
Test script to verify the complete system is working.

Tests:
1. Server is running
2. Agent can connect
3. WebSocket communication works
"""

import asyncio
import json
import os
import sys

import aiohttp


async def test_server_health():
    """Test if server is running."""
    print("🔍 Testing server health...")

    # Get port from environment or use default
    import os

    port = os.getenv("SERVER_PORT", "8001")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://localhost:{port}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Server is healthy on port {port}: {data}")
                    return True
                else:
                    print(f"❌ Server returned status {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Cannot connect to server on port {port}: {e}")
        print("   Make sure server is running: cd server && python run_server.py")
        return False


async def test_api_docs():
    """Test if API docs are available."""
    print("\n🔍 Testing API documentation...")

    port = os.getenv("SERVER_PORT", "8001")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://localhost:{port}/docs") as response:
                if response.status == 200:
                    print(f"✅ API docs available at http://localhost:{port}/docs")
                    return True
                else:
                    print(f"❌ API docs returned status {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Cannot access API docs: {e}")
        return False


async def test_drone_list():
    """Test drone listing endpoint."""
    print("\n🔍 Testing drone list endpoint...")

    port = os.getenv("SERVER_PORT", "8001")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"http://localhost:{port}/api/v1/drones"
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print("✅ Drone list endpoint working")
                    print(f"   Connected drones: {len(data.get('drones', {}))}")
                    return True
                else:
                    print(f"❌ Drone list returned status {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Cannot access drone list: {e}")
        return False


async def test_websocket():
    """Test WebSocket connection."""
    print("\n🔍 Testing WebSocket connection...")

    port = os.getenv("SERVER_PORT", "8001")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(f"ws://localhost:{port}/ws/client") as ws:
                print("✅ WebSocket connected")

                # Wait for system state
                msg = await ws.receive()
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    if data.get("type") == "system_state":
                        print("✅ Received system state")
                        return True

                print("❌ Unexpected WebSocket message")
                return False

    except Exception as e:
        print(f"❌ WebSocket connection failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("=" * 50)
    print("DroneSphere System Test")
    print("=" * 50)

    tests = [
        test_server_health(),
        test_api_docs(),
        test_drone_list(),
        test_websocket(),
    ]

    results = await asyncio.gather(*tests, return_exceptions=True)

    # Summary
    print("\n" + "=" * 50)
    print("Test Summary:")
    passed = sum(1 for r in results if r is True)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    if passed == total:
        port = os.getenv("SERVER_PORT", "8001")
        print("\n✅ All tests passed! System is ready.")
        print("\nNext steps:")
        print("1. Run the agent: cd agent && python run_agent.py --dev")
        print(f"2. Open API docs: http://localhost:{port}/docs")
        print("3. Start building the frontend!")
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
        print("\nMake sure:")
        print("1. Server is running: cd server && python run_server.py")
        print(f"2. No firewall blocking port {os.getenv('SERVER_PORT', '8001')}")
        print("3. All dependencies are installed")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
