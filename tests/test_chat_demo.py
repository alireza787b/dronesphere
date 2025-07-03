# tests/test_chat_demo.py
"""
Demo test for the chat system.
"""

import asyncio
import httpx
import json


async def test_chat_flow():
    """Test the complete chat flow."""
    
    base_url = "http://localhost:8001"
    
    async with httpx.AsyncClient() as client:
        # Start a chat session
        print("=== Starting Chat Session ===")
        
        # Test 1: Simple takeoff
        response = await client.post(
            f"{base_url}/api/v1/chat/message",
            json={
                "drone_id": "test-drone-01",
                "message": "Take off to 20 meters please"
            }
        )
        result = response.json()
        print(f"\nUser: Take off to 20 meters please")
        print(f"Assistant: {result['response']}")
        print(f"Commands: {result['commands']}")
        session_id = result['session_id']
        
        # Test 2: Complex movement
        response = await client.post(
            f"{base_url}/api/v1/chat/message",
            json={
                "session_id": session_id,
                "drone_id": "test-drone-01",
                "message": "Move 5 meters north and 2 meters east"
            }
        )
        result = response.json()
        print(f"\nUser: Move 5 meters north and 2 meters east")
        print(f"Assistant: {result['response']}")
        print(f"Commands: {result['commands']}")
        
        # Test 3: Get session history
        response = await client.get(
            f"{base_url}/api/v1/chat/session/{session_id}/history"
        )
        history = response.json()
        print(f"\n=== Session History ===")
        print(f"Total messages: {len(history['messages'])}")


if __name__ == "__main__":
    asyncio.run(test_chat_flow())