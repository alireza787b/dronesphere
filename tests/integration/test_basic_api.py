"""Basic integration tests for API endpoints."""

import httpx
import pytest


@pytest.mark.integration
async def test_server_ping():
    """Test server ping endpoint (requires running server)."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("http://localhost:8002/ping")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
        except httpx.ConnectError:
            pytest.skip("Server not running")


@pytest.mark.integration
async def test_agent_health():
    """Test agent health endpoint (requires running agent)."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("http://localhost:8001/health")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
        except httpx.ConnectError:
            pytest.skip("Agent not running")
